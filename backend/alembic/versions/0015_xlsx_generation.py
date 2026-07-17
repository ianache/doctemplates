"""Add format-aware document contracts and XLSX templates."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_xlsx_generation"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.add_column(
        "document_types",
        sa.Column("allowed_output_formats", json_type, nullable=True),
    )
    op.execute("UPDATE document_types SET allowed_output_formats = '[\"pdf\"]'")
    op.alter_column("document_types", "allowed_output_formats", nullable=False)

    op.create_table(
        "xlsx_templates",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "document_type_id",
            sa.Uuid(),
            sa.ForeignKey("document_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("detected_sheets", json_type, nullable=False, server_default="[]"),
        sa.Column("detected_tokens", json_type, nullable=False, server_default="[]"),
        sa.Column("image_slots", json_type, nullable=False, server_default="[]"),
        sa.Column("validation_warnings", json_type, nullable=False, server_default="[]"),
        sa.Column("mock_data", json_type, nullable=True),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_xlsx_templates_name", "xlsx_templates", ["name"])

    op.add_column(
        "document_designs",
        sa.Column("output_format", sa.String(), nullable=True),
    )
    op.execute("UPDATE document_designs SET output_format = 'pdf'")
    op.alter_column("document_designs", "output_format", nullable=False)
    op.create_check_constraint(
        "ck_document_design_output_format",
        "document_designs",
        "output_format IN ('pdf', 'xlsx')",
    )
    op.add_column(
        "document_designs",
        sa.Column("xlsx_template_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_designs_xlsx_template_id",
        "document_designs",
        "xlsx_templates",
        ["xlsx_template_id"],
        ["id"],
    )

    op.add_column(
        "document_issuances",
        sa.Column("output_format", sa.String(), nullable=True),
    )
    op.execute("UPDATE document_issuances SET output_format = 'pdf'")
    op.alter_column("document_issuances", "output_format", nullable=False)
    op.create_check_constraint(
        "ck_document_issuance_output_format",
        "document_issuances",
        "output_format IN ('pdf', 'xlsx')",
    )
    op.add_column("document_issuances", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("document_issuances", sa.Column("filename", sa.String(), nullable=True))
    op.add_column(
        "document_issuances",
        sa.Column("preview_storage_key", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_issuances", "preview_storage_key")
    op.drop_column("document_issuances", "filename")
    op.drop_column("document_issuances", "mime_type")
    op.drop_constraint(
        "ck_document_issuance_output_format",
        "document_issuances",
        type_="check",
    )
    op.drop_column("document_issuances", "output_format")

    op.drop_constraint(
        "fk_document_designs_xlsx_template_id",
        "document_designs",
        type_="foreignkey",
    )
    op.drop_column("document_designs", "xlsx_template_id")
    op.drop_constraint(
        "ck_document_design_output_format",
        "document_designs",
        type_="check",
    )
    op.drop_column("document_designs", "output_format")

    op.drop_index("ix_xlsx_templates_name", table_name="xlsx_templates")
    op.drop_table("xlsx_templates")

    op.drop_column("document_types", "allowed_output_formats")
