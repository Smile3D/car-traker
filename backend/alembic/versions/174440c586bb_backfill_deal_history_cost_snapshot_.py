"""backfill deal history cost snapshot from live listings

Revision ID: 174440c586bb
Revises: 0eae98084be4
Create Date: 2026-07-31 10:10:12.629971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '174440c586bb'
down_revision: Union[str, Sequence[str], None] = '0eae98084be4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Data-only migration: for DealHistory rows written before the cost
    snapshot columns existed, recover purchase_price/additional_expenses
    from the still-live Listing where one still exists. The JOIN itself is
    the correctness guard — it naturally excludes rows where listing_id is
    NULL (already SET NULL by the FK's ON DELETE behavior) and any listing_id
    that no longer matches a live row, so no separate existence check is
    needed. Rows whose Listing is already gone stay NULL: that cost data is
    genuinely unrecoverable, not fabricated by this migration.
    net_profit is a computed field (final_price - purchase_price -
    additional_expenses), never a stored column, so nothing to backfill
    there directly — it starts resolving correctly on its own for any row
    this backfills."""
    op.execute(
        """
        UPDATE deal_history
        SET purchase_price = listings.purchase_price,
            additional_expenses = listings.additional_expenses
        FROM listings
        WHERE deal_history.listing_id = listings.id
          AND deal_history.listing_id IS NOT NULL
          AND deal_history.purchase_price IS NULL
        """
    )


def downgrade() -> None:
    """No meaningful downgrade for a data recovery backfill — reverting
    would just re-discard cost data that is otherwise still recoverable at
    downgrade time, with no benefit."""
    pass
