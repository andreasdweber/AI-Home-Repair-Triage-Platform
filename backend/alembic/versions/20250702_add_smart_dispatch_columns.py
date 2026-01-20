"""Add Smart Dispatch columns

Revision ID: 20250702_smart_dispatch
Revises: c14369910540
Create Date: 2025-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250702_smart_dispatch'
down_revision: Union[str, Sequence[str], None] = 'c14369910540'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new columns for Smart Dispatch and Audit features."""
    # Add columns to tickets table
    op.add_column('tickets', sa.Column('contact_info', sa.JSON(), nullable=True))
    op.add_column('tickets', sa.Column('category', sa.String(), nullable=True))
    op.add_column('tickets', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('tickets', sa.Column('priority', sa.String(), nullable=True))
    
    # Add columns to unit_baselines table
    op.add_column('unit_baselines', sa.Column('baseline_json', sa.JSON(), nullable=True))
    op.add_column('unit_baselines', sa.Column('last_updated', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove Smart Dispatch columns."""
    # Remove from tickets
    op.drop_column('tickets', 'contact_info')
    op.drop_column('tickets', 'category')
    op.drop_column('tickets', 'summary')
    op.drop_column('tickets', 'priority')
    
    # Remove from unit_baselines
    op.drop_column('unit_baselines', 'baseline_json')
    op.drop_column('unit_baselines', 'last_updated')
