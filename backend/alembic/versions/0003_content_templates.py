"""content templates

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "html_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_type_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("token_names", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_html_templates_name"), "html_templates", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_html_templates_name"), table_name="html_templates")
    op.drop_table("html_templates")
