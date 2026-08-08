"""add unique partial index for one buyer per listing

Revision ID: 1318e09fa3b1
Revises: f44b9e17d333
Create Date: 2026-08-02 14:10:47.844044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1318e09fa3b1'
down_revision: Union[str, Sequence[str], None] = 'f44b9e17d333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_clients_unique_buyer_per_listing', 'clients', ['listing_id'], unique=True, postgresql_where=sa.text("client_type = 'buyer'"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_clients_unique_buyer_per_listing', table_name='clients', postgresql_where=sa.text("client_type = 'buyer'"))
