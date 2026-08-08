"""add date_added to deal_history

Revision ID: d4850a64aa9d
Revises: 174440c586bb
Create Date: 2026-07-31 10:39:20.844353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4850a64aa9d'
down_revision: Union[str, Sequence[str], None] = '174440c586bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('deal_history', sa.Column('date_added', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deal_history', 'date_added')
