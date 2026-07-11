"""add css column to html_templates

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    # Add css to html_templates
    if inspector.has_table("html_templates") and not _has_column("html_templates", "css"):
        op.add_column(
            "html_templates",
            sa.Column("css", sa.Text(), nullable=True, server_default=""),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())

    # Drop css from html_templates
    if inspector.has_table("html_templates") and _has_column("html_templates", "css"):
        op.drop_column("html_templates", "css")
