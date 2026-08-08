"""add client_stages, migrate client stage to stage_id

Revision ID: 9a02c5ccb02f
Revises: 08b927892353
Create Date: 2026-07-28 06:01:51.214360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a02c5ccb02f'
down_revision: Union[str, Sequence[str], None] = '08b927892353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The stage sets that were previously hardcoded in app code (schemas/client.py's
# SELLER_STAGES/BUYER_STAGES + the uk.json clientStage.* labels). Existing
# clients only ever used these internal keys, so this is an exhaustive mapping.
SELLER_STAGE_MAPPING = [
    (0, 'first_contact', 'Перший контакт'),
    (1, 'inspection', 'Огляд авто'),
    (2, 'negotiation', 'Узгодження умов'),
    (3, 'accepted', 'Авто прийнято'),
    (4, 'deal_closed', 'Угода завершена'),
]
BUYER_STAGE_MAPPING = [
    (0, 'lead', 'Лід'),
    (1, 'viewing', 'Перегляд авто'),
    (2, 'negotiation', 'Переговори'),
    (3, 'reserved', 'Резерв'),
    (4, 'deal_closed', 'Угода закрита'),
    (5, 'declined', 'Відмова'),
]


def upgrade() -> None:
    # 1. New table for user-defined, per-(user, client_type) Kanban columns.
    op.create_table(
        'client_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('client_type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. Add stage_id as NULLABLE first — existing `clients` rows have no
    # value yet, so this can't be NOT NULL until after the data migration.
    op.add_column('clients', sa.Column('stage_id', sa.Integer(), nullable=True))
    op.create_foreign_key('clients_stage_id_fkey', 'clients', 'client_stages', ['stage_id'], ['id'])

    bind = op.get_bind()

    # 3a. For every user who already has clients, materialize the previously
    # hardcoded stage lists as real ClientStage rows (one full set per
    # client_type actually used by that user), so every existing client's
    # text `stage` value has a corresponding row to point stage_id at.
    for order, old_key, display_name in SELLER_STAGE_MAPPING:
        bind.execute(
            sa.text(
                """
                INSERT INTO client_stages (user_id, client_type, name, "order", created_at)
                SELECT DISTINCT c.user_id, 'seller', :display_name, :order, now()
                FROM clients c
                WHERE c.client_type = 'seller'
                """
            ),
            {"display_name": display_name, "order": order},
        )

    for order, old_key, display_name in BUYER_STAGE_MAPPING:
        bind.execute(
            sa.text(
                """
                INSERT INTO client_stages (user_id, client_type, name, "order", created_at)
                SELECT DISTINCT c.user_id, 'buyer', :display_name, :order, now()
                FROM clients c
                WHERE c.client_type = 'buyer'
                """
            ),
            {"display_name": display_name, "order": order},
        )

    # 3b. Point every client's stage_id at the newly created row matching
    # its own user_id + client_type + old text stage key. `negotiation` and
    # `deal_closed` exist in both mappings with different display names, so
    # each client_type is processed against its own list explicitly rather
    # than a combined one, to avoid cross-matching the wrong display name.
    for client_type, stage_mapping in (('seller', SELLER_STAGE_MAPPING), ('buyer', BUYER_STAGE_MAPPING)):
        for _, old_key, display_name in stage_mapping:
            bind.execute(
                sa.text(
                    """
                    UPDATE clients c
                    SET stage_id = cs.id
                    FROM client_stages cs
                    WHERE c.stage = :old_key
                      AND c.client_type = :client_type
                      AND cs.user_id = c.user_id
                      AND cs.client_type = :client_type
                      AND cs.name = :display_name
                    """
                ),
                {"old_key": old_key, "client_type": client_type, "display_name": display_name},
            )

    # 4. Every row must now have a stage_id — this fails loudly (instead of
    # silently corrupting data) if any client's old `stage` text value
    # didn't match one of the mappings above.
    op.alter_column('clients', 'stage_id', nullable=False)

    # 5. The text column is no longer needed.
    op.drop_column('clients', 'stage')


def downgrade() -> None:
    op.add_column('clients', sa.Column('stage', sa.VARCHAR(length=30), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE clients c
            SET stage = cs.name
            FROM client_stages cs
            WHERE cs.id = c.stage_id
            """
        )
    )

    op.alter_column('clients', 'stage', nullable=False)
    op.drop_constraint('clients_stage_id_fkey', 'clients', type_='foreignkey')
    op.drop_column('clients', 'stage_id')
    op.drop_table('client_stages')
