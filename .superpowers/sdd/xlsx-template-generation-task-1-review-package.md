# Task 1 Review Package
## Git Diff
diff --git a/backend/app/models/__init__.py b/backend/app/models/__init__.py
index 93b23d9..759499b 100644
--- a/backend/app/models/__init__.py
+++ b/backend/app/models/__init__.py
@@ -3,9 +3,11 @@ from app.models.session import Session
 from app.models.document_type import DocumentType, DocumentTypeField, DocumentTypeMetadataDefinition
 from app.models.content_template import HtmlTemplate
 from app.models.static_pdf_asset import StaticPdfAsset
+from app.models.xlsx_template import XlsxTemplate
 from app.models.document_design import DocumentDesign, DocumentDesignPage
 from app.models.document_issuance import DocumentIssuance
 from app.models.document_tracelog import DocumentTracelog
+from app.models.template_ai_proposal import HtmlTemplateAiProposal
 
 __all__ = [
     "User",
@@ -15,8 +17,10 @@ __all__ = [
     "DocumentTypeMetadataDefinition",
     "HtmlTemplate",
     "StaticPdfAsset",
+    "XlsxTemplate",
     "DocumentDesign",
     "DocumentDesignPage",
     "DocumentIssuance",
     "DocumentTracelog",
+    "HtmlTemplateAiProposal",
 ]
diff --git a/backend/app/models/document_design.py b/backend/app/models/document_design.py
index fd94237..26d58cc 100644
--- a/backend/app/models/document_design.py
+++ b/backend/app/models/document_design.py
@@ -9,6 +9,7 @@ from app.db import Base
 
 DESIGN_STATUSES = ("draft", "active", "superseded")
 DESIGN_BLOCK_TYPES = ("html_template", "static_pdf")
+DESIGN_OUTPUT_FORMATS = ("pdf", "xlsx")
 
 
 class DocumentDesign(Base):
@@ -33,6 +34,10 @@ class DocumentDesign(Base):
     document_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_types.id"))
     name: Mapped[str]
     description: Mapped[str | None]
+    output_format: Mapped[str] = mapped_column(default="pdf")
+    xlsx_template_id: Mapped[uuid.UUID | None] = mapped_column(
+        ForeignKey("xlsx_templates.id"), nullable=True
+    )
     status: Mapped[str] = mapped_column(default="draft")
     version_group_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
     version_number: Mapped[int | None] = mapped_column(nullable=True)
@@ -41,6 +46,7 @@ class DocumentDesign(Base):
     created_at: Mapped[datetime] = mapped_column(server_default=func.now())
 
     document_type: Mapped["DocumentType"] = relationship()
+    xlsx_template: Mapped["XlsxTemplate | None"] = relationship()
     created_by: Mapped["User"] = relationship()
     pages: Mapped[list["DocumentDesignPage"]] = relationship(
         back_populates="design",
diff --git a/backend/app/models/document_issuance.py b/backend/app/models/document_issuance.py
index 1f31238..40e827d 100644
--- a/backend/app/models/document_issuance.py
+++ b/backend/app/models/document_issuance.py
@@ -19,6 +19,10 @@ class DocumentIssuance(Base):
         ForeignKey("document_designs.id", ondelete="RESTRICT")
     )
     storage_key: Mapped[str | None] = mapped_column(nullable=True, default=None)
+    output_format: Mapped[str] = mapped_column(default="pdf")
+    mime_type: Mapped[str | None] = mapped_column(nullable=True, default=None)
+    filename: Mapped[str | None] = mapped_column(nullable=True, default=None)
+    preview_storage_key: Mapped[str | None] = mapped_column(nullable=True, default=None)
 
     @property
     def file_path(self) -> str | None:
diff --git a/backend/app/models/document_type.py b/backend/app/models/document_type.py
index 431ec20..b918115 100644
--- a/backend/app/models/document_type.py
+++ b/backend/app/models/document_type.py
@@ -1,13 +1,14 @@
 import uuid
 from datetime import datetime
 
-from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
+from sqlalchemy import CheckConstraint, ForeignKey, JSON, UniqueConstraint, func
 from sqlalchemy.orm import Mapped, mapped_column, relationship
 
 from app.db import Base
 
 ALLOWED_FIELD_TYPES = ("string", "number", "date", "boolean")
 ALLOWED_METADATA_TYPES = ("text", "number", "date", "datetime", "boolean")
+DEFAULT_OUTPUT_FORMATS = ["pdf"]
 
 
 class DocumentType(Base):
@@ -16,6 +17,9 @@ class DocumentType(Base):
     id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
     name: Mapped[str] = mapped_column(index=True)
     description: Mapped[str | None]
+    allowed_output_formats: Mapped[list[str]] = mapped_column(
+        JSON, default=lambda: list(DEFAULT_OUTPUT_FORMATS)
+    )
     created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
     created_at: Mapped[datetime] = mapped_column(server_default=func.now())
 
diff --git a/backend/app/schemas/document_design.py b/backend/app/schemas/document_design.py
index fb593e0..a5bfc74 100644
--- a/backend/app/schemas/document_design.py
+++ b/backend/app/schemas/document_design.py
@@ -8,12 +8,16 @@ class DocumentDesignCreate(BaseModel):
     document_type_id: UUID
     name: str
     description: str | None = None
+    output_format: str = "pdf"
+    xlsx_template_id: UUID | None = None
     mock_data: dict | None = None
 
 
 class DocumentDesignUpdate(BaseModel):
     name: str
     description: str | None = None
+    output_format: str = "pdf"
+    xlsx_template_id: UUID | None = None
     mock_data: dict | None = None
 
 
@@ -61,6 +65,8 @@ class DocumentDesignListItem(BaseModel):
     id: UUID
     name: str
     description: str | None
+    output_format: str = "pdf"
+    xlsx_template_id: UUID | None = None
     status: str
     version_group_id: UUID | None = None
     version_number: int | None = None
@@ -77,6 +83,8 @@ class DocumentDesignDetail(BaseModel):
     id: UUID
     name: str
     description: str | None
+    output_format: str = "pdf"
+    xlsx_template_id: UUID | None = None
     status: str
     version_group_id: UUID | None = None
     version_number: int | None = None
diff --git a/backend/app/schemas/document_issuance.py b/backend/app/schemas/document_issuance.py
index bd274cf..6d4814f 100644
--- a/backend/app/schemas/document_issuance.py
+++ b/backend/app/schemas/document_issuance.py
@@ -20,6 +20,10 @@ class DocumentIssuanceOut(BaseModel):
     id: UUID
     design_version_id: UUID
     file_path: str | None = None
+    output_format: str = "pdf"
+    mime_type: str | None = None
+    filename: str | None = None
+    preview_storage_key: str | None = None
     user_id: UUID
     input_data: dict
     metadata_values: dict | None = None
@@ -38,6 +42,10 @@ class DocumentIssuanceLibraryItem(BaseModel):
     id: UUID
     design_version_id: UUID
     design_name: str
+    output_format: str = "pdf"
+    mime_type: str | None = None
+    filename: str | None = None
+    preview_storage_key: str | None = None
     status: str
     design_status: str
     design_version_number: int | None
diff --git a/backend/app/schemas/document_type.py b/backend/app/schemas/document_type.py
index b4a2462..4fd42ad 100644
--- a/backend/app/schemas/document_type.py
+++ b/backend/app/schemas/document_type.py
@@ -70,6 +70,7 @@ class DocumentTypeCreate(BaseModel):
     description: str | None = None
     fields: list[DocumentTypeFieldIn]
     metadata_definitions: list[DocumentTypeMetadataIn] = []
+    allowed_output_formats: list[str] = ["pdf"]
 
     @model_validator(mode="after")
     def validate_schema_structure(self) -> "DocumentTypeCreate":
@@ -139,6 +140,7 @@ class DocumentTypeListItem(BaseModel):
     id: UUID
     name: str
     description: str | None
+    allowed_output_formats: list[str] = ["pdf"]
     field_count: int
     created_by_email: str
     created_at: datetime
@@ -150,6 +152,7 @@ class DocumentTypeDetail(BaseModel):
     id: UUID
     name: str
     description: str | None
+    allowed_output_formats: list[str] = ["pdf"]
     fields: list[DocumentTypeFieldOut]
     metadata_definitions: list[DocumentTypeMetadataOut] = []
     created_by_email: str

## New Files

### backend/alembic/versions/0015_xlsx_generation.py
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
    op.drop_column("document_issuances", "output_format")

    op.drop_constraint(
        "fk_document_designs_xlsx_template_id",
        "document_designs",
        type_="foreignkey",
    )
    op.drop_column("document_designs", "xlsx_template_id")
    op.drop_column("document_designs", "output_format")

    op.drop_index("ix_xlsx_templates_name", table_name="xlsx_templates")
    op.drop_table("xlsx_templates")

    op.drop_column("document_types", "allowed_output_formats")

### backend/app/models/xlsx_template.py
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class XlsxTemplate(Base):
    __tablename__ = "xlsx_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None]
    storage_key: Mapped[str]
    original_filename: Mapped[str]
    detected_sheets: Mapped[list[dict]] = mapped_column(JSON, default=list)
    detected_tokens: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_slots: Mapped[list[dict]] = mapped_column(JSON, default=list)
    validation_warnings: Mapped[list[dict]] = mapped_column(JSON, default=list)
    mock_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document_type: Mapped["DocumentType"] = relationship()
    created_by: Mapped["User"] = relationship()

### backend/tests/test_xlsx_format_contract.py
from uuid import UUID

from app.models.document_design import DESIGN_OUTPUT_FORMATS
from app.models.document_type import DEFAULT_OUTPUT_FORMATS
from app.schemas.document_design import DocumentDesignCreate
from app.schemas.document_type import DocumentTypeCreate


def test_document_type_defaults_to_pdf_format():
    payload = DocumentTypeCreate(
        name="Contract",
        description=None,
        fields=[],
        metadata_definitions=[],
    )

    assert payload.allowed_output_formats == ["pdf"]
    assert DEFAULT_OUTPUT_FORMATS == ["pdf"]


def test_document_design_accepts_xlsx_output_format():
    payload = DocumentDesignCreate(
        document_type_id=UUID("00000000-0000-0000-0000-000000000001"),
        name="Workbook design",
        description=None,
        output_format="xlsx",
        xlsx_template_id=UUID("00000000-0000-0000-0000-000000000002"),
        mock_data=None,
    )

    assert payload.output_format == "xlsx"
    assert payload.xlsx_template_id is not None
    assert DESIGN_OUTPUT_FORMATS == ("pdf", "xlsx")
