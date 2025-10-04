"""
Unit tests for ERD relationship detection and rendering.
"""

import pytest
from pathlib import Path
import tempfile
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from erd import (
    RelationshipDefinition,
    RelationshipManager,
    ModelDiscovery,
    RelationshipMetadata,
)
from erd.relationships import Cardinality, RelationshipType

class TestRelationshipDetection:
    """Test relationship detection from SQLModel definitions."""



    def test_mermaid_relationship_rendering(self):
        """Test Mermaid relationship syntax generation."""
        relationship = RelationshipDefinition(
            from_entity="USER",
            to_entity="ITEM",
            relationship_type=RelationshipType.ONE_TO_MANY,
            from_cardinality=Cardinality.ONE,
            to_cardinality=Cardinality.ZERO_OR_MORE,
            label="items -> owner"
        )
        
        mermaid_syntax = relationship.to_mermaid_relationship()
        expected = 'USER ||--o{ ITEM : items -> owner'
        assert mermaid_syntax == expected

    def test_relationship_manager(self):
        """Test relationship manager functionality."""
        manager = RelationshipManager()
        
        rel1 = RelationshipDefinition(
            from_entity="USER",
            to_entity="ITEM",
            relationship_type=RelationshipType.ONE_TO_MANY,
            from_cardinality=Cardinality.ONE,
            to_cardinality=Cardinality.ZERO_OR_MORE
        )
        
        manager.add_relationship(rel1)
        
        # Test getting relationships for entity
        user_rels = manager.get_relationships_for_entity("USER")
        assert len(user_rels) == 1
        
        item_rels = manager.get_relationships_for_entity("ITEM")
        assert len(item_rels) == 1
        
        # Test outgoing relationships
        outgoing = manager.get_outgoing_relationships("USER")
        assert len(outgoing) == 1
        assert outgoing[0].to_entity == "ITEM"
        
        # Test incoming relationships
        incoming = manager.get_incoming_relationships("ITEM")
        assert len(incoming) == 1
        assert incoming[0].from_entity == "USER"



class TestERDWithRelationships:
    """Test full ERD generation with relationships."""

    def test_erd_generation_with_relationships(self):
        """Test that ERD generation includes relationship lines."""
        from erd.generator import ERDGenerator
        
        # Create temporary model file
        model_content = '''
from sqlmodel import SQLModel, Field, Relationship
import uuid

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    items: list["Item"] = Relationship(back_populates="owner")

class Item(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    owner_id: uuid.UUID = Field(foreign_key="user.id")
    owner: User | None = Relationship(back_populates="items")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(model_content)
            temp_file = f.name
        
        try:
            generator = ERDGenerator(models_path=temp_file)
            mermaid_code = generator.generate_erd()
            
            # Should contain relationship line
            assert "USER ||--o{ ITEM" in mermaid_code or "ITEM }o--|| USER" in mermaid_code
            # Should not include relationship fields as regular fields
            assert "string items" not in mermaid_code
            assert "string owner" not in mermaid_code
            
        finally:
            os.unlink(temp_file)

    def test_relationship_field_filtering(self):
        """Test that relationship fields are filtered from entity field lists."""
        from erd.generator import ERDGenerator
        
        # Create temporary model file with relationship fields
        model_content = '''
from sqlmodel import SQLModel, Field, Relationship
import uuid

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    items: list["Item"] = Relationship(back_populates="owner")

class Item(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    owner_id: uuid.UUID = Field(foreign_key="user.id")
    owner: User | None = Relationship(back_populates="items")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(model_content)
            temp_file = f.name
        
        try:
            generator = ERDGenerator(models_path=temp_file)
            generator._discover_models()
            generator._extract_model_metadata()
            
            # Check that relationship fields are not in the field lists
            user_metadata = generator.generated_models["User"]
            item_metadata = generator.generated_models["Item"]
            
            user_field_names = [f.name for f in user_metadata.fields]
            item_field_names = [f.name for f in item_metadata.fields]
            
            # Relationship fields should not be in regular field lists
            assert "items" not in user_field_names
            assert "owner" not in item_field_names
            
            # But they should be in relationship lists
            assert len(user_metadata.relationships) >= 1
            assert len(item_metadata.relationships) >= 1
            
        finally:
            os.unlink(temp_file)
