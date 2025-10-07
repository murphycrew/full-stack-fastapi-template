from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings, parse_cors


class TestConfigCoverage:
    """Test config.py coverage for missing lines."""

    def test_parse_cors_with_list(self):
        """Test parse_cors with list input (covers line 21-22)."""
        result = parse_cors(["http://localhost:3000", "http://localhost:8000"])
        assert result == ["http://localhost:3000", "http://localhost:8000"]

    def test_parse_cors_with_invalid_type(self):
        """Test parse_cors with invalid type (covers line 23)."""
        with pytest.raises(ValueError):
            parse_cors(123)  # Invalid type

    def test_config_validation_in_production(self):
        """Test config validation in production (covers line 120)."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            with pytest.raises(ValidationError):
                # This should raise ValidationError due to default secrets in production
                Settings(SECRET_KEY="changethis", POSTGRES_PASSWORD="changethis")

    def test_rls_enabled_property(self):
        """Test rls_enabled computed property (covers line 141)."""
        settings = Settings(
            RLS_ENABLED=True,
            RLS_APP_USER="test_user",
            RLS_MAINTENANCE_ADMIN="test_admin",
        )
        assert settings.rls_enabled is True

    def test_rls_maintenance_database_uri_property(self):
        """Test rls_maintenance_database_uri computed property (covers line 162)."""
        settings = Settings()
        uri = settings.rls_maintenance_database_uri
        assert str(uri).startswith("postgresql+psycopg://")
