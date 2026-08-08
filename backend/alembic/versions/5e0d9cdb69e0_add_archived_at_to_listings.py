"""add archived_at to listings

Revision ID: 5e0d9cdb69e0
Revises: 3021a692a5b7
Create Date: 2026-07-31 08:23:01.856621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e0d9cdb69e0'
down_revision: Union[str, Sequence[str], None] = '3021a692a5b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listings', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill so existing sold/removed listings don't all sit at NULL and
    # get silently skipped by the cleanup job forever. Listings has no
    # updated_at column, so created_at is the documented fallback per spec.
    op.execute(
        """
        UPDATE listings
        SET archived_at = created_at
        WHERE status IN ('sold', 'removed') AND archived_at IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('listings', 'archived_at')
