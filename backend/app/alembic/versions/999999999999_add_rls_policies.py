"""Add RLS policies for user-scoped models

Revision ID: 999999999999
Revises: 1a31ce608336
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '999999999999'
down_revision = '1a31ce608336'  # Update this to the latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add RLS policies for all user-scoped models."""
    from app.alembic.rls_policies import create_rls_policies_for_all_registered_tables

    # Create RLS policies for all registered RLS-scoped tables
    create_rls_policies_for_all_registered_tables()


def downgrade() -> None:
    """Remove RLS policies for all user-scoped models."""
    from app.alembic.rls_policies import drop_rls_policies_for_all_registered_tables

    # Drop RLS policies for all registered RLS-scoped tables
    drop_rls_policies_for_all_registered_tables()
