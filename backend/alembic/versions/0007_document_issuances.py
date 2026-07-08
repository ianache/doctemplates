"""document issuances

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not inspector.has_table("document_issuances"):
        op.create_table(
            "document_issuances",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("design_version_id", sa.Uuid(), nullable=False),
            sa.Column("file_path", sa.String(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("input_data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["design_version_id"],
                ["document_designs.id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("document_issuances"):
        op.drop_table("document_issuances")
