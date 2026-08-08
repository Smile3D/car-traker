"""add co_founder role check constraint

Revision ID: 7cf31cce2380
Revises: b7699ff44960
Create Date: 2026-08-07 22:22:58.246551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cf31cce2380'
down_revision: Union[str, Sequence[str], None] = 'b7699ff44960'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_role_valid",
        "users",
        "role IN ('owner', 'co_founder', 'employee')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role_valid", "users", type_="check")
