"""Create HTML template AI proposal history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "html_template_ai_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("template_id", sa.Uuid(), sa.ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("input_html", sa.Text(), nullable=False),
        sa.Column("input_css", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_css", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider", sa.String(), nullable=False, server_default="litellm"),
        sa.Column("model", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="invalid"),
        sa.Column("validation_errors", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False, server_default="[]"),
        sa.Column("is_applyable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('valid', 'invalid', 'failed')",
            name="ck_html_template_ai_proposal_status",
        ),
    )
    op.create_index("ix_html_template_ai_proposals_template_id", "html_template_ai_proposals", ["template_id"])
    op.create_index("ix_html_template_ai_proposals_created_by_id", "html_template_ai_proposals", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_html_template_ai_proposals_created_by_id", table_name="html_template_ai_proposals")
    op.drop_index("ix_html_template_ai_proposals_template_id", table_name="html_template_ai_proposals")
    op.drop_table("html_template_ai_proposals")
