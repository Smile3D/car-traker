"""add on_service fields to listings

Revision ID: e9d21866ea10
Revises: eb28b0f821ca
Create Date: 2026-08-04 10:37:44.570688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9d21866ea10'
down_revision: Union[str, Sequence[str], None] = 'eb28b0f821ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listings', sa.Column('service_note', sa.Text(), nullable=True))
    op.add_column('listings', sa.Column('service_start_date', sa.Date(), nullable=True))
    op.add_column('listings', sa.Column('service_expected_end_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('listings', 'service_expected_end_date')
    op.drop_column('listings', 'service_start_date')
    op.drop_column('listings', 'service_note')
