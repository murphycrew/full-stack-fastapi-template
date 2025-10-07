from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestUtilsRoutes:
    """Test utility routes."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/api/v1/utils/health-check/")
        assert response.status_code == 200
        assert response.json() is True

    @patch("app.api.routes.utils.send_email")
    @patch("app.api.routes.utils.generate_test_email")
    def test_test_email_success(
        self,
        mock_generate_test_email,
        mock_send_email,
        client: TestClient,
        superuser_token_headers,
    ):
        """Test successful test email sending."""
        # Mock the email generation
        mock_email_data = MagicMock()
        mock_email_data.subject = "Test Subject"
        mock_email_data.html_content = "<h1>Test Content</h1>"
        mock_generate_test_email.return_value = mock_email_data

        # Mock the email sending
        mock_send_email.return_value = None

        response = client.post(
            "/api/v1/utils/test-email/?email_to=test@example.com",
            headers=superuser_token_headers,
        )

        assert response.status_code == 201
        assert response.json() == {"message": "Test email sent"}

        # Verify mocks were called
        mock_generate_test_email.assert_called_once_with(email_to="test@example.com")
        mock_send_email.assert_called_once_with(
            email_to="test@example.com",
            subject="Test Subject",
            html_content="<h1>Test Content</h1>",
        )

    def test_test_email_requires_superuser(self, client: TestClient):
        """Test that test email endpoint requires superuser authentication."""
        response = client.post("/api/v1/utils/test-email/?email_to=test@example.com")
        assert response.status_code == 401
