"""add lead_source snapshot to deal_history

Revision ID: eb28b0f821ca
Revises: 5e5066963765
Create Date: 2026-08-04 09:34:26.787004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb28b0f821ca'
down_revision: Union[str, Sequence[str], None] = '5e5066963765'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('deal_history', sa.Column('seller_lead_source', sa.String(length=30), nullable=True))
    op.add_column('deal_history', sa.Column('buyer_lead_source', sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deal_history', 'buyer_lead_source')
    op.drop_column('deal_history', 'seller_lead_source')
