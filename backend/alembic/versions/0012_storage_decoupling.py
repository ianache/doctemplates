"""storage_decoupling

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-12 15:10:29.265106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column 'stored_path' to 'storage_key' on table 'static_pdf_assets'
    op.alter_column('static_pdf_assets', 'stored_path', new_column_name='storage_key')
    # Rename column 'file_path' to 'storage_key' on table 'document_issuances'
    op.alter_column('document_issuances', 'file_path', new_column_name='storage_key')
    
    # Migrate data: extract base filename
    # We match any characters that are not / or \ at the end of the string.
    # In PostgreSQL regex, [^/\\] matches any char except / or \.
    # Since we are using standard SQL regex, we write substring(storage_key from '[^/\\\\]+$').
    op.execute("UPDATE static_pdf_assets SET storage_key = substring(storage_key from '[^/\\\\]+$')")
    op.execute("UPDATE document_issuances SET storage_key = substring(storage_key from '[^/\\\\]+$')")


def downgrade() -> None:
    # Rename column 'storage_key' back to 'stored_path' on table 'static_pdf_assets'
    op.alter_column('static_pdf_assets', 'storage_key', new_column_name='stored_path')
    # Rename column 'storage_key' back to 'file_path' on table 'document_issuances'
    op.alter_column('document_issuances', 'storage_key', new_column_name='file_path')
