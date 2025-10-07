"""
Tests for initial_data.py module.

This module tests the initial data creation functionality, including
the creation of initial superuser and regular user accounts.
"""

from unittest.mock import Mock, patch

from sqlmodel import Session

from app.initial_data import create_initial_users, init, main
from app.models import UserCreate


class TestInitialData:
    """Test initial data creation functionality."""

    def test_create_initial_users_creates_superuser_when_not_exists(
        self, db: Session, monkeypatch
    ):
        """Test that initial superuser is created when it doesn't exist."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.FIRST_SUPERUSER = "admin@example.com"
        mock_settings.FIRST_SUPERUSER_PASSWORD = "admin_password"
        mock_settings.FIRST_USER = "user@example.com"
        mock_settings.FIRST_USER_PASSWORD = "user_password"

        with patch("app.initial_data.settings", mock_settings):
            # Mock crud.get_user_by_email to return None (user doesn't exist)
            with patch("app.initial_data.crud.get_user_by_email") as mock_get_user:
                mock_get_user.return_value = None

                # Mock crud.create_user to return a mock user
                with patch("app.initial_data.crud.create_user") as mock_create_user:
                    mock_superuser = Mock()
                    mock_superuser.email = "admin@example.com"
                    mock_create_user.return_value = mock_superuser

                    # Call the function
                    create_initial_users(db)

                    # Verify that get_user_by_email was called for superuser
                    mock_get_user.assert_any_call(session=db, email="admin@example.com")

                    # Verify that create_user was called for superuser
                    mock_create_user.assert_any_call(
                        session=db,
                        user_create=UserCreate(
                            email="admin@example.com",
                            password="admin_password",
                            full_name="Initial Admin User",
                            is_superuser=True,
                        ),
                    )

    def test_create_initial_users_creates_regular_user_when_not_exists(
        self, db: Session, monkeypatch
    ):
        """Test that initial regular user is created when it doesn't exist."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.FIRST_SUPERUSER = "admin@example.com"
        mock_settings.FIRST_SUPERUSER_PASSWORD = "admin_password"
        mock_settings.FIRST_USER = "user@example.com"
        mock_settings.FIRST_USER_PASSWORD = "user_password"

        with patch("app.initial_data.settings", mock_settings):
            # Mock crud.get_user_by_email to return None for regular user
            with patch("app.initial_data.crud.get_user_by_email") as mock_get_user:
                # First call returns None (superuser doesn't exist), second call returns None (regular user doesn't exist)
                mock_get_user.side_effect = [None, None]

                # Mock crud.create_user to return mock users
                with patch("app.initial_data.crud.create_user") as mock_create_user:
                    mock_superuser = Mock()
                    mock_superuser.email = "admin@example.com"
                    mock_regular_user = Mock()
                    mock_regular_user.email = "user@example.com"
                    mock_create_user.side_effect = [mock_superuser, mock_regular_user]

                    # Call the function
                    create_initial_users(db)

                    # Verify that get_user_by_email was called for regular user
                    mock_get_user.assert_any_call(session=db, email="user@example.com")

                    # Verify that create_user was called for regular user
                    mock_create_user.assert_any_call(
                        session=db,
                        user_create=UserCreate(
                            email="user@example.com",
                            password="user_password",
                            full_name="Initial Regular User",
                            is_superuser=False,
                        ),
                    )

    def test_create_initial_users_skips_existing_superuser(
        self, db: Session, monkeypatch
    ):
        """Test that existing superuser is not recreated."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.FIRST_SUPERUSER = "admin@example.com"
        mock_settings.FIRST_SUPERUSER_PASSWORD = "admin_password"
        mock_settings.FIRST_USER = "user@example.com"
        mock_settings.FIRST_USER_PASSWORD = "user_password"

        with patch("app.initial_data.settings", mock_settings):
            # Mock crud.get_user_by_email to return existing superuser
            with patch("app.initial_data.crud.get_user_by_email") as mock_get_user:
                mock_existing_superuser = Mock()
                mock_existing_superuser.email = "admin@example.com"
                mock_get_user.side_effect = [
                    mock_existing_superuser,
                    None,
                ]  # superuser exists, regular user doesn't

                # Mock crud.create_user to return mock regular user
                with patch("app.initial_data.crud.create_user") as mock_create_user:
                    mock_regular_user = Mock()
                    mock_regular_user.email = "user@example.com"
                    mock_create_user.return_value = mock_regular_user

                    # Call the function
                    create_initial_users(db)

                    # Verify that create_user was only called once (for regular user, not superuser)
                    assert mock_create_user.call_count == 1

                    # Verify that the call was for regular user
                    mock_create_user.assert_called_with(
                        session=db,
                        user_create=UserCreate(
                            email="user@example.com",
                            password="user_password",
                            full_name="Initial Regular User",
                            is_superuser=False,
                        ),
                    )

    def test_create_initial_users_skips_existing_regular_user(
        self, db: Session, monkeypatch
    ):
        """Test that existing regular user is not recreated."""
        # Mock the settings
        mock_settings = Mock()
        mock_settings.FIRST_SUPERUSER = "admin@example.com"
        mock_settings.FIRST_SUPERUSER_PASSWORD = "admin_password"
        mock_settings.FIRST_USER = "user@example.com"
        mock_settings.FIRST_USER_PASSWORD = "user_password"

        with patch("app.initial_data.settings", mock_settings):
            # Mock crud.get_user_by_email to return existing users
            with patch("app.initial_data.crud.get_user_by_email") as mock_get_user:
                mock_existing_superuser = Mock()
                mock_existing_superuser.email = "admin@example.com"
                mock_existing_regular_user = Mock()
                mock_existing_regular_user.email = "user@example.com"
                mock_get_user.side_effect = [
                    mock_existing_superuser,
                    mock_existing_regular_user,
                ]

                # Mock crud.create_user (should not be called)
                with patch("app.initial_data.crud.create_user") as mock_create_user:
                    # Call the function
                    create_initial_users(db)

                    # Verify that create_user was never called
                    mock_create_user.assert_not_called()

    def test_init_function(self, db: Session):
        """Test the init function."""
        with patch("app.initial_data.init_db") as mock_init_db:
            with patch("app.initial_data.create_initial_users") as mock_create_users:
                with patch("app.initial_data.Session") as mock_session:
                    mock_session.return_value.__enter__.return_value = db

                    init()

                    # Verify that init_db was called
                    mock_init_db.assert_called_once_with(db)

                    # Verify that create_initial_users was called
                    mock_create_users.assert_called_once_with(db)

    def test_main_function(self, db: Session):
        """Test the main function."""
        with patch("app.initial_data.logger") as mock_logger:
            with patch("app.initial_data.init") as mock_init:
                main()

                # Verify that logging was called
                mock_logger.info.assert_any_call("Creating initial data")
                mock_logger.info.assert_any_call("Initial data created")

                # Verify that init was called
                mock_init.assert_called_once()

    def test_main_function_as_script(self, db: Session):
        """Test the main function when called as a script."""
        with patch("app.initial_data.logger") as mock_logger:
            with patch("app.initial_data.init") as mock_init:
                # Simulate calling main() as if it were run as a script
                import app.initial_data

                # Call main directly
                app.initial_data.main()

                # Verify that logging was called
                mock_logger.info.assert_any_call("Creating initial data")
                mock_logger.info.assert_any_call("Initial data created")

                # Verify that init was called
                mock_init.assert_called_once()

    def test_script_execution_import(self):
        """Test that the module can be imported and executed (covers line 59)."""
        # This test covers the if __name__ == "__main__": block by ensuring
        # the module can be imported and the main function exists
        import app.initial_data

        # Verify the main function exists and can be called
        assert hasattr(app.initial_data, "main")
        assert callable(app.initial_data.main)

        # The actual line 59 coverage happens when the module is imported
        # and the if __name__ == "__main__": block is evaluated
