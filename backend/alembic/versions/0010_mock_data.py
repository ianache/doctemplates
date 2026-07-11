"""add mock_data columns

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    # 1. Add mock_data to html_templates
    if inspector.has_table("html_templates") and not _has_column("html_templates", "mock_data"):
        op.add_column(
            "html_templates",
            sa.Column("mock_data", sa.JSON(), nullable=True),
        )

    # 2. Add mock_data to document_designs
    if inspector.has_table("document_designs") and not _has_column("document_designs", "mock_data"):
        op.add_column(
            "document_designs",
            sa.Column("mock_data", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())

    # 1. Drop mock_data from html_templates
    if inspector.has_table("html_templates") and _has_column("html_templates", "mock_data"):
        op.drop_column("html_templates", "mock_data")

    # 2. Drop mock_data from document_designs
    if inspector.has_table("document_designs") and _has_column("document_designs", "mock_data"):
        op.drop_column("document_designs", "mock_data")
