from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.api.deps import get_current_user, get_read_only_admin_session
from app.models import User


class TestDepsCoverage:
    """Test deps.py coverage for missing lines."""

    @patch("app.api.deps.jwt.decode")
    def test_get_current_user_user_not_found(self, mock_jwt_decode):
        """Test get_current_user when user is not found (covers line 75)."""
        mock_session = Mock(spec=Session)
        mock_session.get.return_value = None
        mock_jwt_decode.return_value = {"sub": "nonexistent-user-id"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(session=mock_session, token="fake-token")

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @patch("app.api.deps.jwt.decode")
    def test_get_current_user_inactive_user(self, mock_jwt_decode):
        """Test get_current_user when user is inactive (covers line 77)."""
        mock_session = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.is_active = False
        mock_session.get.return_value = mock_user
        mock_jwt_decode.return_value = {"sub": "user-id"}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(session=mock_session, token="fake-token")

        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail

    def test_get_read_only_admin_session_non_superuser(self):
        """Test read-only admin session with non-superuser (covers line 111-114)."""
        mock_user = Mock(spec=User)
        mock_user.is_superuser = False

        with pytest.raises(HTTPException) as exc_info:
            list(get_read_only_admin_session(current_user=mock_user))

        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail

    def test_get_read_only_admin_session_superuser(self):
        """Test read-only admin session with superuser (covers line 115-117)."""
        mock_user = Mock(spec=User)
        mock_user.is_superuser = True
        mock_user.id = "user-id"

        with patch("app.api.deps.get_db_with_rls_context") as mock_get_db:
            mock_get_db.return_value = iter([])

            # Should not raise an exception
            list(get_read_only_admin_session(current_user=mock_user))

            # Verify that get_db_with_rls_context was called
            mock_get_db.assert_called_once_with(mock_user)

    def test_get_db_exception_handling(self):
        """Test get_db exception handling when clearing context (covers line 32)."""
        from app.api.deps import get_db

        with patch("app.api.deps.Session") as mock_session_class:
            mock_session = Mock(spec=Session)
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session_class.return_value.__exit__.return_value = None

            # Create a call counter to track execute calls
            call_count = 0

            def execute_side_effect(*_args, **_kwargs):
                nonlocal call_count
                call_count += 1
                # Only raise exception on the second call (in finally block)
                if call_count == 2:
                    raise Exception("Database error")
                return Mock()

            mock_session.execute.side_effect = execute_side_effect

            # Should not raise an exception due to try/except block
            list(get_db())

            # Verify that session.execute was called twice
            assert call_count == 2

    def test_get_db_with_rls_context_exception_handling(self):
        """Test get_db_with_rls_context exception handling when clearing context (covers line 52)."""
        from app.api.deps import get_db_with_rls_context

        with patch("app.api.deps.Session") as mock_session_class:
            mock_session = Mock(spec=Session)
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session_class.return_value.__exit__.return_value = None

            # Create a call counter to track execute calls
            call_count = 0

            def execute_side_effect(*_args, **_kwargs):
                nonlocal call_count
                call_count += 1
                # Only raise exception on the third call (in finally block)
                if call_count == 3:
                    raise Exception("Database error")
                return Mock()

            mock_session.execute.side_effect = execute_side_effect

            mock_user = Mock(spec=User)
            mock_user.id = "user-id"

            # Should not raise an exception due to try/except block
            list(get_db_with_rls_context(mock_user))

            # Verify that session.execute was called at least 3 times
            assert call_count >= 3
