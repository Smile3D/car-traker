"""add lead_source to clients

Revision ID: 5e5066963765
Revises: 1318e09fa3b1
Create Date: 2026-08-04 09:34:26.471610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e5066963765'
down_revision: Union[str, Sequence[str], None] = '1318e09fa3b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('clients', sa.Column('lead_source', sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('clients', 'lead_source')
