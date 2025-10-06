"""
RLS (Row-Level Security) infrastructure for automatic user-scoped data isolation.

This module provides the core infrastructure for PostgreSQL Row-Level Security
enforcement in the FastAPI template. It includes:

- UserScopedBase: Base class for user-scoped models
- RLS registry: Runtime metadata for RLS-scoped tables
- Policy generation utilities: Automatic RLS policy creation
- Admin context management: Support for admin bypass functionality
- Identity context: Per-request user information management

All RLS management is internal infrastructure - no user-facing API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlmodel import Field, SQLModel

logger = logging.getLogger(__name__)


class UserScopedBase(SQLModel):
    """
    Base class for models that require automatic RLS enforcement.

    Models inheriting from this class will automatically:
    - Have an owner_id field with foreign key to user.id
    - Be registered for RLS policy generation
    - Have RLS policies applied during migrations
    - Enforce user isolation at the database level

    Example:
        class Item(UserScopedBase, table=True):
            title: str = Field(max_length=300)
            description: Optional[str] = None
            # owner_id is automatically inherited from UserScopedBase
    """

    owner_id: UUID = Field(
        foreign_key="user.id",
        nullable=False,
        ondelete="CASCADE",
        index=True,  # Index for performance with RLS policies
        description="ID of the user who owns this record",
    )

    def __init_subclass__(cls, **kwargs):
        """Automatically register RLS-scoped models when they are defined."""
        super().__init_subclass__(**kwargs)

        # Only register if this is a table model
        if hasattr(cls, "__tablename__"):
            table_name = cls.__tablename__

            # Register with RLS registry
            rls_registry.register_table(
                table_name,
                {
                    "model_class": cls,
                    "table_name": table_name,
                    "owner_id_field": "owner_id",
                    "registered_at": __import__("datetime").datetime.now().isoformat(),
                },
            )

            logger.info(f"Auto-registered RLS model: {cls.__name__} -> {table_name}")


class RLSRegistry:
    """
    Registry for tracking RLS-scoped tables and their metadata.

    This registry is used by:
    - Migration system to generate RLS policies
    - CI system to validate model inheritance
    - Runtime system to manage RLS context
    """

    _registry: dict[str, dict[str, Any]] = {}
    _registered_models: list[type[UserScopedBase]] = []

    @classmethod
    def register_table(cls, table_name: str, metadata: dict[str, Any]) -> None:
        """Register a table for RLS enforcement."""
        cls._registry[table_name] = metadata
        logger.debug(f"Registered RLS table: {table_name}")

    @classmethod
    def register_model(cls, model: type[UserScopedBase]) -> None:
        """Register a UserScopedBase model."""
        if model not in cls._registered_models:
            cls._registered_models.append(model)
            logger.info(f"Registered RLS-scoped model: {model.__name__}")

    @classmethod
    def get_registered_tables(cls) -> dict[str, dict[str, Any]]:
        """Get all registered RLS tables."""
        return cls._registry.copy()

    @classmethod
    def get_registered_models(cls) -> list[type[UserScopedBase]]:
        """Get all registered RLS-scoped models."""
        return cls._registered_models.copy()

    @classmethod
    def is_registered(cls, table_name: str) -> bool:
        """Check if a table is registered for RLS."""
        return table_name in cls._registry

    @classmethod
    def is_model_registered(cls, model: type[UserScopedBase]) -> bool:
        """Check if a model is registered for RLS."""
        return model in cls._registered_models

    @classmethod
    def get_table_names(cls) -> list[str]:
        """Get list of all registered table names."""
        return list(cls._registry.keys())

    @classmethod
    def get_model_names(cls) -> list[str]:
        """Get list of all registered model names."""
        return [model.__name__ for model in cls._registered_models]

    @classmethod
    def clear_registry(cls) -> None:
        """Clear the registry (primarily for testing)."""
        cls._registry.clear()
        cls._registered_models.clear()


class RLSPolicyGenerator:
    """
    Utility class for generating PostgreSQL RLS policies.

    Generates the SQL DDL statements needed to:
    - Enable RLS on tables
    - Create user isolation policies
    - Create admin bypass policies
    - Handle policy updates and migrations
    """

    @staticmethod
    def generate_enable_rls_sql(table_name: str) -> str:
        """Generate SQL to enable RLS on a table."""
        return f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"

    @staticmethod
    def generate_user_policies_sql(table_name: str) -> list[str]:
        """Generate SQL for user isolation policies."""
        policies = []

        # User SELECT policy - can only see their own data
        policies.append(
            f"""
            CREATE POLICY user_select_policy ON {table_name}
                FOR SELECT USING (
                    app.user_id::uuid = owner_id OR
                    current_setting('app.role', true) IN ('admin', 'read_only_admin')
                );
        """
        )

        # User INSERT policy - can only insert with their own owner_id
        policies.append(
            f"""
            CREATE POLICY user_insert_policy ON {table_name}
                FOR INSERT WITH CHECK (
                    app.user_id::uuid = owner_id OR
                    current_setting('app.role', true) = 'admin'
                );
        """
        )

        # User UPDATE policy - can only update their own data
        policies.append(
            f"""
            CREATE POLICY user_update_policy ON {table_name}
                FOR UPDATE USING (
                    app.user_id::uuid = owner_id OR
                    current_setting('app.role', true) = 'admin'
                );
        """
        )

        # User DELETE policy - can only delete their own data
        policies.append(
            f"""
            CREATE POLICY user_delete_policy ON {table_name}
                FOR DELETE USING (
                    app.user_id::uuid = owner_id OR
                    current_setting('app.role', true) = 'admin'
                );
        """
        )

        return policies

    @staticmethod
    def generate_drop_policies_sql(table_name: str) -> list[str]:
        """Generate SQL to drop existing RLS policies."""
        policies = [
            f"DROP POLICY IF EXISTS user_select_policy ON {table_name};",
            f"DROP POLICY IF EXISTS user_insert_policy ON {table_name};",
            f"DROP POLICY IF EXISTS user_update_policy ON {table_name};",
            f"DROP POLICY IF EXISTS user_delete_policy ON {table_name};",
        ]
        return policies

    @staticmethod
    def generate_complete_rls_setup_sql(table_name: str) -> list[str]:
        """Generate complete RLS setup SQL for a table."""
        sql_statements = []

        # Enable RLS
        sql_statements.append(RLSPolicyGenerator.generate_enable_rls_sql(table_name))

        # Drop existing policies first
        sql_statements.extend(RLSPolicyGenerator.generate_drop_policies_sql(table_name))

        # Create new policies
        sql_statements.extend(RLSPolicyGenerator.generate_user_policies_sql(table_name))

        return sql_statements

    @staticmethod
    def generate_disable_rls_sql(table_name: str) -> str:
        """Generate SQL to disable RLS on a table."""
        return f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"

    @staticmethod
    def check_rls_enabled_sql(table_name: str) -> str:
        """Generate SQL to check if RLS is enabled on a table."""
        return f"""
            SELECT relrowsecurity
            FROM pg_class
            WHERE relname = '{table_name}'
        """


class AdminContext:
    """
    Context manager for admin operations that bypass RLS.

    Supports both user-level and database-level admin roles:
    - User-level: Regular users with admin privileges
    - Database-level: Database roles for maintenance operations
    """

    def __init__(
        self, user_id: UUID, role: str = "admin", session: Session | None = None
    ):
        self.user_id = user_id
        self.role = role
        self.session = session
        self._original_role: str | None = None
        self._original_user_id: UUID | None = None

    def __enter__(self):
        """Set admin context for the current session."""
        if self.session:
            # Store original context
            try:
                result = self.session.execute(
                    text("SELECT current_setting('app.role', true)")
                ).first()
                self._original_role = result[0] if result else None
                result = self.session.execute(
                    text("SELECT current_setting('app.user_id', true)")
                ).first()
                self._original_user_id = (
                    UUID(result[0]) if result and result[0] else None
                )
            except Exception:
                # Ignore errors when reading original context
                pass

            # Set admin context
            self.session.execute(text(f"SET app.user_id = '{self.user_id}'"))
            self.session.execute(text(f"SET app.role = '{self.role}'"))

        logger.debug(f"Setting admin context: user_id={self.user_id}, role={self.role}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear admin context."""
        if self.session:
            try:
                # Restore original context or clear it
                if self._original_user_id:
                    self.session.execute(
                        text(f"SET app.user_id = '{self._original_user_id}'")
                    )
                else:
                    self.session.execute(text("SET app.user_id = NULL"))

                if self._original_role:
                    self.session.execute(
                        text(f"SET app.role = '{self._original_role}'")
                    )
                else:
                    self.session.execute(text("SET app.role = NULL"))
            except Exception:
                # Ignore errors when restoring context
                pass

        logger.debug("Clearing admin context")

    @classmethod
    def create_read_only_admin(
        cls, user_id: UUID, session: Session | None = None
    ) -> AdminContext:
        """Create a read-only admin context."""
        return cls(user_id, "read_only_admin", session)

    @classmethod
    def create_full_admin(
        cls, user_id: UUID, session: Session | None = None
    ) -> AdminContext:
        """Create a full admin context."""
        return cls(user_id, "admin", session)


class IdentityContext:
    """
    Per-request identity context for RLS enforcement.

    Manages the current user's identity and role for RLS policy evaluation.
    This context is set by FastAPI dependency injection and used by
    the database session for RLS policy evaluation.
    """

    def __init__(self, user_id: UUID, role: str = "user"):
        self.user_id = user_id
        self.role = role

    def set_session_context(self, session: Session) -> None:
        """Set the identity context for a database session."""
        session.execute(text(f"SET app.user_id = '{self.user_id}'"))
        session.execute(text(f"SET app.role = '{self.role}'"))
        logger.debug(f"Set session context: user_id={self.user_id}, role={self.role}")

    def clear_session_context(self, session: Session) -> None:
        """Clear the identity context from a database session."""
        session.execute(text("SET app.user_id = NULL"))
        session.execute(text("SET app.role = NULL"))
        logger.debug("Cleared session context")


# Global registry instance
rls_registry = RLSRegistry()

# Global policy generator instance
policy_generator = RLSPolicyGenerator()
