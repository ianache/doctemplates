"""document metadata

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    # 1. Add metadata_values to document_issuances
    if inspector.has_table("document_issuances") and not _has_column(
        "document_issuances",
        "metadata_values",
    ):
        op.add_column(
            "document_issuances",
            sa.Column("metadata_values", sa.JSON(), nullable=True),
        )

    # 2. Create document_type_metadata_definitions table
    if not inspector.has_table("document_type_metadata_definitions"):
        op.create_table(
            "document_type_metadata_definitions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("document_type_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.CheckConstraint(
                "type IN ('text', 'number', 'date', 'datetime', 'boolean')",
                name="ck_document_type_metadata_type",
            ),
            sa.ForeignKeyConstraint(
                ["document_type_id"],
                ["document_types.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("document_type_id", "name", name="uq_document_type_metadata_name"),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())

    # 1. Drop document_type_metadata_definitions
    if inspector.has_table("document_type_metadata_definitions"):
        op.drop_table("document_type_metadata_definitions")

    # 2. Drop metadata_values from document_issuances
    if inspector.has_table("document_issuances") and _has_column("document_issuances", "metadata_values"):
        op.drop_column("document_issuances", "metadata_values")
