"""add employee invites table

Revision ID: 1c02820b2c14
Revises: 9d40c590d6ba
Create Date: 2026-07-29 15:13:30.274441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c02820b2c14'
down_revision: Union[str, Sequence[str], None] = '9d40c590d6ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'employee_invites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='employee_invites_company_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='employee_invites_created_by_fkey'),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], name='employee_invites_position_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='employee_invites_pkey'),
    )
    op.create_index(op.f('ix_employee_invites_token'), 'employee_invites', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_employee_invites_token'), table_name='employee_invites')
    op.drop_table('employee_invites')
