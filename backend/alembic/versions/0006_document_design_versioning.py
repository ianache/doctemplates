"""document design versioning

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("document_designs")}

    if "version_group_id" not in columns:
        op.add_column("document_designs", sa.Column("version_group_id", sa.Uuid(), nullable=True))
    if "version_number" not in columns:
        op.add_column("document_designs", sa.Column("version_number", sa.Integer(), nullable=True))

    # Drop old check constraint and create new one
    op.drop_constraint("ck_document_design_status", "document_designs", type_="check")
    op.create_check_constraint(
        "ck_document_design_status",
        "document_designs",
        "status IN ('draft', 'active', 'superseded')",
    )

    # Perform the legacy backfill
    op.execute(
        "UPDATE document_designs SET version_group_id = id, version_number = 1 "
        "WHERE status = 'active' AND version_group_id IS NULL"
    )

    # Create partial unique indexes if they don't already exist
    existing_indexes = {index["name"] for index in inspector.get_indexes("document_designs")}
    if "uq_document_design_one_active_per_group" not in existing_indexes:
        op.create_index(
            "uq_document_design_one_active_per_group",
            "document_designs",
            ["version_group_id"],
            unique=True,
            postgresql_where=sa.text("status = 'active' AND version_group_id IS NOT NULL"),
        )
    if "uq_document_design_one_draft_per_group" not in existing_indexes:
        op.create_index(
            "uq_document_design_one_draft_per_group",
            "document_designs",
            ["version_group_id"],
            unique=True,
            postgresql_where=sa.text("status = 'draft' AND version_group_id IS NOT NULL"),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("document_designs")}
    
    if "uq_document_design_one_draft_per_group" in existing_indexes:
        op.drop_index("uq_document_design_one_draft_per_group", table_name="document_designs")
    if "uq_document_design_one_active_per_group" in existing_indexes:
        op.drop_index("uq_document_design_one_active_per_group", table_name="document_designs")

    op.drop_constraint("ck_document_design_status", "document_designs", type_="check")
    op.create_check_constraint(
        "ck_document_design_status",
        "document_designs",
        "status IN ('draft', 'active')",
    )

    columns = {column["name"] for column in inspector.get_columns("document_designs")}
    if "version_number" in columns:
        op.drop_column("document_designs", "version_number")
    if "version_group_id" in columns:
        op.drop_column("document_designs", "version_group_id")
