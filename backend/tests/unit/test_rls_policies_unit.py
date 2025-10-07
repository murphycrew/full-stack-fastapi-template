"""
Tests for alembic/rls_policies.py module.

This module tests the RLS policy migration utilities, including
policy creation, dropping, and management functions.
"""

from unittest.mock import Mock, patch

import pytest

from app.alembic.rls_policies import (
    check_rls_enabled_for_table,
    create_rls_policies_for_all_registered_tables,
    create_rls_policies_for_table,
    disable_rls_for_table,
    downgrade_rls_policies,
    drop_rls_policies_for_all_registered_tables,
    drop_rls_policies_for_table,
    enable_rls_for_table,
    setup_rls_for_new_table,
    teardown_rls_for_removed_table,
    upgrade_rls_policies,
)


class TestRLSPolicies:
    """Test RLS policy migration utilities."""

    def test_create_rls_policies_for_table_when_rls_disabled(self):
        """Test that policy creation is skipped when RLS is disabled."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = False

            with patch("app.alembic.rls_policies.logger") as mock_logger:
                with patch(
                    "app.alembic.rls_policies.policy_generator"
                ) as mock_generator:
                    with patch("app.alembic.rls_policies.op") as mock_op:
                        # Call the function
                        create_rls_policies_for_table("test_table")

                        # Verify that logging was called
                        mock_logger.info.assert_called_once_with(
                            "RLS disabled, skipping policy creation for table: test_table"
                        )

                        # Verify that policy generator was not called
                        mock_generator.generate_complete_rls_setup_sql.assert_not_called()

                        # Verify that op.execute was not called
                        mock_op.execute.assert_not_called()

    def test_create_rls_policies_for_table_success(self):
        """Test successful RLS policy creation."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = True

            with patch("app.alembic.rls_policies.logger") as mock_logger:
                with patch(
                    "app.alembic.rls_policies.policy_generator"
                ) as mock_generator:
                    with patch("app.alembic.rls_policies.op") as mock_op:
                        # Mock the policy generator to return SQL statements
                        mock_sql_statements = [
                            "ALTER TABLE test_table ENABLE ROW LEVEL SECURITY;",
                            "CREATE POLICY test_policy ON test_table FOR ALL TO rls_app_user USING (owner_id = current_setting('app.user_id')::uuid);",
                        ]
                        mock_generator.generate_complete_rls_setup_sql.return_value = (
                            mock_sql_statements
                        )

                        # Call the function
                        create_rls_policies_for_table("test_table")

                        # Verify that policy generator was called
                        mock_generator.generate_complete_rls_setup_sql.assert_called_once_with(
                            "test_table"
                        )

                        # Verify that each SQL statement was executed
                        assert mock_op.execute.call_count == 2

                        # Verify that success logging was called
                        mock_logger.info.assert_called_once_with(
                            "Created RLS policies for table: test_table"
                        )

    def test_create_rls_policies_for_table_failure(self):
        """Test RLS policy creation failure handling."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = True

            with patch("app.alembic.rls_policies.logger") as mock_logger:
                with patch(
                    "app.alembic.rls_policies.policy_generator"
                ) as mock_generator:
                    with patch("app.alembic.rls_policies.op"):
                        # Mock the policy generator to raise an exception
                        mock_generator.generate_complete_rls_setup_sql.side_effect = (
                            Exception("Policy generation failed")
                        )

                        # Call the function and expect it to raise an exception
                        with pytest.raises(Exception, match="Policy generation failed"):
                            create_rls_policies_for_table("test_table")

                        # Verify that error logging was called
                        mock_logger.error.assert_called_once_with(
                            "Failed to create RLS policies for table test_table: Policy generation failed"
                        )

    def test_drop_rls_policies_for_table_success(self):
        """Test successful RLS policy dropping."""
        with patch("app.alembic.rls_policies.logger") as mock_logger:
            with patch("app.alembic.rls_policies.policy_generator") as mock_generator:
                with patch("app.alembic.rls_policies.op") as mock_op:
                    # Mock the policy generator to return drop SQL statements
                    mock_drop_statements = [
                        "DROP POLICY IF EXISTS test_table_user_policy ON test_table;",
                        "DROP POLICY IF EXISTS test_table_admin_policy ON test_table;",
                    ]
                    mock_generator.generate_drop_policies_sql.return_value = (
                        mock_drop_statements
                    )

                    # Call the function
                    drop_rls_policies_for_table("test_table")

                    # Verify that policy generator was called
                    mock_generator.generate_drop_policies_sql.assert_called_once_with(
                        "test_table"
                    )

                    # Verify that each SQL statement was executed
                    assert mock_op.execute.call_count == 2

                    # Verify that success logging was called
                    mock_logger.info.assert_called_once_with(
                        "Dropped RLS policies for table: test_table"
                    )

    def test_drop_rls_policies_for_table_failure(self):
        """Test RLS policy dropping failure handling."""
        with patch("app.alembic.rls_policies.logger") as mock_logger:
            with patch("app.alembic.rls_policies.policy_generator") as mock_generator:
                with patch("app.alembic.rls_policies.op"):
                    # Mock the policy generator to raise an exception
                    mock_generator.generate_drop_policies_sql.side_effect = Exception(
                        "Drop generation failed"
                    )

                    # Call the function and expect it to raise an exception
                    with pytest.raises(Exception, match="Drop generation failed"):
                        drop_rls_policies_for_table("test_table")

                    # Verify that error logging was called
                    mock_logger.error.assert_called_once_with(
                        "Failed to drop RLS policies for table test_table: Drop generation failed"
                    )

    def test_enable_rls_for_table_when_rls_disabled(self):
        """Test that RLS enablement is skipped when RLS is disabled."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = False

            with patch("app.alembic.rls_policies.logger") as mock_logger:
                with patch(
                    "app.alembic.rls_policies.policy_generator"
                ) as mock_generator:
                    with patch("app.alembic.rls_policies.op") as mock_op:
                        # Call the function
                        enable_rls_for_table("test_table")

                        # Verify that logging was called
                        mock_logger.info.assert_called_once_with(
                            "RLS disabled, skipping RLS enablement for table: test_table"
                        )

                        # Verify that policy generator was not called
                        mock_generator.generate_enable_rls_sql.assert_not_called()

                        # Verify that op.execute was not called
                        mock_op.execute.assert_not_called()

    def test_enable_rls_for_table_success(self):
        """Test successful RLS enablement."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = True

            with patch("app.alembic.rls_policies.logger") as mock_logger:
                with patch(
                    "app.alembic.rls_policies.policy_generator"
                ) as mock_generator:
                    with patch("app.alembic.rls_policies.op") as mock_op:
                        # Mock the policy generator to return SQL statement
                        mock_sql_statement = (
                            "ALTER TABLE test_table ENABLE ROW LEVEL SECURITY;"
                        )
                        mock_generator.generate_enable_rls_sql.return_value = (
                            mock_sql_statement
                        )

                        # Call the function
                        enable_rls_for_table("test_table")

                        # Verify that policy generator was called
                        mock_generator.generate_enable_rls_sql.assert_called_once_with(
                            "test_table"
                        )

                        # Verify that SQL statement was executed (check call count and args)
                        assert mock_op.execute.call_count == 1
                        call_args = mock_op.execute.call_args
                        assert call_args is not None
                        # Check that the SQL statement matches
                        executed_sql = str(call_args[0][0])
                        assert (
                            "ALTER TABLE test_table ENABLE ROW LEVEL SECURITY"
                            in executed_sql
                        )

                        # Verify that success logging was called
                        mock_logger.info.assert_called_once_with(
                            "Enabled RLS for table: test_table"
                        )

    def test_disable_rls_for_table_success(self):
        """Test successful RLS disablement."""
        with patch("app.alembic.rls_policies.logger") as mock_logger:
            with patch("app.alembic.rls_policies.policy_generator") as mock_generator:
                with patch("app.alembic.rls_policies.op") as mock_op:
                    # Mock the policy generator to return SQL statement
                    mock_sql_statement = (
                        "ALTER TABLE test_table DISABLE ROW LEVEL SECURITY;"
                    )
                    mock_generator.generate_disable_rls_sql.return_value = (
                        mock_sql_statement
                    )

                    # Call the function
                    disable_rls_for_table("test_table")

                    # Verify that policy generator was called
                    mock_generator.generate_disable_rls_sql.assert_called_once_with(
                        "test_table"
                    )

                    # Verify that SQL statement was executed (check call count and args)
                    assert mock_op.execute.call_count == 1
                    call_args = mock_op.execute.call_args
                    assert call_args is not None
                    # Check that the SQL statement matches
                    executed_sql = str(call_args[0][0])
                    assert (
                        "ALTER TABLE test_table DISABLE ROW LEVEL SECURITY"
                        in executed_sql
                    )

                    # Verify that success logging was called
                    mock_logger.info.assert_called_once_with(
                        "Disabled RLS for table: test_table"
                    )

    def test_create_rls_policies_for_all_registered_tables_with_tables(self):
        """Test creating RLS policies for all registered tables when tables exist."""
        with patch("app.alembic.rls_policies.logger"):
            with patch("app.alembic.rls_policies.rls_registry") as mock_registry:
                with patch(
                    "app.alembic.rls_policies.create_rls_policies_for_table"
                ) as mock_create_policies:
                    # Mock the registry to return a dictionary of table names
                    mock_registry.get_registered_tables.return_value = {
                        "table1": {},
                        "table2": {},
                        "table3": {},
                    }

                    # Call the function
                    create_rls_policies_for_all_registered_tables()

                    # Verify that create_rls_policies_for_table was called for each table
                    assert mock_create_policies.call_count == 3
                    mock_create_policies.assert_any_call("table1")
                    mock_create_policies.assert_any_call("table2")
                    mock_create_policies.assert_any_call("table3")

    def test_create_rls_policies_for_all_registered_tables_no_tables(self):
        """Test creating RLS policies when no tables are registered."""
        with patch("app.alembic.rls_policies.logger") as mock_logger:
            with patch("app.alembic.rls_policies.rls_registry") as mock_registry:
                with patch(
                    "app.alembic.rls_policies.create_rls_policies_for_table"
                ) as mock_create_policies:
                    # Mock the registry to return an empty dictionary
                    mock_registry.get_registered_tables.return_value = {}

                    # Call the function
                    create_rls_policies_for_all_registered_tables()

                    # Verify that logging was called
                    mock_logger.info.assert_called_once_with(
                        "No RLS-scoped tables registered"
                    )

                    # Verify that create_rls_policies_for_table was not called
                    mock_create_policies.assert_not_called()

    def test_drop_rls_policies_for_all_registered_tables_with_tables(self):
        """Test dropping RLS policies for all registered tables when tables exist."""
        with patch("app.alembic.rls_policies.logger"):
            with patch("app.alembic.rls_policies.rls_registry") as mock_registry:
                with patch(
                    "app.alembic.rls_policies.drop_rls_policies_for_table"
                ) as mock_drop_policies:
                    # Mock the registry to return a dictionary of table names
                    mock_registry.get_registered_tables.return_value = {
                        "table1": {},
                        "table2": {},
                    }

                    # Call the function
                    drop_rls_policies_for_all_registered_tables()

                    # Verify that drop_rls_policies_for_table was called for each table
                    assert mock_drop_policies.call_count == 2
                    mock_drop_policies.assert_any_call("table1")
                    mock_drop_policies.assert_any_call("table2")

    def test_drop_rls_policies_for_all_registered_tables_no_tables(self):
        """Test dropping RLS policies when no tables are registered."""
        with patch("app.alembic.rls_policies.logger") as mock_logger:
            with patch("app.alembic.rls_policies.rls_registry") as mock_registry:
                with patch(
                    "app.alembic.rls_policies.drop_rls_policies_for_table"
                ) as mock_drop_policies:
                    # Mock the registry to return an empty dictionary
                    mock_registry.get_registered_tables.return_value = {}

                    # Call the function
                    drop_rls_policies_for_all_registered_tables()

                    # Verify that logging was called
                    mock_logger.info.assert_called_once_with(
                        "No RLS-scoped tables registered"
                    )

                    # Verify that drop_rls_policies_for_table was not called
                    mock_drop_policies.assert_not_called()

    def test_check_rls_enabled_for_table_success(self):
        """Test checking if RLS is enabled for a table successfully."""
        with patch("app.alembic.rls_policies.logger"):
            with patch("app.alembic.rls_policies.policy_generator") as mock_generator:
                with patch("app.alembic.rls_policies.op") as mock_op:
                    # Mock the policy generator to return SQL statement
                    mock_sql_statement = "SELECT relrowsecurity FROM pg_class WHERE relname = 'test_table';"
                    mock_generator.check_rls_enabled_sql.return_value = (
                        mock_sql_statement
                    )

                    # Mock the result to return True
                    mock_result = Mock()
                    mock_result.first.return_value = (True,)
                    mock_op.get_bind.return_value.execute.return_value = mock_result

                    # Call the function
                    result = check_rls_enabled_for_table("test_table")

                    # Verify the result
                    assert result is True

                    # Verify that policy generator was called
                    mock_generator.check_rls_enabled_sql.assert_called_once_with(
                        "test_table"
                    )

                    # Verify that the query was executed
                    mock_op.get_bind.assert_called_once()

    def test_check_rls_enabled_for_table_failure(self):
        """Test checking if RLS is enabled for a table when it fails."""
        with patch("app.alembic.rls_policies.logger") as mock_logger:
            with patch("app.alembic.rls_policies.policy_generator") as mock_generator:
                with patch("app.alembic.rls_policies.op"):
                    # Mock the policy generator to raise an exception
                    mock_generator.check_rls_enabled_sql.side_effect = Exception(
                        "Query failed"
                    )

                    # Call the function
                    result = check_rls_enabled_for_table("test_table")

                    # Verify the result is False
                    assert result is False

                    # Verify that error logging was called
                    mock_logger.error.assert_called_once_with(
                        "Failed to check RLS status for table test_table: Query failed"
                    )

    def test_upgrade_rls_policies_when_rls_disabled(self):
        """Test that RLS policy upgrade is skipped when RLS is disabled."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = False

            with patch("app.alembic.rls_policies.logger") as mock_logger:
                with patch("app.alembic.rls_policies.rls_registry"):
                    with patch(
                        "app.alembic.rls_policies.drop_rls_policies_for_table"
                    ) as mock_drop:
                        with patch(
                            "app.alembic.rls_policies.create_rls_policies_for_table"
                        ) as mock_create:
                            # Call the function
                            upgrade_rls_policies()

                            # Verify that logging was called
                            mock_logger.info.assert_called_once_with(
                                "RLS disabled, skipping policy upgrade"
                            )

                            # Verify that drop and create were not called
                            mock_drop.assert_not_called()
                            mock_create.assert_not_called()

    def test_upgrade_rls_policies_success(self):
        """Test successful RLS policy upgrade."""
        with patch("app.alembic.rls_policies.settings") as mock_settings:
            mock_settings.RLS_ENABLED = True

            with patch("app.alembic.rls_policies.logger"):
                with patch("app.alembic.rls_policies.rls_registry") as mock_registry:
                    with patch(
                        "app.alembic.rls_policies.drop_rls_policies_for_table"
                    ) as mock_drop:
                        with patch(
                            "app.alembic.rls_policies.create_rls_policies_for_table"
                        ) as mock_create:
                            # Mock the registry to return a dictionary of table names
                            mock_registry.get_registered_tables.return_value = {
                                "table1": {},
                                "table2": {},
                            }

                            # Call the function
                            upgrade_rls_policies()

                            # Verify that drop and create were called for each table
                            assert mock_drop.call_count == 2
                            assert mock_create.call_count == 2
                            mock_drop.assert_any_call("table1")
                            mock_drop.assert_any_call("table2")
                            mock_create.assert_any_call("table1")
                            mock_create.assert_any_call("table2")

    def test_downgrade_rls_policies_success(self):
        """Test successful RLS policy downgrade."""
        with patch("app.alembic.rls_policies.logger"):
            with patch("app.alembic.rls_policies.rls_registry") as mock_registry:
                with patch(
                    "app.alembic.rls_policies.drop_rls_policies_for_table"
                ) as mock_drop:
                    with patch(
                        "app.alembic.rls_policies.disable_rls_for_table"
                    ) as mock_disable:
                        # Mock the registry to return a dictionary of table names
                        mock_registry.get_registered_tables.return_value = {
                            "table1": {},
                            "table2": {},
                        }

                        # Call the function
                        downgrade_rls_policies()

                        # Verify that drop and disable were called for each table
                        assert mock_drop.call_count == 2
                        assert mock_disable.call_count == 2
                        mock_drop.assert_any_call("table1")
                        mock_drop.assert_any_call("table2")
                        mock_disable.assert_any_call("table1")
                        mock_disable.assert_any_call("table2")

    def test_setup_rls_for_new_table(self):
        """Test setting up RLS for a new table."""
        with patch("app.alembic.rls_policies.enable_rls_for_table") as mock_enable:
            with patch(
                "app.alembic.rls_policies.create_rls_policies_for_table"
            ) as mock_create:
                # Call the function
                setup_rls_for_new_table("test_table")

                # Verify that enable_rls_for_table was called
                mock_enable.assert_called_once_with("test_table")

                # Verify that create_rls_policies_for_table was called
                mock_create.assert_called_once_with("test_table")

    def test_teardown_rls_for_removed_table(self):
        """Test tearing down RLS for a removed table."""
        with patch("app.alembic.rls_policies.disable_rls_for_table") as mock_disable:
            with patch(
                "app.alembic.rls_policies.drop_rls_policies_for_table"
            ) as mock_drop:
                # Call the function
                teardown_rls_for_removed_table("test_table")

                # Verify that drop_rls_policies_for_table was called
                mock_drop.assert_called_once_with("test_table")

                # Verify that disable_rls_for_table was called
                mock_disable.assert_called_once_with("test_table")
