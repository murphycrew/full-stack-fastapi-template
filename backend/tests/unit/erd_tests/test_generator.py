"""
Unit tests for ERD Generator module.

Tests the core ERD generation functionality including model discovery,
metadata extraction, relationship generation, and Mermaid output.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from erd import (
    EntityDefinition,
    ERDGenerator,
    FieldMetadata,
    ModelMetadata,
    RelationshipDefinition,
    RelationshipMetadata,
)


class TestERDGenerator:
    """Test ERD Generator core functionality."""

    def test_initialization(self):
        """Test ERD Generator initialization with default parameters."""
        generator = ERDGenerator()

        assert generator.models_path == "app/models.py"
        assert generator.output_path == "../docs/database/erd.mmd"
        assert generator.generated_models == {}
        assert generator.model_discovery is not None
        assert generator.validator is not None
        assert generator.mermaid_validator is not None

    def test_initialization_custom_paths(self):
        """Test ERD Generator initialization with custom paths."""
        generator = ERDGenerator(
            models_path="custom/models.py", output_path="custom/output.mmd"
        )

        assert generator.models_path == "custom/models.py"
        assert generator.output_path == "custom/output.mmd"

    def test_generate_entities(self):
        """Test entity generation from model metadata."""
        generator = ERDGenerator()

        # Mock generated models
        user_metadata = ModelMetadata(
            class_name="User",
            table_name="USER",
            file_path=Path("app/models.py"),
            line_number=10,
            fields=[
                FieldMetadata(name="id", type_hint="uuid.UUID", is_primary_key=True),
                FieldMetadata(name="email", type_hint="str", is_primary_key=False),
            ],
            relationships=[],
            constraints=[],
        )

        generator.generated_models = {"User": user_metadata}

        entities = generator._generate_entities()

        assert len(entities) == 1
        assert entities[0].name == "USER"
        assert len(entities[0].fields) == 2
        assert entities[0].fields[0].name == "id"
        assert entities[0].fields[0].is_primary_key is True

    def test_generate_relationships(self):
        """Test relationship generation with bidirectional deduplication."""
        generator = ERDGenerator()

        # Create mock models with bidirectional relationship
        user_metadata = ModelMetadata(
            class_name="User",
            table_name="USER",
            file_path=Path("app/models.py"),
            line_number=10,
            fields=[],
            relationships=[
                RelationshipMetadata(
                    field_name="items",
                    target_model="Item",
                    relationship_type="one-to-many",
                    back_populates="owner",
                    foreign_key_field=None,
                    cascade=None,
                )
            ],
            constraints=[],
        )

        item_metadata = ModelMetadata(
            class_name="Item",
            table_name="ITEM",
            file_path=Path("app/models.py"),
            line_number=20,
            fields=[],
            relationships=[
                RelationshipMetadata(
                    field_name="owner",
                    target_model="User",
                    relationship_type="many-to-one",
                    back_populates="items",
                    foreign_key_field="owner_id",
                    cascade=None,
                )
            ],
            constraints=[],
        )

        generator.generated_models = {"User": user_metadata, "Item": item_metadata}

        relationships = generator._generate_relationships()

        # Should only generate one relationship (the one-to-many direction)
        assert len(relationships) == 1
        assert relationships[0].from_entity == "USER"
        assert relationships[0].to_entity == "ITEM"
        assert relationships[0].relationship_type.value == "1:N"

    def test_is_bidirectional_relationship(self):
        """Test bidirectional relationship detection."""
        generator = ERDGenerator()

        # Create mock relationship metadata
        user_rel = RelationshipMetadata(
            field_name="items",
            target_model="Item",
            relationship_type="one-to-many",
            back_populates="owner",
            foreign_key_field=None,
            cascade=None,
        )

        item_rel = RelationshipMetadata(
            field_name="owner",
            target_model="User",
            relationship_type="many-to-one",
            back_populates="items",
            foreign_key_field="owner_id",
            cascade=None,
        )

        item_model = ModelMetadata(
            class_name="Item",
            table_name="ITEM",
            file_path=Path("app/models.py"),
            line_number=20,
            fields=[],
            relationships=[item_rel],
            constraints=[],
        )

        # Test bidirectional detection
        is_bidirectional = generator._is_bidirectional_relationship(
            user_rel, item_model
        )
        assert is_bidirectional is True

        # Test non-bidirectional relationship
        non_bidirectional_rel = RelationshipMetadata(
            field_name="other_field",
            target_model="OtherModel",
            relationship_type="many-to-one",
            back_populates=None,
            foreign_key_field=None,
            cascade=None,
        )

        is_bidirectional2 = generator._is_bidirectional_relationship(
            non_bidirectional_rel, item_model
        )
        assert is_bidirectional2 is False

    def test_generate_mermaid_code(self):
        """Test Mermaid code generation."""
        generator = ERDGenerator()

        # Mock entities
        entities = [
            EntityDefinition(name="USER", fields=[], description="User entity"),
            EntityDefinition(name="ITEM", fields=[], description="Item entity"),
        ]

        # Mock relationships
        relationships = [
            RelationshipDefinition(
                from_entity="USER",
                to_entity="ITEM",
                relationship_type=None,  # Will be set by the class
                from_cardinality=None,
                to_cardinality=None,
            )
        ]

        mermaid_code = generator._generate_mermaid_code(entities, relationships)

        assert "erDiagram" in mermaid_code
        assert "USER {" in mermaid_code
        assert "ITEM {" in mermaid_code

    @patch.object(ERDGenerator, "_discover_models")
    def test_generate_erd_failure(self, mock_discover):
        """Test ERD generation failure handling."""
        generator = ERDGenerator()

        # Mock discovery to raise exception
        mock_discover.side_effect = Exception("Model discovery failed")

        with pytest.raises(Exception) as exc_info:
            generator.generate_erd()

        assert "ERD generation failed" in str(exc_info.value)
        assert "Model discovery failed" in str(exc_info.value)

    def test_find_target_model(self):
        """Test target model finding for foreign key fields."""
        generator = ERDGenerator()

        # Test with _id suffix
        target = generator._find_target_model("owner_id")
        assert target == "Owner"

        # Test with user_id suffix
        target = generator._find_target_model("user_id")
        assert target == "User"

        # Test without _id suffix
        target = generator._find_target_model("name")
        assert target is None
