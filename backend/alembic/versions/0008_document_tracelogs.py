"""document tracelogs

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("document_issuances") and not _has_column(
        "document_issuances",
        "status",
    ):
        op.add_column(
            "document_issuances",
            sa.Column("status", sa.String(), server_default="success", nullable=False),
        )
        op.create_check_constraint(
            "ck_document_issuance_status",
            "document_issuances",
            "status IN ('success', 'failure')",
        )
        op.alter_column("document_issuances", "status", server_default=None)

    if not inspector.has_table("document_tracelogs"):
        op.create_table(
            "document_tracelogs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("issuance_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "event_type IN ('generation', 'download', 'share')",
                name="ck_document_tracelog_event_type",
            ),
            sa.ForeignKeyConstraint(
                ["issuance_id"],
                ["document_issuances.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_document_tracelogs_issuance_id",
            "document_tracelogs",
            ["issuance_id"],
        )
        op.create_index("ix_document_tracelogs_user_id", "document_tracelogs", ["user_id"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("document_tracelogs"):
        op.drop_index("ix_document_tracelogs_user_id", table_name="document_tracelogs")
        op.drop_index("ix_document_tracelogs_issuance_id", table_name="document_tracelogs")
        op.drop_table("document_tracelogs")

    if inspector.has_table("document_issuances") and _has_column("document_issuances", "status"):
        op.drop_constraint(
            "ck_document_issuance_status",
            "document_issuances",
            type_="check",
        )
        op.drop_column("document_issuances", "status")
