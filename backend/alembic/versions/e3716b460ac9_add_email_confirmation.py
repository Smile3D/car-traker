"""add email confirmation

Revision ID: e3716b460ac9
Revises: 107d512ffbb1
Create Date: 2026-08-05 15:58:29.927957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3716b460ac9'
down_revision: Union[str, Sequence[str], None] = '107d512ffbb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_confirmation_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='email_confirmation_tokens_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='email_confirmation_tokens_pkey'),
    )
    op.create_index(op.f('ix_email_confirmation_tokens_token'), 'email_confirmation_tokens', ['token'], unique=True)

    op.add_column('users', sa.Column('is_email_confirmed', sa.Boolean(), server_default='false', nullable=False))

    # Every user who registered before this feature shipped is already an
    # active, trusted account (owner, employee, or individual) — only
    # owners registering from here on go through the confirm-email flow.
    op.execute("UPDATE users SET is_email_confirmed = true")


def downgrade() -> None:
    op.drop_column('users', 'is_email_confirmed')
    op.drop_index(op.f('ix_email_confirmation_tokens_token'), table_name='email_confirmation_tokens')
    op.drop_table('email_confirmation_tokens')
