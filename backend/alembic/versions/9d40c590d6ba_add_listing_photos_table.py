"""add listing photos table

Revision ID: 9d40c590d6ba
Revises: 2d9a15dee35a
Create Date: 2026-07-29 12:49:29.125891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d40c590d6ba'
down_revision: Union[str, Sequence[str], None] = '2d9a15dee35a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'listing_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('listing_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['listing_id'], ['listings.id'], name='listing_photos_listing_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='listing_photos_pkey'),
    )


def downgrade() -> None:
    op.drop_table('listing_photos')
