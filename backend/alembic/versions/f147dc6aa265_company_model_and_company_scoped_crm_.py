"""company model and company scoped crm data

Revision ID: f147dc6aa265
Revises: 3ca6ee515cb3
Create Date: 2026-07-28 21:14:36.827507

Introduces Company as the new owner of all CRM data (listings, clients,
client_stages, telegram_integrations), replacing the old "everything
belongs to user_id" model with "everything belongs to company_id, and a
company has an owner plus employees (users with company_id set)".

Steps, in order:
  1. Create `companies`.
  2. Add `users.company_id` / `role` / `is_active` (nullable company_id/role
     for now, since not every user belongs to a company).
  3. Data migration: for every existing business user, create a Company
     from their company_name/business_phone/business_tax_id, and set
     company_id + role='owner' on that user.
  4. Destroy all existing CRM rows (clients, listings, client_stages,
     telegram_integrations, employees) — this is test data with no
     company_id to backfill, and preserving it was explicitly out of scope.
  5. Repoint listings/clients/client_stages/telegram_integrations from
     user_id to company_id (NOT NULL — safe now that the tables are empty),
     and repoint clients.employee_id from employees.id to users.id.
  6. Drop the old `employees` table and the old company_name/
     business_phone/business_tax_id columns on `users`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f147dc6aa265'
down_revision: Union[str, Sequence[str], None] = '3ca6ee515cb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. companies
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('business_phone', sa.String(length=50), nullable=True),
        sa.Column('business_tax_id', sa.String(length=50), nullable=True),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name='companies_owner_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='companies_pkey'),
    )

    # 2. users.company_id / role / is_active
    op.add_column('users', sa.Column('company_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.create_foreign_key('users_company_id_fkey', 'users', 'companies', ['company_id'], ['id'])

    # 3. Data migration: existing business users become company owners.
    op.execute(
        """
        INSERT INTO companies (name, business_phone, business_tax_id, owner_user_id, created_at)
        SELECT company_name, business_phone, business_tax_id, id, now()
        FROM users
        WHERE account_type = 'business'
        """
    )
    op.execute(
        """
        UPDATE users
        SET company_id = companies.id, role = 'owner'
        FROM companies
        WHERE companies.owner_user_id = users.id
        """
    )

    # 4. Destroy existing CRM data (test data, no company_id to backfill).
    # Order respects FKs: clients references listings/client_stages/employees.
    op.execute('DELETE FROM clients')
    op.execute('DELETE FROM listings')
    op.execute('DELETE FROM client_stages')
    op.execute('DELETE FROM telegram_integrations')

    op.drop_constraint('clients_employee_id_fkey', 'clients', type_='foreignkey')
    op.drop_constraint('clients_user_id_fkey', 'clients', type_='foreignkey')
    op.drop_constraint('employees_user_id_fkey', 'employees', type_='foreignkey')
    op.drop_table('employees')

    # 5. Repoint CRM ownership columns to company_id.
    op.add_column('client_stages', sa.Column('company_id', sa.Integer(), nullable=False))
    op.create_foreign_key('client_stages_company_id_fkey', 'client_stages', 'companies', ['company_id'], ['id'])
    op.drop_column('client_stages', 'user_id')

    op.add_column('clients', sa.Column('company_id', sa.Integer(), nullable=False))
    op.create_foreign_key('clients_company_id_fkey', 'clients', 'companies', ['company_id'], ['id'])
    op.create_foreign_key('clients_employee_id_fkey', 'clients', 'users', ['employee_id'], ['id'])
    op.drop_column('clients', 'user_id')

    op.add_column('listings', sa.Column('company_id', sa.Integer(), nullable=False))
    op.create_foreign_key('listings_company_id_fkey', 'listings', 'companies', ['company_id'], ['id'])
    op.drop_column('listings', 'user_id')

    op.add_column('telegram_integrations', sa.Column('company_id', sa.Integer(), nullable=False))
    op.create_unique_constraint('telegram_integrations_company_id_key', 'telegram_integrations', ['company_id'])
    op.create_foreign_key('telegram_integrations_company_id_fkey', 'telegram_integrations', 'companies', ['company_id'], ['id'])
    op.drop_column('telegram_integrations', 'user_id')

    # 6. Drop the old per-user company fields (now owned by Company).
    op.drop_column('users', 'business_phone')
    op.drop_column('users', 'company_name')
    op.drop_column('users', 'business_tax_id')


def downgrade() -> None:
    # Schema-only reversal — the CRM data destroyed in upgrade() is not
    # recoverable, and company profile fields are restored empty.
    op.add_column('users', sa.Column('business_tax_id', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('company_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('business_phone', sa.VARCHAR(length=50), autoincrement=False, nullable=True))

    op.drop_column('telegram_integrations', 'company_id')
    op.add_column('telegram_integrations', sa.Column('user_id', sa.Integer(), autoincrement=False, nullable=False))
    op.create_unique_constraint('telegram_integrations_user_id_key', 'telegram_integrations', ['user_id'])
    op.create_foreign_key('telegram_integrations_user_id_fkey', 'telegram_integrations', 'users', ['user_id'], ['id'])

    op.drop_column('listings', 'company_id')
    op.add_column('listings', sa.Column('user_id', sa.Integer(), autoincrement=False, nullable=False))
    op.create_foreign_key('listings_user_id_fkey', 'listings', 'users', ['user_id'], ['id'])

    op.drop_constraint('clients_employee_id_fkey', 'clients', type_='foreignkey')
    op.drop_column('clients', 'company_id')
    op.add_column('clients', sa.Column('user_id', sa.Integer(), autoincrement=False, nullable=False))
    op.create_foreign_key('clients_user_id_fkey', 'clients', 'users', ['user_id'], ['id'])

    op.drop_column('client_stages', 'company_id')
    op.add_column('client_stages', sa.Column('user_id', sa.Integer(), autoincrement=False, nullable=False))
    op.create_foreign_key('client_stages_user_id_fkey', 'client_stages', 'users', ['user_id'], ['id'])

    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('name', sa.Text(), autoincrement=False, nullable=False),
        sa.Column('phone', sa.Text(), autoincrement=False, nullable=False),
        sa.Column('email', sa.Text(), autoincrement=False, nullable=True),
        sa.Column('position', sa.Text(), autoincrement=False, nullable=False),
        sa.Column('notes', sa.Text(), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), autoincrement=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='employees_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='employees_pkey'),
    )
    op.create_foreign_key('clients_employee_id_fkey', 'clients', 'employees', ['employee_id'], ['id'])

    op.drop_constraint('users_company_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'role')
    op.drop_column('users', 'company_id')

    op.drop_table('companies')
