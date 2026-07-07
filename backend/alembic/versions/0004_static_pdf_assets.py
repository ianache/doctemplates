"""static pdf assets

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    table_exists = inspector.has_table("static_pdf_assets")
    if not table_exists:
        op.create_table(
            "static_pdf_assets",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("original_filename", sa.String(), nullable=False),
            sa.Column("stored_filename", sa.String(), nullable=False),
            sa.Column("stored_path", sa.String(), nullable=False),
            sa.Column("page_count", sa.Integer(), nullable=False),
            sa.Column("page_start", sa.Integer(), nullable=True),
            sa.Column("page_end", sa.Integer(), nullable=True),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("created_by_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    index_name = op.f("ix_static_pdf_assets_stored_filename")
    indexes = {index["name"] for index in inspector.get_indexes("static_pdf_assets")}
    if index_name not in indexes:
        op.create_index(
            index_name,
            "static_pdf_assets",
            ["stored_filename"],
            unique=False,
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("static_pdf_assets"):
        indexes = {index["name"] for index in inspector.get_indexes("static_pdf_assets")}
        index_name = op.f("ix_static_pdf_assets_stored_filename")
        if index_name in indexes:
            op.drop_index(index_name, table_name="static_pdf_assets")
        op.drop_table("static_pdf_assets")
