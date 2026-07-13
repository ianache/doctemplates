"""async_issuance_jobs

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-13 06:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, Sequence[str], None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop check constraint 'ck_document_issuance_status'
    op.drop_constraint('ck_document_issuance_status', 'document_issuances', type_='check')

    # 2. Re-create constraint with 'queued', 'processing', 'success', 'failure'
    op.create_check_constraint(
        'ck_document_issuance_status',
        'document_issuances',
        "status IN ('queued', 'processing', 'success', 'failure')"
    )

    # 3. Make storage_key column nullable
    op.alter_column('document_issuances', 'storage_key', nullable=True)

    # 4. Add columns celery_task_id, error_message, queued_at, started_at, completed_at, retry_count
    op.add_column('document_issuances', sa.Column('celery_task_id', sa.String(), nullable=True))
    op.add_column('document_issuances', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('document_issuances', sa.Column('queued_at', sa.DateTime(), nullable=True))
    op.add_column('document_issuances', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('document_issuances', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('document_issuances', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    # 1. Delete or normalize non-success/non-failure rows to satisfy previous constraint
    # We delete 'queued' and 'processing' rows or normalize them to 'failure' so that we don't break the constraint.
    # Marking queued/processing as failure ensures no active/orphan tasks are assumed success.
    op.execute("UPDATE document_issuances SET status = 'failure' WHERE status IN ('queued', 'processing')")

    # 2. Make sure storage_key is non-null for downgrade (since we're reverting to previous state)
    # If storage_key is null, we set a dummy or empty key or delete those records.
    # Let's delete records that have null storage_key to avoid constraint failure.
    op.execute("DELETE FROM document_issuances WHERE storage_key IS NULL")

    # 3. Revert storage_key to non-nullable
    op.alter_column('document_issuances', 'storage_key', nullable=False)

    # 4. Drop check constraint 'ck_document_issuance_status'
    op.drop_constraint('ck_document_issuance_status', 'document_issuances', type_='check')

    # 5. Re-create constraint with 'success', 'failure'
    op.create_check_constraint(
        'ck_document_issuance_status',
        'document_issuances',
        "status IN ('success', 'failure')"
    )

    # 6. Drop the columns
    op.drop_column('document_issuances', 'retry_count')
    op.drop_column('document_issuances', 'completed_at')
    op.drop_column('document_issuances', 'started_at')
    op.drop_column('document_issuances', 'queued_at')
    op.drop_column('document_issuances', 'error_message')
    op.drop_column('document_issuances', 'celery_task_id')
