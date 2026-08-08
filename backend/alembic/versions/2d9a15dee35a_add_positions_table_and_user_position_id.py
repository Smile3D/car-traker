"""add positions table and user position_id

Revision ID: 2d9a15dee35a
Revises: 995836afbb14
Create Date: 2026-07-29 10:47:27.725063

Adds the Position entity (owner-managed list of job titles per company) and
User.position_id, replacing what would otherwise be a free-text job title.

Note: there is no pre-existing free-text `position` column on `users` to
migrate data out of — that field was never carried over when the old
Employee table was merged into User during the company/employee refactor.
position_id is added fresh, nullable, with no data migration needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d9a15dee35a'
down_revision: Union[str, Sequence[str], None] = '995836afbb14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='positions_company_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='positions_pkey'),
    )

    op.add_column('users', sa.Column('position_id', sa.Integer(), nullable=True))
    op.create_foreign_key('users_position_id_fkey', 'users', 'positions', ['position_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('users_position_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'position_id')

    op.drop_table('positions')
