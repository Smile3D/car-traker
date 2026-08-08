"""backfill deal history date_added from live listings

Revision ID: f44b9e17d333
Revises: d4850a64aa9d
Create Date: 2026-07-31 10:40:16.308591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f44b9e17d333'
down_revision: Union[str, Sequence[str], None] = 'd4850a64aa9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Same recovery rule as the purchase_price/additional_expenses backfill
    (see 174440c586bb): only rows whose Listing still exists get a value:
    the JOIN itself excludes anything with listing_id NULL or pointing at an
    already-deleted row. Anything left NULL after this is genuinely gone."""
    op.execute(
        """
        UPDATE deal_history
        SET date_added = listings.date_added
        FROM listings
        WHERE deal_history.listing_id = listings.id
          AND deal_history.listing_id IS NOT NULL
          AND deal_history.date_added IS NULL
        """
    )


def downgrade() -> None:
    """No meaningful downgrade for a data recovery backfill."""
    pass
