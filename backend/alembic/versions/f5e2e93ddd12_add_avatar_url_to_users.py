"""add avatar_url to users

Revision ID: f5e2e93ddd12
Revises: e9d21866ea10
Create Date: 2026-08-04 11:51:35.104607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5e2e93ddd12'
down_revision: Union[str, Sequence[str], None] = 'e9d21866ea10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'avatar_url')
