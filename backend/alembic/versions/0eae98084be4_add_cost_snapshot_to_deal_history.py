"""add cost snapshot to deal_history

Revision ID: 0eae98084be4
Revises: 5e0d9cdb69e0
Create Date: 2026-07-31 09:47:39.645164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0eae98084be4'
down_revision: Union[str, Sequence[str], None] = '5e0d9cdb69e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('deal_history', sa.Column('purchase_price', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('deal_history', sa.Column('additional_expenses', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deal_history', 'additional_expenses')
    op.drop_column('deal_history', 'purchase_price')
