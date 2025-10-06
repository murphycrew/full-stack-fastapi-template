"""
RLS policy migration utilities for Alembic.

This module provides utilities for managing RLS policies during database migrations.
It includes functions to create, update, and manage RLS policies for user-scoped tables.
"""

import logging
from typing import List, Dict, Any

from sqlalchemy import text, Connection
from alembic import op

from app.core.config import settings
from app.core.rls import rls_registry, policy_generator

logger = logging.getLogger(__name__)


def create_rls_policies_for_table(table_name: str) -> None:
    """
    Create RLS policies for a specific table.

    Args:
        table_name: Name of the table to create RLS policies for
    """
    if not settings.RLS_ENABLED:
        logger.info(f"RLS disabled, skipping policy creation for table: {table_name}")
        return

    try:
        # Generate RLS setup SQL
        rls_sql_statements = policy_generator.generate_complete_rls_setup_sql(table_name)

        # Execute each SQL statement
        for sql_statement in rls_sql_statements:
            op.execute(text(sql_statement))

        logger.info(f"Created RLS policies for table: {table_name}")

    except Exception as e:
        logger.error(f"Failed to create RLS policies for table {table_name}: {e}")
        raise


def drop_rls_policies_for_table(table_name: str) -> None:
    """
    Drop RLS policies for a specific table.

    Args:
        table_name: Name of the table to drop RLS policies for
    """
    try:
        # Generate drop policies SQL
        drop_sql_statements = policy_generator.generate_drop_policies_sql(table_name)

        # Execute each SQL statement
        for sql_statement in drop_sql_statements:
            op.execute(text(sql_statement))

        logger.info(f"Dropped RLS policies for table: {table_name}")

    except Exception as e:
        logger.error(f"Failed to drop RLS policies for table {table_name}: {e}")
        raise


def enable_rls_for_table(table_name: str) -> None:
    """
    Enable RLS for a specific table.

    Args:
        table_name: Name of the table to enable RLS for
    """
    if not settings.RLS_ENABLED:
        logger.info(f"RLS disabled, skipping RLS enablement for table: {table_name}")
        return

    try:
        sql_statement = policy_generator.generate_enable_rls_sql(table_name)
        op.execute(text(sql_statement))

        logger.info(f"Enabled RLS for table: {table_name}")

    except Exception as e:
        logger.error(f"Failed to enable RLS for table {table_name}: {e}")
        raise


def disable_rls_for_table(table_name: str) -> None:
    """
    Disable RLS for a specific table.

    Args:
        table_name: Name of the table to disable RLS for
    """
    try:
        sql_statement = policy_generator.generate_disable_rls_sql(table_name)
        op.execute(text(sql_statement))

        logger.info(f"Disabled RLS for table: {table_name}")

    except Exception as e:
        logger.error(f"Failed to disable RLS for table {table_name}: {e}")
        raise


def create_rls_policies_for_all_registered_tables() -> None:
    """
    Create RLS policies for all registered RLS-scoped tables.
    """
    registered_tables = rls_registry.get_registered_tables()

    if not registered_tables:
        logger.info("No RLS-scoped tables registered")
        return

    for table_name in registered_tables.keys():
        create_rls_policies_for_table(table_name)


def drop_rls_policies_for_all_registered_tables() -> None:
    """
    Drop RLS policies for all registered RLS-scoped tables.
    """
    registered_tables = rls_registry.get_registered_tables()

    if not registered_tables:
        logger.info("No RLS-scoped tables registered")
        return

    for table_name in registered_tables.keys():
        drop_rls_policies_for_table(table_name)


def check_rls_enabled_for_table(table_name: str) -> bool:
    """
    Check if RLS is enabled for a specific table.

    Args:
        table_name: Name of the table to check

    Returns:
        True if RLS is enabled, False otherwise
    """
    try:
        sql_statement = policy_generator.check_rls_enabled_sql(table_name)
        result = op.get_bind().execute(text(sql_statement)).first()

        return result[0] if result else False

    except Exception as e:
        logger.error(f"Failed to check RLS status for table {table_name}: {e}")
        return False


def upgrade_rls_policies() -> None:
    """
    Upgrade RLS policies for all registered tables.
    This is typically called during migration upgrades.
    """
    if not settings.RLS_ENABLED:
        logger.info("RLS disabled, skipping policy upgrade")
        return

    registered_tables = rls_registry.get_registered_tables()

    for table_name in registered_tables.keys():
        try:
            # Drop existing policies first
            drop_rls_policies_for_table(table_name)

            # Create new policies
            create_rls_policies_for_table(table_name)

        except Exception as e:
            logger.error(f"Failed to upgrade RLS policies for table {table_name}: {e}")
            raise


def downgrade_rls_policies() -> None:
    """
    Downgrade RLS policies for all registered tables.
    This is typically called during migration downgrades.
    """
    registered_tables = rls_registry.get_registered_tables()

    for table_name in registered_tables.keys():
        try:
            # Drop policies
            drop_rls_policies_for_table(table_name)

            # Disable RLS
            disable_rls_for_table(table_name)

        except Exception as e:
            logger.error(f"Failed to downgrade RLS policies for table {table_name}: {e}")
            raise


# Migration helper functions for common RLS operations
def setup_rls_for_new_table(table_name: str) -> None:
    """
    Complete RLS setup for a new table.

    Args:
        table_name: Name of the new table
    """
    enable_rls_for_table(table_name)
    create_rls_policies_for_table(table_name)


def teardown_rls_for_removed_table(table_name: str) -> None:
    """
    Complete RLS teardown for a removed table.

    Args:
        table_name: Name of the removed table
    """
    drop_rls_policies_for_table(table_name)
    disable_rls_for_table(table_name)
