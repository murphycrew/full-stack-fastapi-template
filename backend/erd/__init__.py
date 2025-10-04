"""
ERD Package - Entity Relationship Diagram generation from SQLModel definitions.

This package provides functionality to automatically generate Mermaid ERD diagrams
from SQLModel class definitions, including validation and output formatting.

Main Components:
- generator: Main ERD generation logic
- models: Data structures for model metadata
- validation: ERD validation and error checking
- discovery: SQLModel introspection and parsing
- output: ERD output formatting and file handling
- entities: Entity definition structures
- fields: Field definition structures
- relationships: Relationship definition and management
- mermaid_validator: Mermaid syntax validation

Usage:
    from erd import ERDGenerator

    generator = ERDGenerator()
    mermaid_code = generator.generate_erd()
"""

from .discovery import ModelDiscovery
from .entities import EntityDefinition
from .generator import ERDGenerator
from .mermaid_validator import MermaidValidator
from .models import (
    ConstraintMetadata,
    FieldMetadata,
    ModelMetadata,
    RelationshipMetadata,
)
from .output import ERDOutput
from .relationships import RelationshipDefinition, RelationshipManager
from .validation import (
    ERDValidator,
    ErrorSeverity,
    ValidationConfig,
    ValidationError,
    ValidationMode,
    ValidationResult,
)

__version__ = "1.0.0"
__all__ = [
    "ERDGenerator",
    "FieldMetadata",
    "ModelMetadata",
    "RelationshipMetadata",
    "ConstraintMetadata",
    "ERDValidator",
    "ValidationResult",
    "ValidationError",
    "ErrorSeverity",
    "ValidationMode",
    "ValidationConfig",
    "ERDOutput",
    "EntityDefinition",
    "RelationshipDefinition",
    "RelationshipManager",
    "ModelDiscovery",
    "MermaidValidator",
]
