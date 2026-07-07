"""document types and document type fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_types_name"), "document_types", ["name"], unique=False)

    op.create_table(
        "document_type_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_type_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_type_id", "name", name="uq_document_type_field_name"),
        sa.CheckConstraint(
            "type IN ('string', 'number', 'date', 'boolean')",
            name="ck_document_type_field_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("document_type_fields")
    op.drop_index(op.f("ix_document_types_name"), table_name="document_types")
    op.drop_table("document_types")
