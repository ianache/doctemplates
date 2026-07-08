"""document designs

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    columns = {column["name"] for column in inspector.get_columns("static_pdf_assets")}
    if "document_type_id" not in columns:
        op.add_column("static_pdf_assets", sa.Column("document_type_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_static_pdf_assets_document_type_id_document_types",
            "static_pdf_assets",
            "document_types",
            ["document_type_id"],
            ["id"],
        )

    if not inspector.has_table("document_designs"):
        op.create_table(
            "document_designs",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("document_type_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_by_id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "status IN ('draft', 'active')",
                name="ck_document_design_status",
            ),
            sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("document_design_pages"):
        op.create_table(
            "document_design_pages",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("design_id", sa.Uuid(), nullable=False),
            sa.Column("block_type", sa.String(), nullable=False),
            sa.Column("content_id", sa.Uuid(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "block_type IN ('html_template', 'static_pdf')",
                name="ck_design_page_block_type",
            ),
            sa.ForeignKeyConstraint(["design_id"], ["document_designs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if inspector.has_table("document_design_pages"):
        op.drop_table("document_design_pages")
    if inspector.has_table("document_designs"):
        op.drop_table("document_designs")

    columns = {column["name"] for column in inspector.get_columns("static_pdf_assets")}
    if "document_type_id" in columns:
        op.drop_constraint(
            "fk_static_pdf_assets_document_type_id_document_types",
            "static_pdf_assets",
            type_="foreignkey",
        )
        op.drop_column("static_pdf_assets", "document_type_id")
