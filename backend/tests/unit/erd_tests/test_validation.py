"""
Unit tests for ERD Validation module.

Tests the validation system for ERD generation including
model validation, ERD validation, and error handling.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from erd import ERDValidator, ErrorSeverity, ValidationError, ValidationResult


class TestValidationError:
    """Test ValidationError data structure."""

    def test_validation_error_creation(self):
        """Test ValidationError creation."""
        error = ValidationError(
            message="Test error message",
            severity="error",
            line_number=10,
            error_code="ERR001",
        )

        assert error.message == "Test error message"
        assert error.severity == "error"
        assert error.line_number == 10
        assert error.error_code == "ERR001"

    def test_validation_error_to_dict(self):
        """Test ValidationError to_dict conversion."""
        error = ValidationError(
            message="Test error", severity="error", line_number=5, error_code="ERR002"
        )

        error_dict = error.to_dict()

        assert error_dict["message"] == "Test error"
        assert error_dict["severity"] == "error"
        assert error_dict["line_number"] == 5
        assert error_dict["error_code"] == "ERR002"


class TestValidationResult:
    """Test ValidationResult data structure."""

    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult()

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors."""
        error = ValidationError(
            message="Test error", severity="error", line_number=10, error_code="ERR001"
        )

        result = ValidationResult()
        result.add_error(error)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0] == error

    def test_validation_result_with_warnings(self):
        """Test ValidationResult with warnings."""
        warning = ValidationError(
            message="Test warning",
            severity=ErrorSeverity.WARNING,
            line_number=15,
            error_code="WARN001",
        )

        result = ValidationResult()
        result.add_warning(warning)

        assert result.is_valid is True  # Warnings don't make result invalid
        assert len(result.warnings) == 1
        assert result.warnings[0] == warning

    def test_validation_result_to_dict(self):
        """Test ValidationResult to_dict conversion."""
        error = ValidationError(
            message="Test error", severity="error", line_number=10, error_code="ERR001"
        )

        warning = ValidationError(
            message="Test warning",
            severity=ErrorSeverity.WARNING,
            line_number=15,
            error_code="WARN001",
        )

        result = ValidationResult()
        result.add_error(error)
        result.add_warning(warning)

        result_dict = result.to_dict()

        assert result_dict["is_valid"] is False
        assert len(result_dict["errors"]) == 1
        assert len(result_dict["warnings"]) == 1
        assert result_dict["errors"][0]["message"] == "Test error"
        assert result_dict["warnings"][0]["message"] == "Test warning"


class TestERDValidator:
    """Test ERDValidator functionality."""

    def test_validator_initialization(self):
        """Test ERDValidator initialization."""
        validator = ERDValidator()

        assert validator is not None

    def test_validate_mermaid_syntax_success(self):
        """Test successful Mermaid syntax validation."""
        validator = ERDValidator()

        # Valid Mermaid ERD syntax
        erd_syntax = """erDiagram
    USER {
        uuid id PK
        string email
    }

    ITEM {
        uuid id PK
        uuid owner_id FK
    }

    USER ||--o{ ITEM : owns"""

        result = validator.validate_mermaid_syntax(erd_syntax)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_mermaid_syntax_missing_erdiagram(self):
        """Test Mermaid syntax validation with missing erDiagram declaration."""
        validator = ERDValidator()

        # Invalid syntax - missing erDiagram
        erd_syntax = """USER {
        uuid id PK
    }"""

        result = validator.validate_mermaid_syntax(erd_syntax)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "erDiagram" in result.errors[0].message

    def test_validate_all_success(self):
        """Test validate_all method with valid ERD."""
        validator = ERDValidator()

        # Valid ERD syntax
        erd_syntax = """erDiagram
    USER {
        uuid id PK
        string email
    }"""

        result = validator.validate_all(erd_syntax)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_all_with_errors(self):
        """Test validate_all method with invalid ERD."""
        validator = ERDValidator()

        # Invalid ERD syntax
        erd_syntax = """USER {
        uuid id PK
    }"""

        result = validator.validate_all(erd_syntax)

        assert result.is_valid is False
        assert len(result.errors) >= 1

    def test_validate_entities(self):
        """Test validation that entities exist in ERD."""
        validator = ERDValidator()

        # ERD with entities
        erd_syntax = """erDiagram
    USER {
        uuid id PK
    }

    ITEM {
        uuid id PK
    }"""

        result = validator.validate_entities(erd_syntax)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_entities_no_entities(self):
        """Test validation when no entities exist."""
        validator = ERDValidator()

        # ERD without entities
        erd_syntax = "erDiagram"

        result = validator.validate_entities(erd_syntax)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "no entities" in result.errors[0].message.lower()

    def test_validate_relationships(self):
        """Test validation that relationships exist in ERD."""
        validator = ERDValidator()

        # ERD with relationships
        erd_syntax = """erDiagram
    USER {
        uuid id PK
    }

    ITEM {
        uuid id PK
    }

    USER ||--o{ ITEM : owns"""

        # Parse relationships first
        relationships = validator._parse_relationships(erd_syntax)
        result = validator.validate_relationships(relationships)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_relationships_no_relationships(self):
        """Test validation when no relationships exist."""
        validator = ERDValidator()

        # ERD without relationships
        erd_syntax = """erDiagram
    USER {
        uuid id PK
    }"""

        # Parse relationships first
        relationships = validator._parse_relationships(erd_syntax)
        result = validator.validate_relationships(relationships)

        # This should be valid (entities can exist without relationships)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_mermaid_syntax_basic(self):
        """Test basic Mermaid syntax validation."""
        validator = ERDValidator()

        # Valid basic syntax
        erd_syntax = """erDiagram
    USER {
        uuid id PK
    }"""

        result = validator.validate_mermaid_syntax(erd_syntax)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_mermaid_syntax_complex(self):
        """Test complex Mermaid syntax validation."""
        validator = ERDValidator()

        # Complex but valid syntax
        erd_syntax = """erDiagram
    USER {
        uuid id PK
        string email UK
        boolean is_active
    }

    ITEM {
        uuid id PK
        string title
        uuid owner_id FK
    }

    USER ||--o{ ITEM : owns
    USER }o--|| ITEM : created_by"""

        result = validator.validate_mermaid_syntax(erd_syntax)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_parse_entities(self):
        """Test entity parsing from ERD."""
        validator = ERDValidator()

        # ERD with 2 entities
        erd_syntax = """erDiagram
    USER {
        uuid id PK
    }

    ITEM {
        uuid id PK
    }"""

        entities = validator._parse_entities(erd_syntax)
        assert len(entities) == 2
        assert any(entity.get("name") == "USER" for entity in entities)
        assert any(entity.get("name") == "ITEM" for entity in entities)

    def test_parse_relationships(self):
        """Test relationship parsing from ERD."""
        validator = ERDValidator()

        # ERD with 1 relationship
        erd_syntax = """erDiagram
    USER {
        uuid id PK
    }

    ITEM {
        uuid id PK
    }

    USER ||--o{ ITEM : owns"""

        relationships = validator._parse_relationships(erd_syntax)
        assert len(relationships) == 1
        assert relationships[0].get("from_entity") == "USER"
        assert relationships[0].get("to_entity") == "ITEM"
