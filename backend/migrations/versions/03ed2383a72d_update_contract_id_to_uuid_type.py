"""Update all primary and foreign keys to UUID type

Revision ID: 03ed2383a72d
Revises: 157088439244
Create Date: 2025-10-09 23:25:54.605918

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '03ed2383a72d'
down_revision: Union[str, None] = '157088439244'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop all foreign key constraints first
    op.drop_constraint('alerts_obligation_id_fkey', 'alerts', type_='foreignkey')
    op.drop_constraint('alerts_contract_id_fkey', 'alerts', type_='foreignkey')
    op.drop_constraint('obligations_contract_id_fkey', 'obligations', type_='foreignkey')

    # Alter primary and foreign key columns for all tables
    # Contracts
    op.alter_column('contracts', 'id',
               existing_type=sa.VARCHAR(),
               type_=postgresql.UUID(as_uuid=True),
               existing_nullable=False,
               postgresql_using='id::uuid')

    # Obligations
    op.alter_column('obligations', 'id',
               existing_type=sa.VARCHAR(),
               type_=postgresql.UUID(as_uuid=True),
               existing_nullable=False,
               postgresql_using='id::uuid')
    op.alter_column('obligations', 'contract_id',
               existing_type=sa.VARCHAR(),
               type_=postgresql.UUID(as_uuid=True),
               postgresql_using='contract_id::uuid')

    # Alerts
    op.alter_column('alerts', 'id',
               existing_type=sa.VARCHAR(),
               type_=postgresql.UUID(as_uuid=True),
               existing_nullable=False,
               postgresql_using='id::uuid')
    op.alter_column('alerts', 'contract_id',
               existing_type=sa.VARCHAR(),
               type_=postgresql.UUID(as_uuid=True),
               postgresql_using='contract_id::uuid')
    op.alter_column('alerts', 'obligation_id',
               existing_type=sa.VARCHAR(),
               type_=postgresql.UUID(as_uuid=True),
               postgresql_using='obligation_id::uuid')

    # Recreate all foreign key constraints
    op.create_foreign_key('obligations_contract_id_fkey', 'obligations', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('alerts_contract_id_fkey', 'alerts', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('alerts_obligation_id_fkey', 'alerts', 'obligations', ['obligation_id'], ['id'])


def downgrade() -> None:
    # This downgrade is complex; a full restore from backup would be better in production.
    op.drop_constraint('alerts_obligation_id_fkey', 'alerts', type_='foreignkey')
    op.drop_constraint('alerts_contract_id_fkey', 'alerts', type_='foreignkey')
    op.drop_constraint('obligations_contract_id_fkey', 'obligations', type_='foreignkey')

    # Revert columns to VARCHAR
    op.alter_column('alerts', 'obligation_id', type_=sa.VARCHAR(), existing_type=postgresql.UUID(as_uuid=True))
    op.alter_column('alerts', 'contract_id', type_=sa.VARCHAR(), existing_type=postgresql.UUID(as_uuid=True))
    op.alter_column('alerts', 'id', type_=sa.VARCHAR(), existing_type=postgresql.UUID(as_uuid=True))
    op.alter_column('obligations', 'contract_id', type_=sa.VARCHAR(), existing_type=postgresql.UUID(as_uuid=True))
    op.alter_column('obligations', 'id', type_=sa.VARCHAR(), existing_type=postgresql.UUID(as_uuid=True))
    op.alter_column('contracts', 'id', type_=sa.VARCHAR(), existing_type=postgresql.UUID(as_uuid=True))

    # Recreate foreign keys
    op.create_foreign_key('obligations_contract_id_fkey', 'obligations', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('alerts_contract_id_fkey', 'alerts', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('alerts_obligation_id_fkey', 'alerts', 'obligations', ['obligation_id'], ['id'])