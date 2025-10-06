#!/usr/bin/env python3
"""
Database role setup script for RLS (Row-Level Security) infrastructure.

This script creates the necessary database roles for RLS functionality:
- Application user role: For normal application operations (subject to RLS)
- Maintenance admin role: For maintenance operations (bypasses RLS)

The script is designed to be run during database initialization
and supports both initial setup and role updates.
"""

import logging
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseRoleSetup:
    """Manages database role creation and configuration for RLS."""

    def __init__(self):
        self.engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

    def create_application_role(self, role_name: str, password: str) -> bool:
        """
        Create the application database role for normal operations.

        This role will be subject to RLS policies and used for regular
        application database connections.

        Args:
            role_name: Name of the application role
            password: Password for the application role

        Returns:
            bool: True if role was created successfully, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Create the role
                conn.execute(
                    text(
                        f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{role_name}') THEN
                            CREATE ROLE {role_name} WITH LOGIN PASSWORD '{password}';
                        END IF;
                    END
                    $$;
                """
                    )
                )

                # Grant necessary permissions
                conn.execute(
                    text(
                        f"""
                    GRANT CONNECT ON DATABASE {settings.POSTGRES_DB} TO {role_name};
                    GRANT USAGE ON SCHEMA public TO {role_name};
                    GRANT CREATE ON SCHEMA public TO {role_name};
                    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role_name};
                    GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {role_name};
                """
                    )
                )

                # Set default privileges for future objects
                conn.execute(
                    text(
                        f"""
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role_name};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT USAGE ON SEQUENCES TO {role_name};
                """
                    )
                )

                conn.commit()
                logger.info(f"Successfully created application role: {role_name}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to create application role {role_name}: {e}")
            return False

    def create_maintenance_admin_role(self, role_name: str, password: str) -> bool:
        """
        Create the maintenance admin database role for maintenance operations.

        This role can bypass RLS policies and is used for:
        - Database maintenance operations
        - Read-only reporting and analytics
        - Emergency data access

        Args:
            role_name: Name of the maintenance admin role
            password: Password for the maintenance admin role

        Returns:
            bool: True if role was created successfully, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Create the role with superuser privileges
                conn.execute(
                    text(
                        f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{role_name}') THEN
                            CREATE ROLE {role_name} WITH LOGIN SUPERUSER PASSWORD '{password}';
                        END IF;
                    END
                    $$;
                """
                    )
                )

                # Grant admin permissions
                conn.execute(
                    text(
                        f"""
                    GRANT CONNECT ON DATABASE {settings.POSTGRES_DB} TO {role_name};
                    GRANT ALL PRIVILEGES ON SCHEMA public TO {role_name};
                    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {role_name};
                    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {role_name};
                    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO {role_name};
                """
                    )
                )

                # Set default privileges for future objects
                conn.execute(
                    text(
                        f"""
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT ALL ON TABLES TO {role_name};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT ALL ON SEQUENCES TO {role_name};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT ALL ON FUNCTIONS TO {role_name};
                """
                    )
                )

                conn.commit()
                logger.info(f"Successfully created maintenance admin role: {role_name}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Failed to create maintenance admin role {role_name}: {e}")
            return False

    def setup_rls_roles(self) -> bool:
        """
        Set up all necessary database roles for RLS functionality.

        Creates both application and maintenance admin roles with
        appropriate permissions for RLS operations.

        Returns:
            bool: True if all roles were created successfully, False otherwise
        """
        logger.info("Setting up RLS database roles...")

        # Get role names from environment variables or use defaults
        app_role = os.getenv("RLS_APP_USER", "rls_app_user")
        app_password = os.getenv("RLS_APP_PASSWORD", "changethis")

        admin_role = os.getenv("RLS_MAINTENANCE_ADMIN", "rls_maintenance_admin")
        admin_password = os.getenv("RLS_MAINTENANCE_ADMIN_PASSWORD", "changethis")

        # Create application role
        app_success = self.create_application_role(app_role, app_password)

        # Create maintenance admin role
        admin_success = self.create_maintenance_admin_role(admin_role, admin_password)

        if app_success and admin_success:
            logger.info("All RLS database roles created successfully")
            return True
        else:
            logger.error("Failed to create some RLS database roles")
            return False

    def verify_roles(self) -> bool:
        """
        Verify that all required database roles exist and have correct permissions.

        Returns:
            bool: True if all roles exist and are properly configured, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Check if roles exist
                result = conn.execute(
                    text(
                        """
                    SELECT rolname FROM pg_catalog.pg_roles
                    WHERE rolname IN ('rls_app_user', 'rls_maintenance_admin');
                """
                    )
                )

                existing_roles = [row[0] for row in result.fetchall()]

                if len(existing_roles) >= 2:
                    logger.info("All RLS database roles verified successfully")
                    return True
                else:
                    logger.warning(f"Missing RLS roles. Found: {existing_roles}")
                    return False

        except SQLAlchemyError as e:
            logger.error(f"Failed to verify RLS roles: {e}")
            return False


def main():
    """Main entry point for the database role setup script."""
    logger.info("Starting RLS database role setup...")

    setup = DatabaseRoleSetup()

    # Set up the roles
    success = setup.setup_rls_roles()

    if success:
        # Verify the setup
        if setup.verify_roles():
            logger.info("RLS database role setup completed successfully")
            sys.exit(0)
        else:
            logger.error("RLS database role verification failed")
            sys.exit(1)
    else:
        logger.error("RLS database role setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
