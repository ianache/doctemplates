# XLSX Template Generation Final Review Package
 M backend/app/api/document_designs.py
 M backend/app/api/issuances.py
 M backend/app/models/document_design.py
 M backend/app/models/document_issuance.py
 M backend/app/models/document_type.py
 M backend/app/schemas/document_design.py
 M backend/app/schemas/document_issuance.py
 M backend/app/schemas/document_type.py
 M backend/app/services/design_validation.py
 M backend/app/services/issuance_jobs.py
 M backend/app/services/storage/local.py
 M backend/app/services/storage/s3.py
 M backend/app/workers/document_generation.py
 M backend/tests/test_async_generation_jobs.py
 M backend/tests/test_document_tracelogs.py
 M frontend/src/App.tsx
 M frontend/src/lib/documentDesigns.ts
 M frontend/src/lib/documentIssuances.ts
 M frontend/src/lib/documentTypes.ts
 M frontend/src/pages/AuthenticatedShell.tsx
 M frontend/src/pages/content/ContentLibraryPage.tsx
 M frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx
 M frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx
 M frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx
 M frontend/src/pages/document-types/DocumentTypeCreatePage.tsx
?? .superpowers/sdd/xlsx-template-generation-task-8-report.md
?? backend/alembic/versions/0015_xlsx_generation.py
?? backend/app/api/xlsx_templates.py
?? backend/app/models/xlsx_template.py
?? backend/app/schemas/xlsx_template.py
?? backend/app/services/document_generation.py
?? backend/app/services/xlsx_analysis.py
?? backend/app/services/xlsx_images.py
?? backend/app/services/xlsx_renderer.py
?? backend/tests/test_xlsx_analysis.py
?? backend/tests/test_xlsx_designs.py
?? backend/tests/test_xlsx_format_contract.py
?? backend/tests/test_xlsx_issuance_generation.py
?? backend/tests/test_xlsx_preview.py
?? backend/tests/test_xlsx_renderer.py
?? backend/tests/test_xlsx_templates_api.py
?? frontend/src/lib/xlsxTemplates.ts
?? frontend/src/pages/content/XlsxTemplateDetailPage.tsx
?? frontend/src/pages/content/XlsxTemplateUploadPage.tsx
?? frontend/src/pages/content/XlsxTemplatesPage.tsx
?? frontend/src/pages/content/components/XlsxPreviewGrid.tsx

## File: backend/alembic/versions/0015_xlsx_generation.py
```
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

```

## File: backend/app/models/xlsx_template.py
```
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

```

## File: backend/app/models/document_type.py
```
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ALLOWED_FIELD_TYPES = ("string", "number", "date", "boolean")
ALLOWED_METADATA_TYPES = ("text", "number", "date", "datetime", "boolean")
DEFAULT_OUTPUT_FORMATS = ["pdf"]


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None]
    allowed_output_formats: Mapped[list[str]] = mapped_column(
        JSON, default=lambda: list(DEFAULT_OUTPUT_FORMATS)
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    created_by: Mapped["User"] = relationship()
    fields: Mapped[list["DocumentTypeField"]] = relationship(
        back_populates="document_type",
        cascade="all, delete-orphan",
        order_by="DocumentTypeField.position",
    )
    metadata_definitions: Mapped[list["DocumentTypeMetadataDefinition"]] = relationship(
        back_populates="document_type",
        cascade="all, delete-orphan",
        order_by="DocumentTypeMetadataDefinition.name",
    )


class DocumentTypeField(Base):
    __tablename__ = "document_type_fields"
    __table_args__ = (
        UniqueConstraint("document_type_id", "name", name="uq_document_type_field_name"),
        CheckConstraint(
            f"type IN {ALLOWED_FIELD_TYPES!r}",
            name="ck_document_type_field_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="CASCADE")
    )
    name: Mapped[str]
    type: Mapped[str]
    description: Mapped[str | None]
    position: Mapped[int]

    document_type: Mapped["DocumentType"] = relationship(back_populates="fields")


class DocumentTypeMetadataDefinition(Base):
    __tablename__ = "document_type_metadata_definitions"
    __table_args__ = (
        UniqueConstraint("document_type_id", "name", name="uq_document_type_metadata_name"),
        CheckConstraint(
            f"type IN {ALLOWED_METADATA_TYPES!r}",
            name="ck_document_type_metadata_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="CASCADE")
    )
    name: Mapped[str]
    type: Mapped[str]
    required: Mapped[bool] = mapped_column(default=True)

    document_type: Mapped["DocumentType"] = relationship(back_populates="metadata_definitions")

```

## File: backend/app/models/document_design.py
```
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, JSON, func, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


DESIGN_STATUSES = ("draft", "active", "superseded")
DESIGN_BLOCK_TYPES = ("html_template", "static_pdf")
DESIGN_OUTPUT_FORMATS = ("pdf", "xlsx")


class DocumentDesign(Base):
    __tablename__ = "document_designs"
    __table_args__ = (
        CheckConstraint(f"status IN {DESIGN_STATUSES!r}", name="ck_document_design_status"),
        CheckConstraint(
            f"output_format IN {DESIGN_OUTPUT_FORMATS!r}",
            name="ck_document_design_output_format",
        ),
        Index(
            "uq_document_design_one_active_per_group",
            "version_group_id",
            unique=True,
            postgresql_where=text("status = 'active' AND version_group_id IS NOT NULL"),
        ),
        Index(
            "uq_document_design_one_draft_per_group",
            "version_group_id",
            unique=True,
            postgresql_where=text("status = 'draft' AND version_group_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_types.id"))
    name: Mapped[str]
    description: Mapped[str | None]
    output_format: Mapped[str] = mapped_column(default="pdf")
    xlsx_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("xlsx_templates.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(default="draft")
    version_group_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    version_number: Mapped[int | None] = mapped_column(nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    mock_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document_type: Mapped["DocumentType"] = relationship()
    xlsx_template: Mapped["XlsxTemplate | None"] = relationship()
    created_by: Mapped["User"] = relationship()
    pages: Mapped[list["DocumentDesignPage"]] = relationship(
        back_populates="design",
        cascade="all, delete-orphan",
        order_by="DocumentDesignPage.position",
    )


class DocumentDesignPage(Base):
    __tablename__ = "document_design_pages"
    __table_args__ = (
        CheckConstraint(f"block_type IN {DESIGN_BLOCK_TYPES!r}", name="ck_design_page_block_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    design_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_designs.id", ondelete="CASCADE")
    )
    block_type: Mapped[str]
    content_id: Mapped[uuid.UUID]
    position: Mapped[int]
    title: Mapped[str | None]
    notes: Mapped[str | None]
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    design: Mapped["DocumentDesign"] = relationship(back_populates="pages")

```

## File: backend/app/models/document_issuance.py
```
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


ISSUANCE_STATUSES = ("queued", "processing", "success", "failure")
ISSUANCE_OUTPUT_FORMATS = ("pdf", "xlsx")


class DocumentIssuance(Base):
    __tablename__ = "document_issuances"
    __table_args__ = (
        CheckConstraint(f"status IN {ISSUANCE_STATUSES!r}", name="ck_document_issuance_status"),
        CheckConstraint(
            f"output_format IN {ISSUANCE_OUTPUT_FORMATS!r}",
            name="ck_document_issuance_output_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    design_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_designs.id", ondelete="RESTRICT")
    )
    storage_key: Mapped[str | None] = mapped_column(nullable=True, default=None)
    output_format: Mapped[str] = mapped_column(default="pdf")
    mime_type: Mapped[str | None] = mapped_column(nullable=True, default=None)
    filename: Mapped[str | None] = mapped_column(nullable=True, default=None)
    preview_storage_key: Mapped[str | None] = mapped_column(nullable=True, default=None)

    @property
    def file_path(self) -> str | None:
        if not self.storage_key:
            return None
        from pathlib import Path
        if Path(self.storage_key).is_absolute():
            return self.storage_key
        from app.config import settings
        import os
        return os.path.join(settings.issuance_storage_root, self.storage_key)

    @file_path.setter
    def file_path(self, value: str | None) -> None:
        self.storage_key = value
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    input_data: Mapped[dict] = mapped_column(JSON)
    metadata_values: Mapped[dict | None] = mapped_column(JSON, default=None)
    status: Mapped[str] = mapped_column(default="queued")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    celery_task_id: Mapped[str | None] = mapped_column(nullable=True, default=None)
    error_message: Mapped[str | None] = mapped_column(nullable=True, default=None)
    queued_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)
    retry_count: Mapped[int] = mapped_column(default=0, server_default="0")

    design_version: Mapped["DocumentDesign"] = relationship()
    user: Mapped["User"] = relationship()
    tracelogs: Mapped[list["DocumentTracelog"]] = relationship(
        back_populates="issuance",
        cascade="all, delete-orphan",
        order_by="DocumentTracelog.created_at",
        passive_deletes=True,
    )

```

## File: backend/app/schemas/xlsx_template.py
```
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class XlsxTemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    document_type_name: str
    name: str
    description: str | None
    original_filename: str
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]
    mock_data: dict | None
    created_by_email: str
    created_at: datetime


class XlsxTemplateDetail(XlsxTemplateListItem):
    pass


class XlsxTemplatePreviewRequest(BaseModel):
    mock_data: dict | None = None


class XlsxPreviewCell(BaseModel):
    address: str
    value: str | int | float | bool | None
    style: dict = {}


class XlsxPreviewSheet(BaseModel):
    name: str
    max_row: int
    max_column: int
    merged_ranges: list[str]
    cells: list[XlsxPreviewCell]


class XlsxTemplatePreviewResponse(BaseModel):
    sheets: list[XlsxPreviewSheet]
    warnings: list[dict] = []

```

## File: backend/app/schemas/document_type.py
```
from datetime import datetime
from typing import Literal
from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, model_validator, field_validator

FieldType = Literal["string", "number", "date", "boolean"]
OutputFormat = Literal["pdf", "xlsx"]

PARENT_SEGMENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?$")
LEAF_SEGMENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")



class DocumentTypeFieldIn(BaseModel):
    name: str
    type: FieldType
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name_path(cls, v: str) -> str:
        if not v:
            raise ValueError("Field name cannot be empty")
        segments = v.split(".")
        if len(segments) > 5:
            raise ValueError("Field path depth cannot exceed 5 levels")
        for i, segment in enumerate(segments):
            if not segment:
                raise ValueError("Field path segments cannot be empty")
            if i < len(segments) - 1:
                if not PARENT_SEGMENT_RE.match(segment):
                    raise ValueError(f"Invalid parent path segment: '{segment}'")
            else:
                if not LEAF_SEGMENT_RE.match(segment):
                    raise ValueError(f"Invalid leaf path segment: '{segment}'")
        return v


class DocumentTypeFieldOut(DocumentTypeFieldIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


MetadataType = Literal["text", "number", "date", "datetime", "boolean"]


class DocumentTypeMetadataIn(BaseModel):
    name: str
    type: MetadataType
    required: bool = True

    @field_validator("name")
    @classmethod
    def validate_metadata_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Metadata name cannot be empty")
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(f"Invalid metadata name: '{v}'. Must be a valid identifier.")
        return v


class DocumentTypeMetadataOut(DocumentTypeMetadataIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class DocumentTypeCreate(BaseModel):
    name: str
    description: str | None = None
    fields: list[DocumentTypeFieldIn]
    metadata_definitions: list[DocumentTypeMetadataIn] = []
    allowed_output_formats: list[OutputFormat] = ["pdf"]

    @field_validator("allowed_output_formats")
    @classmethod
    def validate_allowed_output_formats(cls, values: list[OutputFormat]) -> list[OutputFormat]:
        if not values:
            raise ValueError("At least one output format must be allowed")
        if len(values) != len(set(values)):
            raise ValueError("Allowed output formats must be unique")
        return values

    @model_validator(mode="after")
    def validate_schema_structure(self) -> "DocumentTypeCreate":
        # 1. Check case-insensitive uniqueness of field names
        lower_names = [f.name.lower() for f in self.fields]
        if len(lower_names) != len(set(lower_names)):
            raise ValueError("Field names must be unique within a document type (case-insensitive)")

        # 2. Build the structural schema tree and detect conflicts
        root = {"type": "object", "children": {}}

        for field in self.fields:
            segments = field.name.split(".")
            current = root
            
            for idx, segment in enumerate(segments):
                is_last = (idx == len(segments) - 1)
                
                # Determine name and if it's a list
                if segment.endswith("[]"):
                    name = segment[:-2].lower()
                    is_list = True
                else:
                    name = segment.lower()
                    is_list = False
                
                # Check for structural conflict
                if is_last:
                    # Leaf segment
                    if name in current["children"]:
                        raise ValueError(f"Conflict: '{field.name}' collides with an existing field path or parent")
                    current["children"][name] = {
                        "type": "leaf",
                        "field_type": field.type
                    }
                else:
                    # Parent segment
                    if name in current["children"]:
                        existing = current["children"][name]
                        if is_list:
                            if existing["type"] != "list":
                                raise ValueError(f"Conflict: Path segment '{segment}' is declared as both a list and a non-list")
                            current = existing["element_node"]
                        else:
                            if existing["type"] != "object":
                                raise ValueError(f"Conflict: Path segment '{segment}' is declared as both an object and a non-object/leaf")
                            current = existing
                    else:
                        if is_list:
                            element_node = {"type": "object", "children": {}}
                            new_node = {
                                "type": "list",
                                "element_node": element_node
                            }
                            current["children"][name] = new_node
                            current = element_node
                        else:
                            new_node = {"type": "object", "children": {}}
                            current["children"][name] = new_node
                            current = new_node
        return self


class DocumentTypeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    allowed_output_formats: list[OutputFormat] = ["pdf"]
    field_count: int
    created_by_email: str
    created_at: datetime


class DocumentTypeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    allowed_output_formats: list[OutputFormat] = ["pdf"]
    fields: list[DocumentTypeFieldOut]
    metadata_definitions: list[DocumentTypeMetadataOut] = []
    created_by_email: str
    created_at: datetime

```

## File: backend/app/schemas/document_design.py
```
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.document_type import OutputFormat


class DocumentDesignCreate(BaseModel):
    document_type_id: UUID
    name: str
    description: str | None = None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    mock_data: dict | None = None


class DocumentDesignUpdate(BaseModel):
    name: str
    description: str | None = None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    mock_data: dict | None = None


class AddTemplatePage(BaseModel):
    template_id: UUID
    title: str | None = None
    notes: str | None = None
    config: dict | None = None


class AddStaticPdfPage(BaseModel):
    static_pdf_asset_id: UUID
    title: str | None = None
    notes: str | None = None
    config: dict | None = None


class ReorderDesignPages(BaseModel):
    page_ids: list[UUID]


class UpdateDesignPage(BaseModel):
    title: str | None = None
    notes: str | None = None
    config: dict | None = None


class DocumentDesignPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    block_type: str
    content_id: UUID
    position: int
    title: str | None
    notes: str | None
    config: dict
    snapshot: dict
    created_at: datetime


class DocumentDesignListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    status: str
    version_group_id: UUID | None = None
    version_number: int | None = None
    document_type_id: UUID
    document_type_name: str
    page_count: int
    created_by_email: str
    created_at: datetime


class DocumentDesignDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    output_format: OutputFormat = "pdf"
    xlsx_template_id: UUID | None = None
    status: str
    version_group_id: UUID | None = None
    version_number: int | None = None
    document_type_id: UUID
    document_type_name: str
    created_by_email: str
    created_at: datetime
    pages: list[DocumentDesignPageOut]
    warnings: list[str] = []
    mock_data: dict | None = None

```

## File: backend/app/schemas/document_issuance.py
```
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentTracelogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issuance_id: UUID
    event_type: str
    user_id: UUID | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime


class DocumentIssuanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_version_id: UUID
    file_path: str | None = None
    output_format: str = "pdf"
    mime_type: str | None = None
    filename: str | None = None
    preview_storage_key: str | None = None
    user_id: UUID
    input_data: dict
    metadata_values: dict | None = None
    status: str
    created_at: datetime

    celery_task_id: str | None = None
    error_message: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


class DocumentIssuanceLibraryItem(BaseModel):
    id: UUID
    design_version_id: UUID
    design_name: str
    output_format: str = "pdf"
    mime_type: str | None = None
    filename: str | None = None
    preview_storage_key: str | None = None
    status: str
    design_status: str
    design_version_number: int | None
    user_id: UUID
    generated_by_email: str
    input_data: dict
    metadata_values: dict | None = None
    created_at: datetime
    preview_url: str
    download_url: str

    celery_task_id: str | None = None
    error_message: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


class DocumentIssuanceShareOut(BaseModel):
    public_url: str

```

## File: backend/app/api/xlsx_templates.py
```
from io import BytesIO
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.dependencies import get_storage_provider
from app.models.document_type import DocumentType
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate
from app.schemas.xlsx_template import (
    XlsxTemplateDetail,
    XlsxTemplateListItem,
    XlsxTemplatePreviewRequest,
    XlsxTemplatePreviewResponse,
)
from app.services.storage.base import StorageProvider
from app.services.xlsx_analysis import analyze_xlsx_template
from app.services.xlsx_renderer import preview_xlsx_template


router = APIRouter(prefix="/api/xlsx-templates", tags=["xlsx-templates"])


def _reject_macro_enabled_workbook(workbook_bytes: bytes) -> None:
    try:
        with ZipFile(BytesIO(workbook_bytes)) as archive:
            names = {name.lower() for name in archive.namelist()}
            content_types = archive.read("[Content_Types].xml").decode("utf-8", errors="ignore").lower()
    except (BadZipFile, KeyError) as exc:
        raise HTTPException(status_code=400, detail="Invalid .xlsx file") from exc

    if (
        "xl/vbaproject.bin" in names
        or "vnd.ms-office.vbaproject" in content_types
        or "macroenabled" in content_types
    ):
        raise HTTPException(status_code=400, detail="Macro-enabled workbooks not supported")


def _detail(template: XlsxTemplate) -> XlsxTemplateDetail:
    return XlsxTemplateDetail(
        id=template.id,
        document_type_id=template.document_type_id,
        document_type_name=template.document_type.name,
        name=template.name,
        description=template.description,
        original_filename=template.original_filename,
        detected_sheets=list(template.detected_sheets or []),
        detected_tokens=list(template.detected_tokens or []),
        image_slots=list(template.image_slots or []),
        validation_warnings=list(template.validation_warnings or []),
        mock_data=template.mock_data,
        created_by_email=template.created_by.email,
        created_at=template.created_at,
    )


def _get_template(db: SQLAlchemySession, template_id: UUID) -> XlsxTemplate:
    template = (
        db.query(XlsxTemplate)
        .options(joinedload(XlsxTemplate.document_type), joinedload(XlsxTemplate.created_by))
        .filter(XlsxTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="XLSX template not found")
    return template


@router.post("", response_model=XlsxTemplateDetail, status_code=201)
def upload_xlsx_template(
    document_type_id: UUID = Form(...),
    name: str = Form(...),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> XlsxTemplateDetail:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    document_type = (
        db.query(DocumentType)
        .options(selectinload(DocumentType.fields))
        .filter(DocumentType.id == document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")

    workbook_bytes = file.file.read()
    _reject_macro_enabled_workbook(workbook_bytes)
    try:
        analysis = analyze_xlsx_template(workbook_bytes, {field.name for field in document_type.fields})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid .xlsx file: {exc}") from exc

    storage_key = f"{uuid4()}.xlsx"
    storage_provider.save(storage_key, workbook_bytes, category="xlsx_templates")
    template = XlsxTemplate(
        document_type=document_type,
        name=name,
        description=description,
        storage_key=storage_key,
        original_filename=file.filename,
        detected_sheets=analysis.detected_sheets,
        detected_tokens=analysis.detected_tokens,
        image_slots=analysis.image_slots,
        validation_warnings=analysis.validation_warnings,
        created_by=user,
    )
    db.add(template)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage_provider.delete(storage_key, category="xlsx_templates")
        except Exception:
            pass
        raise
    db.refresh(template)
    db.refresh(document_type)
    db.refresh(user)
    return _detail(template)


@router.get("", response_model=list[XlsxTemplateListItem])
def list_xlsx_templates(
    document_type_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[XlsxTemplateListItem]:
    query = (
        db.query(XlsxTemplate)
        .options(joinedload(XlsxTemplate.document_type), joinedload(XlsxTemplate.created_by))
        .order_by(XlsxTemplate.created_at.desc())
    )
    if document_type_id is not None:
        query = query.filter(XlsxTemplate.document_type_id == document_type_id)
    return [_detail(template) for template in query.all()]


@router.get("/{template_id}", response_model=XlsxTemplateDetail)
def get_xlsx_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> XlsxTemplateDetail:
    return _detail(_get_template(db, template_id))


@router.post("/{template_id}/validate", response_model=XlsxTemplateDetail)
def validate_xlsx_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> XlsxTemplateDetail:
    template = _get_template(db, template_id)
    try:
        workbook_bytes = storage_provider.get(template.storage_key, category="xlsx_templates")
        analysis = analyze_xlsx_template(
            workbook_bytes, {field.name for field in template.document_type.fields}
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Stored XLSX template not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid stored .xlsx file: {exc}") from exc

    template.detected_sheets = analysis.detected_sheets
    template.detected_tokens = analysis.detected_tokens
    template.image_slots = analysis.image_slots
    template.validation_warnings = analysis.validation_warnings
    db.commit()
    db.refresh(template)
    return _detail(template)


@router.post("/{template_id}/preview", response_model=XlsxTemplatePreviewResponse)
def preview_xlsx_template_route(
    template_id: UUID,
    request: XlsxTemplatePreviewRequest | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> XlsxTemplatePreviewResponse:
    template = _get_template(db, template_id)
    try:
        workbook_bytes = storage_provider.get(template.storage_key, category="xlsx_templates")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Stored XLSX template not found") from exc

    payload = (
        request.mock_data
        if request is not None and request.mock_data is not None
        else template.mock_data or {}
    )
    try:
        preview = preview_xlsx_template(workbook_bytes, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return XlsxTemplatePreviewResponse(**preview)

```

## File: backend/app/api/document_designs.py
```
import io
import os
import uuid
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.api.document_types import require_document_type
from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.models.document_type import DocumentType, DocumentTypeMetadataDefinition
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate
from app.schemas.document_issuance import DocumentIssuanceOut
from app.services.pdf_generator import generate_composed_pdf
from app.dependencies import get_storage_provider
from app.services.storage.base import StorageProvider

from app.schemas.document_design import (
    AddStaticPdfPage,
    AddTemplatePage,
    DocumentDesignCreate,
    DocumentDesignUpdate,
    DocumentDesignDetail,
    DocumentDesignListItem,
    DocumentDesignPageOut,
    ReorderDesignPages,
    UpdateDesignPage,
)
from app.services.design_validation import (
    assert_no_duplicate_static_pdf,
    assert_static_pdf_compatible,
    assert_template_compatible,
    get_design_warnings,
    static_pdf_snapshot,
    template_snapshot,
    validate_design_activation,
)

router = APIRouter(prefix="/api/document-designs", tags=["document-designs"])


def _query_design(db: SQLAlchemySession, design_id: UUID) -> DocumentDesign | None:
    return (
        db.query(DocumentDesign)
        .options(
            joinedload(DocumentDesign.document_type).selectinload(DocumentType.fields),
            joinedload(DocumentDesign.created_by),
            selectinload(DocumentDesign.pages),
        )
        .filter(DocumentDesign.id == design_id)
        .first()
    )


def _require_design(db: SQLAlchemySession, design_id: UUID) -> DocumentDesign:
    design = _query_design(db, design_id)
    if design is None:
        raise HTTPException(status_code=404, detail="Document design not found")
    return design


def _require_page(design: DocumentDesign, page_id: UUID) -> DocumentDesignPage:
    page = next((candidate for candidate in design.pages if candidate.id == page_id), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Design page not found")
    return page


def _validate_design_output(
    db: SQLAlchemySession,
    document_type: DocumentType,
    output_format: str,
    xlsx_template_id: UUID | None,
) -> XlsxTemplate | None:
    allowed_formats = document_type.allowed_output_formats or ["pdf"]
    if output_format not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Document type does not allow {output_format} output",
        )

    if output_format == "xlsx" and xlsx_template_id is None:
        raise HTTPException(status_code=400, detail="XLSX designs require xlsx_template_id")

    if output_format == "pdf" and xlsx_template_id is not None:
        raise HTTPException(
            status_code=400,
            detail="PDF designs cannot reference an XLSX template",
        )

    if xlsx_template_id is None:
        return None

    template = db.query(XlsxTemplate).filter(XlsxTemplate.id == xlsx_template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="XLSX template not found")
    if template.document_type_id != document_type.id:
        raise HTTPException(
            status_code=400,
            detail="XLSX template must belong to the design document type",
        )
    return template


def _page_out(page: DocumentDesignPage) -> DocumentDesignPageOut:
    return DocumentDesignPageOut(
        id=page.id,
        block_type=page.block_type,
        content_id=page.content_id,
        position=page.position,
        title=page.title,
        notes=page.notes,
        config=page.config or {},
        snapshot=page.snapshot or {},
        created_at=page.created_at,
    )


def _activate_design(design: DocumentDesign, db: SQLAlchemySession) -> None:
    validate_design_activation(design, db)

    if design.version_group_id is None:
        design.version_group_id = design.id
        design.version_number = 1
        design.status = "active"
        return

    old_current = (
        db.query(DocumentDesign)
        .filter(
            DocumentDesign.version_group_id == design.version_group_id,
            DocumentDesign.status == "active",
            DocumentDesign.id != design.id,
        )
        .first()
    )
    if old_current is not None:
        old_current.status = "superseded"
        db.flush()
    design.status = "active"


def _detail(design: DocumentDesign, db: SQLAlchemySession = None) -> DocumentDesignDetail:
    ordered_pages = sorted(design.pages, key=lambda page: page.position)
    warnings = []
    if design.status == "draft":
        warnings = get_design_warnings(design, db)
    return DocumentDesignDetail(
        id=design.id,
        name=design.name,
        description=design.description,
        output_format=design.output_format,
        xlsx_template_id=design.xlsx_template_id,
        status=design.status,
        version_group_id=design.version_group_id,
        version_number=design.version_number,
        document_type_id=design.document_type_id,
        document_type_name=design.document_type.name,
        created_by_email=design.created_by.email,
        created_at=design.created_at,
        pages=[_page_out(page) for page in ordered_pages],
        warnings=warnings,
        mock_data=design.mock_data,
    )


@router.post("", response_model=DocumentDesignDetail, status_code=201)
def create_document_design(
    payload: DocumentDesignCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    document_type = require_document_type(db, payload.document_type_id)
    xlsx_template = _validate_design_output(
        db,
        document_type,
        payload.output_format,
        payload.xlsx_template_id,
    )

    design = DocumentDesign(
        document_type=document_type,
        name=payload.name,
        description=payload.description,
        output_format=payload.output_format,
        xlsx_template=xlsx_template,
        status="draft",
        created_by=user,
        mock_data=payload.mock_data,
    )
    db.add(design)
    db.commit()
    db.refresh(design)
    return _detail(design, db)


@router.put("/{design_id}", response_model=DocumentDesignDetail)
def update_document_design(
    design_id: UUID,
    payload: DocumentDesignUpdate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = (
        db.query(DocumentDesign)
        .options(
            joinedload(DocumentDesign.document_type),
            joinedload(DocumentDesign.created_by),
            selectinload(DocumentDesign.pages),
        )
        .filter(DocumentDesign.id == design_id)
        .first()
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Document design not found")
    xlsx_template = _validate_design_output(
        db,
        design.document_type,
        payload.output_format,
        payload.xlsx_template_id,
    )

    design.name = payload.name
    design.description = payload.description
    design.output_format = payload.output_format
    design.xlsx_template = xlsx_template
    design.mock_data = payload.mock_data

    db.commit()
    db.refresh(design)
    return _detail(design, db)


@router.get("", response_model=list[DocumentDesignListItem])
def list_document_designs(
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentDesignListItem]:
    rows = (
        db.query(DocumentDesign, func.count(DocumentDesignPage.id))
        .outerjoin(DocumentDesignPage, DocumentDesignPage.design_id == DocumentDesign.id)
        .options(
            selectinload(DocumentDesign.document_type),
            selectinload(DocumentDesign.created_by),
        )
        .group_by(DocumentDesign.id)
        .order_by(DocumentDesign.created_at.desc())
        .all()
    )
    return [
        DocumentDesignListItem(
            id=design.id,
            name=design.name,
            description=design.description,
            output_format=design.output_format,
            xlsx_template_id=design.xlsx_template_id,
            status=design.status,
            version_group_id=design.version_group_id,
            version_number=design.version_number,
            document_type_id=design.document_type_id,
            document_type_name=design.document_type.name,
            page_count=page_count,
            created_by_email=design.created_by.email,
            created_at=design.created_at,
        )
        for design, page_count in rows
    ]


@router.get("/{design_id}", response_model=DocumentDesignDetail)
def get_document_design(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    return _detail(_require_design(db, design_id), db)


@router.post("/{design_id}/pages/template", response_model=DocumentDesignPageOut, status_code=201)
def add_template_page(
    design_id: UUID,
    payload: AddTemplatePage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    template = db.query(HtmlTemplate).filter(HtmlTemplate.id == payload.template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_template_compatible(design, template)

    page = DocumentDesignPage(
        design=design,
        block_type="html_template",
        content_id=template.id,
        position=len(design.pages),
        title=payload.title,
        notes=payload.notes,
        config=payload.config or {},
        snapshot=template_snapshot(template),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return _page_out(page)


@router.post("/{design_id}/pages/static-pdf", response_model=DocumentDesignPageOut, status_code=201)
def add_static_pdf_page(
    design_id: UUID,
    payload: AddStaticPdfPage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    asset = db.query(StaticPdfAsset).filter(StaticPdfAsset.id == payload.static_pdf_asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="PDF asset not found")
    assert_static_pdf_compatible(design, asset)
    assert_no_duplicate_static_pdf(design, asset)

    page = DocumentDesignPage(
        design=design,
        block_type="static_pdf",
        content_id=asset.id,
        position=len(design.pages),
        title=payload.title,
        notes=payload.notes,
        config=payload.config or {},
        snapshot=static_pdf_snapshot(asset),
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return _page_out(page)


@router.patch("/{design_id}/pages/reorder", response_model=DocumentDesignDetail)
def reorder_design_pages(
    design_id: UUID,
    payload: ReorderDesignPages,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    pages_by_id = {page.id: page for page in design.pages}
    if set(payload.page_ids) != set(pages_by_id):
        raise HTTPException(status_code=400, detail="Reorder payload must include every design page")

    for position, page_id in enumerate(payload.page_ids):
        pages_by_id[page_id].position = position
    db.commit()
    return _detail(design, db)


@router.patch("/{design_id}/pages/{page_id}", response_model=DocumentDesignPageOut)
def update_design_page(
    design_id: UUID,
    page_id: UUID,
    payload: UpdateDesignPage,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignPageOut:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    page = _require_page(design, page_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(page, field, value)
    db.commit()
    db.refresh(page)
    return _page_out(page)


@router.delete("/{design_id}/pages/{page_id}", status_code=204)
def delete_design_page(
    design_id: UUID,
    page_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> Response:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft designs can be modified")
    page = _require_page(design, page_id)

    db.delete(page)
    remaining = [candidate for candidate in design.pages if candidate.id != page_id]
    for position, candidate in enumerate(sorted(remaining, key=lambda item: item.position)):
        candidate.position = position
    db.commit()
    return Response(status_code=204)


@router.post("/{design_id}/activate", response_model=DocumentDesignDetail)
def activate_document_design(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    design = _require_design(db, design_id)
    _activate_design(design, db)

    db.commit()
    db.refresh(design)
    return _detail(design, db)


@router.post("/{design_id}/versions", response_model=DocumentDesignDetail, status_code=201)
def fork_document_design_version(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentDesignDetail:
    from sqlalchemy.exc import IntegrityError

    current = _require_design(db, design_id)
    if current.status != "active":
        raise HTTPException(status_code=400, detail="Only the active version can be edited")

    group_id = current.version_group_id or current.id

    # Check for existing draft in the same group to resume (D-04)
    existing_draft = (
        db.query(DocumentDesign)
        .filter(DocumentDesign.version_group_id == group_id, DocumentDesign.status == "draft")
        .first()
    )
    if existing_draft is not None:
        return _detail(existing_draft, db)

    next_version = (
        db.query(func.max(DocumentDesign.version_number))
        .filter(DocumentDesign.version_group_id == group_id)
        .scalar() or 0
    ) + 1

    draft = DocumentDesign(
        document_type_id=current.document_type_id,
        name=current.name,
        description=current.description,
        output_format=current.output_format,
        xlsx_template_id=current.xlsx_template_id,
        status="draft",
        version_group_id=group_id,
        version_number=next_version,
        created_by=user,
    )

    # Deep copy pages
    for page in sorted(current.pages, key=lambda p: p.position):
        draft.pages.append(
            DocumentDesignPage(
                block_type=page.block_type,
                content_id=page.content_id,
                position=page.position,
                title=page.title,
                notes=page.notes,
                config=dict(page.config or {}),
                snapshot=dict(page.snapshot or {}),
            )
        )

    db.add(draft)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Fall back to the draft that was concurrently created
        existing_draft = (
            db.query(DocumentDesign)
            .filter(DocumentDesign.version_group_id == group_id, DocumentDesign.status == "draft")
            .first()
        )
        if existing_draft is not None:
            return _detail(existing_draft, db)
        raise

    db.refresh(draft)
    return _detail(draft, db)


@router.get("/{design_id}/versions", response_model=list[DocumentDesignListItem])
def list_document_design_versions(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentDesignListItem]:
    anchor = _require_design(db, design_id)
    group_id = anchor.version_group_id or anchor.id
    rows = (
        db.query(DocumentDesign, func.count(DocumentDesignPage.id))
        .outerjoin(DocumentDesignPage, DocumentDesignPage.design_id == DocumentDesign.id)
        .options(
            selectinload(DocumentDesign.document_type),
            selectinload(DocumentDesign.created_by),
        )
        .filter(DocumentDesign.version_group_id == group_id)
        .group_by(DocumentDesign.id)
        .order_by(DocumentDesign.version_number.desc())
        .all()
    )
    return [
        DocumentDesignListItem(
            id=design.id,
            name=design.name,
            description=design.description,
            output_format=design.output_format,
            xlsx_template_id=design.xlsx_template_id,
            status=design.status,
            version_group_id=design.version_group_id,
            version_number=design.version_number,
            document_type_id=design.document_type_id,
            document_type_name=design.document_type.name,
            page_count=page_count,
            created_by_email=design.created_by.email,
            created_at=design.created_at,
        )
        for design, page_count in rows
    ]


@router.delete("/{design_id}", status_code=204)
def discard_document_design_draft(
    design_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> Response:
    design = _require_design(db, design_id)
    if design.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft versions can be discarded")
    db.delete(design)
    db.commit()
    return Response(status_code=204)


from datetime import datetime

def validate_metadata_values(
    values: dict,
    definitions: list[DocumentTypeMetadataDefinition]
) -> dict:
    """Validates metadata values against definitions.
    Raises HTTPException 400 if validation fails.
    Returns coerced metadata values dictionary.
    """
    coerced = {}
    
    # Case insensitive check for keys
    values_lower = {k.lower(): (k, v) for k, v in values.items()}
    
    for def_ in definitions:
        name_lower = def_.name.lower()
        
        # Check if present
        if name_lower not in values_lower:
            if def_.required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required metadata field '{def_.name}' is missing."
                )
            continue
            
        orig_key, val = values_lower[name_lower]
        
        if val is None or val == "":
            if def_.required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Required metadata field '{def_.name}' cannot be empty."
                )
            coerced[def_.name] = None
            continue
            
        # Coerce based on type
        t = def_.type
        if t == "text":
            coerced[def_.name] = str(val)
        elif t == "number":
            try:
                if isinstance(val, bool):
                    coerced[def_.name] = float(1 if val else 0)
                else:
                    coerced[def_.name] = float(val)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a number."
                )
        elif t == "boolean":
            if isinstance(val, bool):
                coerced[def_.name] = val
            elif str(val).lower() in ("true", "1", "yes", "on"):
                coerced[def_.name] = True
            elif str(val).lower() in ("false", "0", "no", "off"):
                coerced[def_.name] = False
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a boolean."
                )
        elif t == "date":
            if isinstance(val, datetime):
                coerced[def_.name] = val.date().isoformat()
            elif isinstance(val, str):
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                    coerced[def_.name] = val
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Metadata field '{def_.name}' must be a date in YYYY-MM-DD format."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a date."
                )
        elif t == "datetime":
            if isinstance(val, datetime):
                coerced[def_.name] = val.isoformat()
            elif isinstance(val, str):
                try:
                    val_str = val
                    if val_str.endswith("Z"):
                        val_str = val_str[:-1] + "+00:00"
                    datetime.fromisoformat(val_str)
                    coerced[def_.name] = val
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Metadata field '{def_.name}' must be a valid datetime (ISO 8601 format)."
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Metadata field '{def_.name}' must be a datetime."
                )
        else:
            coerced[def_.name] = val
            
    return coerced


@router.post("/{design_id}/generate", response_model=DocumentIssuanceOut, status_code=202)
def generate_document(
    design_id: UUID,
    payload: dict = Body(default={}),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> DocumentIssuance:
    design = _require_design(db, design_id)
    if design.status == "draft":
        _activate_design(design, db)
        db.flush()

    # Split data and metadata
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(metadata, dict):
        metadata = {}

    # Validate metadata
    coerced_metadata = validate_metadata_values(metadata, design.document_type.metadata_definitions)

    # Validate and coerce input data payload against document type fields if fields are defined
    if design.document_type.fields:
        from app.services.pdf_generator import validate_and_coerce_payload
        from fastapi import HTTPException
        try:
            validate_and_coerce_payload(data, design.document_type.fields)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    from datetime import datetime
    from app.services.issuance_jobs import enqueue_document_generation

    issuance_id = uuid.uuid4()
    issuance = DocumentIssuance(
        id=issuance_id,
        design_version_id=design.id,
        storage_key=None,
        user_id=user.id,
        input_data=data,
        metadata_values=coerced_metadata,
        status="queued",
        queued_at=datetime.utcnow(),
    )
    db.add(issuance)
    db.commit()
    db.refresh(issuance)

    # Enqueue task
    try:
        task_id = enqueue_document_generation(str(issuance.id))
        issuance.celery_task_id = task_id
        db.commit()
    except Exception as e:
        issuance.status = "failure"
        issuance.error_message = f"Failed to enqueue: {str(e)}"
        issuance.completed_at = datetime.utcnow()
        db.commit()

    db.refresh(issuance)
    return issuance


@router.post("/{design_id}/preview")
def preview_document(
    design_id: UUID,
    payload: dict = Body(default={}),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> Response:
    design = _require_design(db, design_id)
    if design.status not in ("draft", "active"):
        raise HTTPException(status_code=400, detail="Preview only allowed for draft or active designs")

    # Split data and metadata
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(metadata, dict):
        metadata = {}

    # Validate metadata
    _ = validate_metadata_values(metadata, design.document_type.metadata_definitions)

    pdf_bytes = generate_composed_pdf(design, data, db, storage_provider, mock_fallback=True)
    return Response(content=pdf_bytes, media_type="application/pdf")

```

## File: backend/app/api/issuances.py
```
from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.user import User
from app.dependencies import get_storage_provider
from app.services.storage.base import StorageProvider
from app.schemas.document_issuance import (
    DocumentIssuanceLibraryItem,
    DocumentIssuanceShareOut,
    DocumentTracelogOut,
)
from app.utils.signature import generate_issuance_signature, verify_issuance_signature

router = APIRouter(prefix="/api/issuances", tags=["issuances"])
public_router = APIRouter(prefix="/api/public/document-issuances", tags=["public-issuances"])


def _request_metadata(request: Request, route: str) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "route": route,
    }


def _require_issuance(db: SQLAlchemySession, issuance_id: UUID) -> DocumentIssuance:
    issuance = (
        db.query(DocumentIssuance)
        .options(
            joinedload(DocumentIssuance.design_version),
            joinedload(DocumentIssuance.user),
        )
        .filter(DocumentIssuance.id == issuance_id)
        .first()
    )
    if issuance is None:
        raise HTTPException(status_code=404, detail="Document issuance not found")
    return issuance


def _issuance_out(issuance: DocumentIssuance) -> DocumentIssuanceLibraryItem:
    return DocumentIssuanceLibraryItem(
        id=issuance.id,
        design_version_id=issuance.design_version_id,
        design_name=issuance.design_version.name,
        output_format=issuance.output_format,
        mime_type=issuance.mime_type,
        filename=issuance.filename,
        preview_storage_key=issuance.preview_storage_key,
        status=issuance.status,
        design_status=issuance.design_version.status,
        design_version_number=issuance.design_version.version_number,
        user_id=issuance.user_id,
        generated_by_email=issuance.user.email,
        input_data=issuance.input_data,
        metadata_values=issuance.metadata_values,
        created_at=issuance.created_at,
        preview_url=f"/api/issuances/{issuance.id}/preview",
        download_url=f"/api/issuances/{issuance.id}/download",
        celery_task_id=issuance.celery_task_id,
        error_message=issuance.error_message,
        queued_at=issuance.queued_at,
        started_at=issuance.started_at,
        completed_at=issuance.completed_at,
        retry_count=issuance.retry_count,
    )


def _document_response(
    issuance: DocumentIssuance,
    storage_provider: StorageProvider,
    disposition: str = "attachment",
) -> Response:
    try:
        return storage_provider.get_download_response(
            issuance.storage_key,
            filename=issuance.filename or f"{issuance.id}.pdf",
            category="issuances",
            disposition=disposition,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Issued document file not found on storage")


def _append_tracelog(
    db: SQLAlchemySession,
    issuance: DocumentIssuance,
    event_type: Literal["download", "share"],
    user_id: UUID | None,
    metadata: dict,
) -> None:
    db.add(
        DocumentTracelog(
            issuance_id=issuance.id,
            user_id=user_id,
            event_type=event_type,
            metadata_=metadata,
        )
    )
    db.commit()


def _verify_issuance_ready(issuance: DocumentIssuance) -> None:
    if issuance.status in ("queued", "processing"):
        raise HTTPException(
            status_code=409,
            detail="Document generation is not complete"
        )
    if issuance.status == "failure":
        raise HTTPException(
            status_code=409,
            detail=issuance.error_message or "Document generation failed"
        )
    if not issuance.storage_key:
        raise HTTPException(
            status_code=409,
            detail="Document file is not ready"
        )


@public_router.get("/{issuance_id}/download")
def public_download_issuance(
    issuance_id: UUID,
    signature: str,
    request: Request,
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    if not verify_issuance_signature(issuance_id, signature):
        raise HTTPException(status_code=403, detail="Invalid document signature")

    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    response = _document_response(issuance, storage_provider)
    _append_tracelog(
        db,
        issuance,
        "download",
        None,
        _request_metadata(request, f"GET /api/public/document-issuances/{issuance.id}/download"),
    )
    return response


@router.get("", response_model=list[DocumentIssuanceLibraryItem])
def list_issuances(
    design_name: str | None = None,
    id: UUID | None = None,
    status: Literal["queued", "processing", "success", "failure"] | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    metadata_key: str | None = None,
    metadata_value: str | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentIssuanceLibraryItem]:
    query = (
        db.query(DocumentIssuance)
        .join(DocumentIssuance.design_version)
        .join(DocumentIssuance.user)
        .options(
            joinedload(DocumentIssuance.design_version),
            joinedload(DocumentIssuance.user),
        )
    )

    if design_name:
        query = query.filter(DocumentDesign.name.ilike(f"%{design_name}%"))
    if id is not None:
        query = query.filter(DocumentIssuance.id == id)
    if status is not None:
        query = query.filter(DocumentIssuance.status == status)
    if created_from is not None:
        query = query.filter(DocumentIssuance.created_at >= datetime.combine(created_from, time.min))
    if created_to is not None:
        query = query.filter(DocumentIssuance.created_at <= datetime.combine(created_to, time.max))
    if metadata_key and metadata_value is not None:
        query = query.filter(
            func.coalesce(func.json_extract_path_text(DocumentIssuance.metadata_values, metadata_key), "").ilike(
                f"%{metadata_value}%"
            )
        )

    issuances = query.order_by(DocumentIssuance.created_at.desc()).all()
    return [_issuance_out(issuance) for issuance in issuances]


@router.get("/{issuance_id}", response_model=DocumentIssuanceLibraryItem)
def get_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuanceLibraryItem:
    return _issuance_out(_require_issuance(db, issuance_id))


@router.get("/{issuance_id}/preview")
def preview_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    return _document_response(issuance, storage_provider, disposition="inline")


@router.get("/{issuance_id}/download")
def download_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    response = _document_response(issuance, storage_provider)
    _append_tracelog(
        db,
        issuance,
        "download",
        user.id,
        _request_metadata(request, f"GET /api/issuances/{issuance.id}/download"),
    )
    return response


@router.post("/{issuance_id}/share", response_model=DocumentIssuanceShareOut)
def share_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuanceShareOut:
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    signature = generate_issuance_signature(issuance.id)
    public_url = f"/api/public/document-issuances/{issuance.id}/download?signature={signature}"
    _append_tracelog(
        db,
        issuance,
        "share",
        user.id,
        _request_metadata(request, f"POST /api/issuances/{issuance.id}/share"),
    )
    return DocumentIssuanceShareOut(public_url=public_url)


@router.get("/{issuance_id}/tracelogs", response_model=list[DocumentTracelogOut])
def list_issuance_tracelogs(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentTracelog]:
    _require_issuance(db, issuance_id)
    return (
        db.query(DocumentTracelog)
        .filter(DocumentTracelog.issuance_id == issuance_id)
        .order_by(DocumentTracelog.created_at.asc())
        .all()
    )

```

## File: backend/app/services/xlsx_analysis.py
```
import re
from dataclasses import dataclass
from io import BytesIO

from openpyxl import load_workbook


TOKEN_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*}}")


@dataclass
class XlsxTemplateAnalysis:
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]


def analyze_xlsx_template(workbook_bytes: bytes, schema_tokens: set[str]) -> XlsxTemplateAnalysis:
    workbook = load_workbook(BytesIO(workbook_bytes), read_only=False, data_only=False)
    detected_sheets: list[dict] = []
    detected_tokens: list[str] = []
    validation_warnings: list[dict] = []
    seen_tokens: set[str] = set()

    for worksheet in workbook.worksheets:
        detected_sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "print_area": str(worksheet.print_area) if worksheet.print_area else None,
                "merged_ranges": [str(cell_range) for cell_range in worksheet.merged_cells.ranges],
            }
        )
        for row in worksheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                for token in TOKEN_PATTERN.findall(cell.value):
                    if token not in seen_tokens:
                        seen_tokens.add(token)
                        detected_tokens.append(token)
                    if token not in schema_tokens:
                        validation_warnings.append(
                            {
                                "type": "unknown_schema_token",
                                "sheet": worksheet.title,
                                "cell": cell.coordinate,
                                "message": f"Token '{{{{{token}}}}}' is not defined by the document type",
                                "suggestion": "Add the field to the document type or replace the token",
                            }
                        )

    return XlsxTemplateAnalysis(
        detected_sheets=detected_sheets,
        detected_tokens=detected_tokens,
        image_slots=[],
        validation_warnings=validation_warnings,
    )

```

## File: backend/app/services/xlsx_images.py
```
import base64
import binascii
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass(frozen=True)
class NormalizedImage:
    mime_type: str
    content: bytes
    width: int
    height: int


def normalize_image_value(value: object) -> NormalizedImage:
    if not isinstance(value, str) or not value.startswith("data:image/"):
        raise ValueError("invalid_image_payload")

    try:
        header, encoded = value.split(",", 1)
    except ValueError as exc:
        raise ValueError("invalid_image_payload") from exc

    mime_type = header.removeprefix("data:").split(";", 1)[0]
    if mime_type not in {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}:
        raise ValueError("unsupported_image_type")

    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid_image_payload") from exc

    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except Exception as exc:
        raise ValueError("invalid_image_payload") from exc

    return NormalizedImage(mime_type=mime_type, content=content, width=width, height=height)

```

## File: backend/app/services/xlsx_renderer.py
```
import copy
import json
from io import BytesIO
from typing import Any

from jinja2.sandbox import SandboxedEnvironment
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from app.services.xlsx_images import normalize_image_value


_JINJA_ENV = SandboxedEnvironment(autoescape=False)
_REPEAT_DEFINED_NAME = "_docman_repeats"


def render_xlsx_template(
    workbook_bytes: bytes,
    payload: dict,
    image_values: dict | None = None,
) -> bytes:
    workbook = load_workbook(BytesIO(workbook_bytes), data_only=False)
    repeat_rows = _render_repeat_rows(workbook, payload)

    for worksheet in workbook.worksheets:
        skipped_rows = repeat_rows.get(worksheet.title, set())
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.row in skipped_rows:
                    continue
                _render_cell(cell, payload)

    _insert_images(workbook, image_values or {})

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def preview_xlsx_template(workbook_bytes: bytes, payload: dict) -> dict:
    rendered_bytes = render_xlsx_template(workbook_bytes, payload)
    workbook = load_workbook(BytesIO(rendered_bytes), data_only=False)
    sheets: list[dict] = []

    for worksheet in workbook.worksheets:
        cells = []
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cells.append({"address": cell.coordinate, "value": cell.value, "style": {}})
        sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "merged_ranges": [str(cell_range) for cell_range in worksheet.merged_cells.ranges],
                "cells": cells,
            }
        )

    return {"sheets": sheets, "warnings": []}


def _render_repeat_rows(workbook, payload: dict) -> dict[str, set[int]]:
    rendered_rows: dict[str, set[int]] = {}
    offset_by_sheet: dict[str, int] = {}

    for spec in _load_repeat_specs(workbook):
        sheet_name = spec["sheet"]
        if sheet_name not in workbook.sheetnames:
            raise ValueError("invalid_repeat_metadata")
        worksheet = workbook[sheet_name]
        row_index = int(spec["row"]) + offset_by_sheet.get(sheet_name, 0)
        items = _resolve_path(payload, spec["list"])
        if items is None:
            items = []
        if not isinstance(items, list):
            raise ValueError("repeat_list_must_be_array")

        _reject_merged_repeat_row(worksheet, row_index)
        rendered = _render_repeat_row(worksheet, row_index, payload, items)
        rendered_rows.setdefault(sheet_name, set()).update(rendered)
        offset_by_sheet[sheet_name] = offset_by_sheet.get(sheet_name, 0) + len(items) - 1

    return rendered_rows


def _load_repeat_specs(workbook) -> list[dict]:
    defined_name = workbook.defined_names.get(_REPEAT_DEFINED_NAME)
    if defined_name is None:
        return []

    specs: list[dict] = []
    for sheet_name, coordinate in defined_name.destinations:
        if sheet_name not in workbook.sheetnames:
            raise ValueError("invalid_repeat_metadata")
        worksheet = workbook[sheet_name]
        raw_value = worksheet[coordinate].value
        if raw_value in (None, ""):
            continue
        parsed = json.loads(raw_value)
        if not isinstance(parsed, list):
            raise ValueError("invalid_repeat_metadata")
        for item in parsed:
            if not isinstance(item, dict) or not {"sheet", "row", "list"} <= item.keys():
                raise ValueError("invalid_repeat_metadata")
            specs.append(item)

    return sorted(specs, key=lambda spec: (spec["sheet"], int(spec["row"])))


def _render_repeat_row(worksheet: Worksheet, row_index: int, payload: dict, items: list[dict]) -> set[int]:
    if not items:
        worksheet.delete_rows(row_index, 1)
        return set()

    template_cells = [_snapshot_cell(cell) for cell in worksheet[row_index]]
    template_height = worksheet.row_dimensions[row_index].height
    if len(items) > 1:
        worksheet.insert_rows(row_index + 1, len(items) - 1)

    rendered_rows: set[int] = set()
    for item_index, item in enumerate(items):
        target_row = row_index + item_index
        rendered_rows.add(target_row)
        if template_height is not None:
            worksheet.row_dimensions[target_row].height = template_height
        for template_cell in template_cells:
            target_cell = worksheet.cell(row=target_row, column=template_cell["column"])
            _apply_cell_snapshot(template_cell, target_cell)
            context = {**payload, "item": item}
            _render_cell(target_cell, context)

    return rendered_rows


def _snapshot_cell(cell) -> dict:
    return {
        "column": cell.column,
        "value": cell.value,
        "has_style": cell.has_style,
        "style": copy.copy(cell._style),
        "number_format": cell.number_format,
        "font": copy.copy(cell.font),
        "fill": copy.copy(cell.fill),
        "border": copy.copy(cell.border),
        "alignment": copy.copy(cell.alignment),
        "protection": copy.copy(cell.protection),
    }


def _apply_cell_snapshot(snapshot: dict, target) -> None:
    target.value = snapshot["value"]
    if snapshot["has_style"]:
        target._style = copy.copy(snapshot["style"])
    target.number_format = snapshot["number_format"]
    target.font = copy.copy(snapshot["font"])
    target.fill = copy.copy(snapshot["fill"])
    target.border = copy.copy(snapshot["border"])
    target.alignment = copy.copy(snapshot["alignment"])
    target.protection = copy.copy(snapshot["protection"])


def _render_cell(cell, context: dict) -> None:
    if isinstance(cell.value, str) and "{{" in cell.value:
        cell.value = _escape_formula_text(_JINJA_ENV.from_string(cell.value).render(context))


def _escape_formula_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _insert_images(workbook, image_values: dict) -> None:
    for anchor, raw_value in image_values.items():
        if "!" not in anchor:
            raise ValueError("invalid_image_anchor")
        sheet_name, cell_coordinate = anchor.split("!", 1)
        if sheet_name not in workbook.sheetnames:
            raise ValueError("invalid_image_anchor")
        normalized = normalize_image_value(raw_value)
        image = OpenpyxlImage(BytesIO(normalized.content))
        image.anchor = cell_coordinate
        workbook[sheet_name].add_image(image)


def _reject_merged_repeat_row(worksheet: Worksheet, row_index: int) -> None:
    for merged_range in worksheet.merged_cells.ranges:
        min_col, min_row, max_col, max_row = range_boundaries(str(merged_range))
        del min_col, max_col
        if min_row <= row_index <= max_row:
            raise ValueError("unsupported_merge_in_repeat_range")


def _resolve_path(payload: dict, path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current

```

## File: backend/app/services/document_generation.py
```
from dataclasses import dataclass

from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.document_issuance import DocumentIssuance
from app.services.pdf_generator import generate_composed_pdf
from app.services.storage.base import StorageProvider
from app.services.xlsx_renderer import render_xlsx_template

PDF_MIME_TYPE = "application/pdf"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True)
class GeneratedDocument:
    content: bytes
    mime_type: str
    filename: str
    extension: str


def generate_document_file(
    issuance: DocumentIssuance,
    db: SQLAlchemySession,
    storage_provider: StorageProvider,
) -> GeneratedDocument:
    design = issuance.design_version
    if design.output_format == "xlsx":
        if design.xlsx_template is None:
            raise ValueError("XLSX design is missing its template")
        workbook_bytes = storage_provider.get(
            design.xlsx_template.storage_key,
            category="xlsx_templates",
        )
        content = render_xlsx_template(workbook_bytes, issuance.input_data)
        return GeneratedDocument(
            content=content,
            mime_type=XLSX_MIME_TYPE,
            filename=f"{issuance.id}.xlsx",
            extension="xlsx",
        )

    content = generate_composed_pdf(
        design,
        issuance.input_data,
        db,
        storage_provider,
        mock_fallback=False,
    )
    return GeneratedDocument(
        content=content,
        mime_type=PDF_MIME_TYPE,
        filename=f"{issuance.id}.pdf",
        extension="pdf",
    )

```

## File: backend/app/services/design_validation.py
```
from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.content_template import HtmlTemplate
from app.models.document_design import DocumentDesign
from app.models.static_pdf_asset import StaticPdfAsset


def template_snapshot(template: HtmlTemplate) -> dict:
    return {
        "template_id": str(template.id),
        "name": template.name,
        "html": template.html,
        "css": template.css,
        "token_names": list(template.token_names or []),
        "document_type_id": str(template.document_type_id),
    }


def static_pdf_snapshot(asset: StaticPdfAsset) -> dict:
    return {
        "asset_id": str(asset.id),
        "filename": asset.original_filename,
        "stored_filename": asset.stored_filename,
        "stored_path": asset.stored_path,
        "page_count": asset.page_count,
        "page_start": asset.page_start,
        "page_end": asset.page_end,
        "file_size": asset.file_size,
        "document_type_id": str(asset.document_type_id) if asset.document_type_id else None,
    }


def assert_template_compatible(design: DocumentDesign, template: HtmlTemplate) -> None:
    if template.document_type_id != design.document_type_id:
        raise HTTPException(
            status_code=400,
            detail="Template must belong to the design document type",
        )


def assert_static_pdf_compatible(design: DocumentDesign, asset: StaticPdfAsset) -> None:
    if asset.document_type_id is not None and asset.document_type_id != design.document_type_id:
        raise HTTPException(
            status_code=400,
            detail="PDF asset must be global or belong to the design document type",
        )


def assert_no_duplicate_static_pdf(design: DocumentDesign, asset: StaticPdfAsset) -> None:
    duplicate = any(
        page.block_type == "static_pdf" and page.content_id == asset.id for page in design.pages
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="PDF asset already exists in this design")


def get_design_warnings(design: DocumentDesign, db: SQLAlchemySession = None) -> list[str]:
    from app.services.content_validation import get_ancestor_paths, extract_template_tokens_ast_warnings

    allowed_tokens = {field.name for field in design.document_type.fields}
    valid_ancestors = set()
    for token in allowed_tokens:
        valid_ancestors.update(get_ancestor_paths(token))

    warnings = []

    template_page_ids = {page.content_id for page in design.pages if page.block_type == "html_template"}
    templates_by_id = {}
    if db is not None and template_page_ids:
        templates = db.query(HtmlTemplate).filter(HtmlTemplate.id.in_(template_page_ids)).all()
        templates_by_id = {template.id: template for template in templates}

    for page in design.pages:
        if page.block_type != "html_template":
            continue

        html = None
        template = templates_by_id.get(page.content_id)
        if template is not None:
            html = template.html
        else:
            snapshot = page.snapshot or {}
            html = snapshot.get("html")

        if html:
            page_warnings = extract_template_tokens_ast_warnings(html, valid_ancestors)
            warnings.extend(page_warnings)

    return sorted(list(set(warnings)))


def validate_design_activation(design: DocumentDesign, db: SQLAlchemySession) -> None:
    if not design.name or not design.document_type_id:
        raise HTTPException(status_code=400, detail="Design name and document type are required")

    allowed_formats = design.document_type.allowed_output_formats or ["pdf"]
    if design.output_format not in allowed_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Document type does not allow {design.output_format} output",
        )

    if design.output_format == "xlsx":
        if design.xlsx_template_id is None:
            raise HTTPException(
                status_code=400,
                detail="XLSX designs require a template before activation",
            )
        if design.xlsx_template is None:
            raise HTTPException(status_code=404, detail="XLSX template not found")
        if design.xlsx_template.document_type_id != design.document_type_id:
            raise HTTPException(
                status_code=400,
                detail="XLSX template must belong to the design document type",
            )
        if design.xlsx_template.validation_warnings:
            raise HTTPException(status_code=400, detail="XLSX template has validation warnings")
        return

    if not design.pages:
        raise HTTPException(status_code=400, detail="Active designs require at least one page")

    warnings = get_design_warnings(design, db)
    if warnings:
        invalid_tokens = []
        for warning in warnings:
            if warning.startswith("Token '") and warning.endswith("' is not declared in schema"):
                token = warning[7:-27]
                invalid_tokens.append(token)
            else:
                invalid_tokens.append(warning)

        raise HTTPException(
            status_code=400,
            detail=f"Invalid template tokens: {', '.join(sorted(list(set(invalid_tokens))))}",
        )

```

## File: backend/app/services/issuance_jobs.py
```
def enqueue_document_generation(issuance_id: str) -> str:
    """Enqueues document generation via a Celery worker task.

    Lazily imports the task to allow app startup and testing before the
    worker module is fully defined.
    """
    from app.workers.document_generation import generate_document
    task = generate_document.delay(issuance_id)
    return str(task.id)

```

## File: backend/app/workers/document_generation.py
```
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload

from app.workers.celery_app import celery_app
from app.db import SessionLocal
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_design import DocumentDesign
from app.services.document_generation import generate_document_file
from app.dependencies import get_storage_provider

logger = logging.getLogger(__name__)


def _generate_document_impl(issuance_id: str) -> None:
    db = SessionLocal()
    try:
        issuance_uuid = issuance_id if isinstance(issuance_id, uuid.UUID) else uuid.UUID(issuance_id)
        # Lock issuance row for update to prevent concurrent task runs from racing
        issuance = (
            db.query(DocumentIssuance)
            .filter(DocumentIssuance.id == issuance_uuid)
            .with_for_update()
            .first()
        )

        if not issuance:
            logger.error(f"DocumentIssuance {issuance_id} not found.")
            return

        if issuance.status != "queued":
            logger.info(f"DocumentIssuance {issuance_id} has status '{issuance.status}'. Skipping generation.")
            return

        # 1. Update status to processing
        issuance.status = "processing"
        issuance.started_at = datetime.utcnow()
        db.commit()

        # Re-fetch for generation logic to ensure we are operating on clean DB state
        design = (
            db.query(DocumentDesign)
            .options(
                joinedload(DocumentDesign.document_type),
                joinedload(DocumentDesign.created_by),
                joinedload(DocumentDesign.xlsx_template),
                selectinload(DocumentDesign.pages),
            )
            .filter(DocumentDesign.id == issuance.design_version_id)
            .first()
        )

        if not design:
            raise ValueError(f"DocumentDesign {issuance.design_version_id} not found.")

        # 2. Generate document bytes
        storage_provider = get_storage_provider()
        issuance.design_version = design
        generated = generate_document_file(issuance, db, storage_provider)

        # 3. Save to storage
        storage_key = storage_provider.save(
            f"{issuance.id}.{generated.extension}",
            generated.content,
            category="issuances"
        )

        # 4. Update status to success
        issuance.storage_key = storage_key
        issuance.output_format = design.output_format
        issuance.mime_type = generated.mime_type
        issuance.filename = generated.filename
        issuance.status = "success"
        issuance.completed_at = datetime.utcnow()

        # 5. Create tracelog
        tracelog = DocumentTracelog(
            issuance_id=issuance.id,
            user_id=issuance.user_id,
            event_type="generation",
            metadata_={
                "source": "Celery Worker",
                "design_id": str(design.id),
            },
        )
        db.add(tracelog)
        db.commit()
        logger.info(f"Successfully generated document for DocumentIssuance {issuance_id}")

    except Exception as e:
        db.rollback()
        logger.exception(f"Error generating document for DocumentIssuance {issuance_id}")
        
        # Open a new transaction to record the failure status securely
        fail_db = SessionLocal()
        try:
            issuance_uuid = issuance_id if isinstance(issuance_id, uuid.UUID) else uuid.UUID(issuance_id)
            issuance = fail_db.query(DocumentIssuance).filter(DocumentIssuance.id == issuance_uuid).first()
            if issuance:
                issuance.status = "failure"
                # Truncate error message to avoid DB constraints or excessive sizes
                issuance.error_message = str(e)[:1000]
                issuance.completed_at = datetime.utcnow()
                fail_db.commit()
        except Exception as fail_err:
            logger.exception(f"Failed to record failure status for {issuance_id}: {fail_err}")
        finally:
            fail_db.close()
        
        raise e
    finally:
        db.close()


@celery_app.task(name="app.workers.document_generation.generate_document")
def generate_document(issuance_id: str) -> None:
    """Task to generate a document file asynchronously."""
    return _generate_document_impl(issuance_id)


@celery_app.task(name="app.workers.document_generation.generate_document_pdf")
def generate_document_pdf(issuance_id: str) -> None:
    """Backward-compatible task name for already queued PDF generation jobs."""
    return _generate_document_impl(issuance_id)

```

## File: backend/app/services/storage/local.py
```
import io
import mimetypes
import os
from pathlib import Path
from fastapi import Response
from fastapi.responses import FileResponse

from app.services.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, root_paths: dict[str, str]):
        self.root_paths = root_paths

    def _get_path(self, key: str, category: str) -> Path:
        path = Path(key)
        if path.is_absolute():
            return path
        root = self.root_paths.get(category)
        if not root:
            raise ValueError(f"Unknown storage category: {category}")
        return Path(root) / key

    def save(self, key: str, content: bytes, category: str) -> str:
        path = self._get_path(key, category)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def get(self, key: str, category: str) -> bytes:
        path = self._get_path(key, category)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes()

    def get_stream(self, key: str, category: str) -> io.BytesIO:
        return io.BytesIO(self.get(key, category))

    def delete(self, key: str, category: str) -> None:
        path = self._get_path(key, category)
        if path.exists():
            os.remove(path)

    def get_download_response(self, key: str, filename: str, category: str, disposition: str = "attachment") -> Response:
        path = self._get_path(key, category)
        if not path.exists():
            raise FileNotFoundError(f"File not found for download: {path}")
        headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return FileResponse(
            path,
            media_type=media_type,
            headers=headers,
        )

    def exists(self, key: str, category: str = "issuances") -> bool:
        try:
            path = self._get_path(key, category)
            return path.exists()
        except Exception:
            return False

```

## File: backend/app/services/storage/s3.py
```
import io
import mimetypes
from pathlib import Path
import boto3
from botocore.client import Config
from fastapi import Response
from fastapi.responses import StreamingResponse

from app.services.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(
        self,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region_name: str | None,
        buckets: dict[str, str],
    ):
        self.buckets = buckets
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name or "us-east-1",
            config=Config(signature_version="s3v4"),
        )

    def _clean_key(self, key: str) -> str:
        path = Path(key)
        if path.is_absolute():
            return path.name
        return key

    def _get_bucket(self, category: str) -> str:
        bucket = self.buckets.get(category)
        if not bucket:
            raise ValueError(f"Unknown storage category: {category}")
        return bucket

    def save(self, key: str, content: bytes, category: str) -> str:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        self.s3.put_object(
            Bucket=bucket,
            Key=cleaned_key,
            Body=content,
            ContentType=mimetypes.guess_type(cleaned_key)[0] or "application/octet-stream"
        )
        return cleaned_key

    def get(self, key: str, category: str) -> bytes:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            resp = self.s3.get_object(Bucket=bucket, Key=cleaned_key)
            return resp["Body"].read()
        except Exception as e:
            # Check for NoSuchKey or generic client errors
            raise FileNotFoundError(f"File not found in S3 bucket {bucket}: {cleaned_key} due to {e}")

    def get_stream(self, key: str, category: str) -> io.BytesIO:
        return io.BytesIO(self.get(key, category))

    def delete(self, key: str, category: str) -> None:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.delete_object(Bucket=bucket, Key=cleaned_key)
        except Exception:
            pass

    def get_download_response(self, key: str, filename: str, category: str, disposition: str = "attachment") -> Response:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.head_object(Bucket=bucket, Key=cleaned_key)
        except Exception:
            raise FileNotFoundError(f"File not found in S3 bucket {bucket}: {cleaned_key}")

        resp = self.s3.get_object(Bucket=bucket, Key=cleaned_key)

        def _stream():
            yield from resp["Body"]

        headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
        return StreamingResponse(
            _stream(),
            media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            headers=headers,
        )

    def exists(self, key: str, category: str = "issuances") -> bool:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.head_object(Bucket=bucket, Key=cleaned_key)
            return True
        except Exception:
            return False

```

## File: backend/tests/test_xlsx_format_contract.py
```
from uuid import UUID

import pytest
from pydantic import ValidationError

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


@pytest.mark.parametrize("formats", [[], ["pdf", "pdf"]])
def test_document_type_rejects_empty_or_duplicate_output_formats(formats):
    with pytest.raises(ValidationError):
        DocumentTypeCreate(
            name="Contract",
            fields=[],
            allowed_output_formats=formats,
        )


def test_document_design_rejects_invalid_output_format():
    with pytest.raises(ValidationError):
        DocumentDesignCreate(
            document_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Invalid design",
            output_format="docx",
        )

```

## File: backend/tests/test_xlsx_analysis.py
```
import io

from openpyxl import Workbook

from app.services.xlsx_analysis import analyze_xlsx_template


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "Customer: {{cliente.nombre}}"
    worksheet.print_area = "A1:C12"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_analyze_xlsx_template_extracts_sheet_token_and_print_area() -> None:
    analysis = analyze_xlsx_template(_workbook_bytes(), {"cliente.nombre"})

    assert analysis.detected_sheets == [
        {
            "name": "Summary",
            "max_row": 1,
            "max_column": 1,
            "print_area": "'Summary'!$A$1:$C$12",
            "merged_ranges": [],
        }
    ]
    assert analysis.detected_tokens == ["cliente.nombre"]
    assert analysis.validation_warnings == []
    assert analysis.image_slots == []


def test_analyze_xlsx_template_warns_for_unknown_schema_token() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["B4"] = "{{cliente.desconocido}}"
    output = io.BytesIO()
    workbook.save(output)

    analysis = analyze_xlsx_template(output.getvalue(), {"cliente.nombre"})

    assert analysis.validation_warnings[0]["type"] == "unknown_schema_token"
    assert analysis.validation_warnings[0]["cell"] == "B4"
    assert analysis.validation_warnings[0]["sheet"] == "Summary"

```

## File: backend/tests/test_xlsx_templates_api.py
```
import io
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.config import settings
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-sub", email="xlsx@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(db_session: SQLAlchemySession, user: User) -> DocumentType:
    document_type = DocumentType(
        name="Workbook",
        description="Workbook template",
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            )
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    workbook.active["A1"] = "{{cliente.nombre}}"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _macro_enabled_workbook_bytes(include_vba_project: bool) -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types><Override ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml" /></Types>',
        )
        if include_vba_project:
            archive.writestr("xl/vbaProject.bin", b"macro")
    return output.getvalue()


def test_upload_list_and_detail_xlsx_template(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Main workbook"},
            files={"file": ("main.xlsx", _workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

        assert response.status_code == 201
        created = response.json()
        assert created["detected_tokens"] == ["cliente.nombre"]
        assert created["document_type_name"] == "Workbook"

        list_response = client.get("/api/xlsx-templates")
        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == created["id"]

        detail_response = client.get(f"/api/xlsx-templates/{created['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["original_filename"] == "main.xlsx"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_upload_rejects_non_xlsx_filename(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)

    for filename in ("macro.xlsm", "notes.txt"):
        response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Invalid workbook"},
            files={"file": (filename, b"not a workbook", "application/octet-stream")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Only .xlsx files are supported"


def test_upload_rejects_renamed_macro_enabled_workbook(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)

    for include_vba_project in (False, True):
        response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Macro workbook"},
            files={
                "file": (
                    "macro.xlsx",
                    _macro_enabled_workbook_bytes(include_vba_project),
                    "application/octet-stream",
                )
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Macro-enabled workbooks not supported"


def test_upload_deletes_stored_workbook_when_database_commit_fails(
    client: TestClient, db_session: SQLAlchemySession, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(db_session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
            with pytest.raises(RuntimeError, match="commit failed"):
                client.post(
                    "/api/xlsx-templates",
                    data={"document_type_id": str(document_type.id), "name": "Failed workbook"},
                    files={"file": ("failed.xlsx", _workbook_bytes(), "application/octet-stream")},
                )

        assert list(tmp_path.iterdir()) == []
    finally:
        settings.xlsx_template_storage_root = original_root

```

## File: backend/tests/test_xlsx_renderer.py
```
from io import BytesIO

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.workbook.defined_name import DefinedName

from app.services.xlsx_images import normalize_image_value
from app.services.xlsx_renderer import render_xlsx_template


def _summary_workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "Customer"
    worksheet["B1"] = "{{cliente.nombre}}"
    worksheet["C1"] = "=SUM(1,2)"
    worksheet.column_dimensions["B"].width = 30
    worksheet.print_area = "A1:C10"
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _repeat_workbook_bytes(repeat_json: str = '[{"sheet":"Items","row":2,"list":"items"}]') -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Items"
    worksheet["A1"] = "Name"
    worksheet["B1"] = "Qty"
    worksheet["A2"] = "{{item.name}}"
    worksheet["B2"] = "{{item.qty}}"
    worksheet["Z1"] = repeat_json
    worksheet.column_dimensions["Z"].hidden = True
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Items'!$Z$1"))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_render_replaces_cell_token_and_preserves_workbook_structure() -> None:
    output = render_xlsx_template(_summary_workbook_bytes(), {"cliente": {"nombre": "ACME"}})
    workbook = load_workbook(BytesIO(output), data_only=False)
    worksheet = workbook["Summary"]

    assert worksheet["B1"].value == "ACME"
    assert str(worksheet.print_area) == "'Summary'!$A$1:$C$10"
    assert worksheet.column_dimensions["B"].width == 30
    assert worksheet["C1"].value == "=SUM(1,2)"


def test_render_escapes_payload_formula_values() -> None:
    output = render_xlsx_template(_summary_workbook_bytes(), {"cliente": {"nombre": "=HYPERLINK(\"x\")"}})
    workbook = load_workbook(BytesIO(output), data_only=False)

    assert workbook["Summary"]["B1"].value == "'=HYPERLINK(\"x\")"


def test_render_repeats_explicit_row_for_list_items() -> None:
    output = render_xlsx_template(
        _repeat_workbook_bytes(),
        {"items": [{"name": "A", "qty": 1}, {"name": "B", "qty": 2}]},
    )
    rendered = load_workbook(BytesIO(output))["Items"]

    assert rendered["A2"].value == "A"
    assert rendered["B2"].value == "1"
    assert rendered["A3"].value == "B"
    assert rendered["B3"].value == "2"


def test_empty_repeat_row_updates_later_repeat_offsets() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Items"
    worksheet["A2"] = "{{item.name}}"
    worksheet["A3"] = "{{item.name}}"
    worksheet["Z1"] = (
        '[{"sheet":"Items","row":2,"list":"empty_items"},'
        '{"sheet":"Items","row":3,"list":"items"}]'
    )
    worksheet.column_dimensions["Z"].hidden = True
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Items'!$Z$1"))
    buffer = BytesIO()
    workbook.save(buffer)

    output = render_xlsx_template(buffer.getvalue(), {"empty_items": [], "items": [{"name": "A"}]})
    rendered = load_workbook(BytesIO(output))["Items"]

    assert rendered["A2"].value == "A"
    assert rendered["A3"].value is None


def test_render_rejects_merged_cells_intersecting_repeat_row() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Items"
    worksheet["A2"] = "{{item.name}}"
    worksheet.merge_cells("A2:B2")
    worksheet["Z1"] = '[{"sheet":"Items","row":2,"list":"items"}]'
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Items'!$Z$1"))
    buffer = BytesIO()
    workbook.save(buffer)

    with pytest.raises(ValueError, match="unsupported_merge_in_repeat_range"):
        render_xlsx_template(buffer.getvalue(), {"items": [{"name": "A"}]})


def test_normalize_png_data_url() -> None:
    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    image = normalize_image_value(data_url)

    assert image.mime_type == "image/png"
    assert image.width >= 1
    assert image.height >= 1


def test_render_inserts_explicitly_anchored_image() -> None:
    data_url = (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    output = render_xlsx_template(_summary_workbook_bytes(), {}, {"Summary!D4": data_url})
    workbook = load_workbook(BytesIO(output))

    assert len(workbook["Summary"]._images) == 1


def test_normalize_rejects_invalid_base64_data_url() -> None:
    with pytest.raises(ValueError, match="invalid_image_payload"):
        normalize_image_value("data:image/png;base64,not-valid-base64")

```

## File: backend/tests/test_xlsx_preview.py
```
import io

from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.workbook.defined_name import DefinedName
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.config import settings
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-preview-sub", email="xlsx-preview@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(db_session: SQLAlchemySession, user: User) -> DocumentType:
    document_type = DocumentType(
        name="Preview Workbook",
        description="Preview workbook type",
        allowed_output_formats=["pdf", "xlsx"],
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            )
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["B1"] = "{{cliente.nombre}}"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _repeat_workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "{{item.name}}"
    worksheet["Z1"] = '[{"sheet":"Summary","row":1,"list":"items"}]'
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Summary'!$Z$1"))
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _invalid_repeat_metadata_workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "Value"
    worksheet["Z1"] = '[{"sheet":"Missing","row":1,"list":"items"}]'
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Summary'!$Z$1"))
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_preview_returns_sheet_cells(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        upload_response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Preview template"},
            files={
                "file": (
                    "preview.xlsx",
                    _workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert upload_response.status_code == 201
        template_id = upload_response.json()["id"]

        response = client.post(
            f"/api/xlsx-templates/{template_id}/preview",
            json={"mock_data": {"cliente": {"nombre": "ACME"}}},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["sheets"][0]["name"] == "Summary"
        assert body["sheets"][0]["cells"][0]["address"] == "B1"
        assert body["sheets"][0]["cells"][0]["value"] == "ACME"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_uses_template_mock_data_when_body_missing(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        template_id = _upload_preview_template(client, document_type.id)
        template = db_session.get(XlsxTemplate, template_id)
        template.mock_data = {"cliente": {"nombre": "Stored"}}
        db_session.commit()

        response = client.post(f"/api/xlsx-templates/{template_id}/preview")

        assert response.status_code == 200
        assert response.json()["sheets"][0]["cells"][0]["value"] == "Stored"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_empty_mock_data_does_not_fall_back_to_template_mock_data(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        template_id = _upload_preview_template(client, document_type.id)
        template = db_session.get(XlsxTemplate, template_id)
        template.mock_data = {"cliente": {"nombre": "Stored"}}
        db_session.commit()

        response = client.post(f"/api/xlsx-templates/{template_id}/preview", json={"mock_data": {}})

        assert response.status_code == 200
        assert response.json()["sheets"][0]["cells"][0]["value"] == ""
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_returns_400_for_renderer_validation_error(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        upload_response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Repeat template"},
            files={
                "file": (
                    "repeat.xlsx",
                    _repeat_workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post(
            f"/api/xlsx-templates/{upload_response.json()['id']}/preview",
            json={"mock_data": {"items": "not-a-list"}},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "repeat_list_must_be_array"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_returns_400_for_invalid_repeat_metadata(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        upload_response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Invalid repeat template"},
            files={
                "file": (
                    "invalid-repeat.xlsx",
                    _invalid_repeat_metadata_workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post(f"/api/xlsx-templates/{upload_response.json()['id']}/preview")

        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_repeat_metadata"
    finally:
        settings.xlsx_template_storage_root = original_root


def _upload_preview_template(client: TestClient, document_type_id) -> str:
    response = client.post(
        "/api/xlsx-templates",
        data={"document_type_id": str(document_type_id), "name": "Preview template"},
        files={
            "file": (
                "preview.xlsx",
                _workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201
    return response.json()["id"]

```

## File: backend/tests/test_xlsx_designs.py
```
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_design import DocumentDesign
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-design-sub", email="xlsx-design@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(
    db_session: SQLAlchemySession,
    user: User,
    name: str = "Workbook Type",
    allowed_output_formats: list[str] | None = None,
) -> DocumentType:
    document_type = DocumentType(
        name=name,
        description=f"{name} description",
        allowed_output_formats=allowed_output_formats or ["pdf"],
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            )
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _xlsx_template(
    db_session: SQLAlchemySession,
    user: User,
    document_type: DocumentType,
    name: str = "Workbook Template",
    validation_warnings: list[dict] | None = None,
) -> XlsxTemplate:
    template = XlsxTemplate(
        document_type=document_type,
        name=name,
        description=None,
        storage_key=f"{name}.xlsx",
        original_filename=f"{name}.xlsx",
        detected_sheets=[],
        detected_tokens=["cliente.nombre"],
        image_slots=[],
        validation_warnings=validation_warnings or [],
        created_by=user,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def test_create_rejects_xlsx_when_document_type_allows_only_pdf(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf"])

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
        },
    )

    assert response.status_code == 400
    assert "does not allow xlsx output" in response.json()["detail"]


def test_create_requires_template_for_xlsx_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX designs require xlsx_template_id"


def test_create_rejects_xlsx_template_on_pdf_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "PDF design",
            "output_format": "pdf",
            "xlsx_template_id": str(template.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "PDF designs cannot reference an XLSX template"


def test_create_rejects_xlsx_template_from_another_document_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(
        db_session, user, name="Primary Type", allowed_output_formats=["pdf", "xlsx"]
    )
    other_type = _document_type(
        db_session, user, name="Other Type", allowed_output_formats=["pdf", "xlsx"]
    )
    template = _xlsx_template(db_session, user, other_type)

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
            "xlsx_template_id": str(template.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template must belong to the design document type"


def test_update_applies_xlsx_design_validation(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)
    create_response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "PDF design",
            "output_format": "pdf",
        },
    )
    assert create_response.status_code == 201
    design_id = create_response.json()["id"]

    missing_template = client.put(
        f"/api/document-designs/{design_id}",
        json={
            "name": "Workbook design",
            "description": None,
            "output_format": "xlsx",
        },
    )
    assert missing_template.status_code == 400
    assert missing_template.json()["detail"] == "XLSX designs require xlsx_template_id"

    valid_update = client.put(
        f"/api/document-designs/{design_id}",
        json={
            "name": "Workbook design",
            "description": None,
            "output_format": "xlsx",
            "xlsx_template_id": str(template.id),
        },
    )
    assert valid_update.status_code == 200
    assert valid_update.json()["output_format"] == "xlsx"
    assert valid_update.json()["xlsx_template_id"] == str(template.id)


def test_activate_xlsx_design_succeeds_without_pdf_pages(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_activate_xlsx_design_fails_when_template_has_warnings(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(
        db_session,
        user,
        document_type,
        validation_warnings=[{"type": "unknown_schema_token", "cell": "A1"}],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template has validation warnings"


def test_activate_xlsx_design_rechecks_allowed_output_formats(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf"])
    template = _xlsx_template(db_session, user, document_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert "does not allow xlsx output" in response.json()["detail"]


def test_activate_xlsx_design_rechecks_template_document_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(
        db_session, user, name="Primary Type", allowed_output_formats=["pdf", "xlsx"]
    )
    other_type = _document_type(
        db_session, user, name="Other Type", allowed_output_formats=["pdf", "xlsx"]
    )
    template = _xlsx_template(db_session, user, other_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template must belong to the design document type"

```

## File: backend/tests/test_xlsx_issuance_generation.py
```
from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook, load_workbook

from app.services.document_generation import XLSX_MIME_TYPE, generate_document_file


class _Storage:
    def __init__(self, workbook_bytes: bytes) -> None:
        self.workbook_bytes = workbook_bytes

    def get(self, key: str, category: str) -> bytes:
        assert key == "template.xlsx"
        assert category == "xlsx_templates"
        return self.workbook_bytes


class _Template:
    storage_key = "template.xlsx"


class _Design:
    output_format = "xlsx"
    xlsx_template = _Template()


class _Issuance:
    id = uuid4()
    design_version = _Design()
    input_data = {"cliente": {"nombre": "ACME"}}


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    workbook.active["A1"] = "{{cliente.nombre}}"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_xlsx_mime_type_constant() -> None:
    assert XLSX_MIME_TYPE == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_generate_document_file_renders_xlsx_workbook() -> None:
    issuance = _Issuance()
    generated = generate_document_file(issuance, db=None, storage_provider=_Storage(_workbook_bytes()))

    assert generated.mime_type == XLSX_MIME_TYPE
    assert generated.filename == f"{issuance.id}.xlsx"
    assert generated.extension == "xlsx"
    workbook = load_workbook(BytesIO(generated.content))
    assert workbook.active["A1"].value == "ACME"

```

## File: backend/tests/test_async_generation_jobs.py
```
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.config import settings
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_type import DocumentType
from app.models.user import User
from app.services.document_generation import GeneratedDocument
from app.workers.document_generation import generate_document_pdf
from app.utils.signature import generate_issuance_signature


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub=f"async-sub-{uuid.uuid4()}", email=f"async-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    from app.auth.session_service import create_session
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_design(db_session: SQLAlchemySession, user: User) -> DocumentDesign:
    document_type = DocumentType(
        name=f"Async Type {uuid.uuid4()}",
        description="Async test document type",
        created_by=user,
        fields=[],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Async Design",
        description="Async test design",
        status="active",
        version_group_id=uuid.uuid4(),
        version_number=1,
        created_by=user,
    )
    db_session.add_all([document_type, design])
    db_session.commit()
    db_session.refresh(design)
    return design


def test_enqueue_endpoint_flow(
    client: TestClient,
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)

    # 1. Disable eager mode temporarily to assert queue status
    monkeypatch.setattr(settings, "celery_task_always_eager", False)

    # Mock Celery delay method to prevent calling Redis
    called_delay = False
    def mock_delay(*args, **kwargs):
        nonlocal called_delay
        called_delay = True
        class MockAsyncResult:
            id = "mock-task-123"
        return MockAsyncResult()

    import app.workers.document_generation as dg
    monkeypatch.setattr(dg.generate_document, "delay", mock_delay)

    response = client.post(f"/api/document-designs/{design.id}/generate", json={"name": "Acme"})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["celery_task_id"] == "mock-task-123"
    assert called_delay is True

    # Check database state
    issuance = db_session.get(DocumentIssuance, data["id"])
    assert issuance is not None
    assert issuance.status == "queued"
    assert issuance.celery_task_id == "mock-task-123"
    assert issuance.storage_key is None


def test_worker_success_path(
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # 1. Create User, Design and Queued Issuance
    user = User(sub=f"async-sub-{uuid.uuid4()}", email="worker@example.com")
    db_session.add(user)
    db_session.commit()

    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={"name": "Worker Success"},
        status="queued",
    )
    db_session.add(issuance)
    db_session.commit()

    # Mock document generation
    monkeypatch.setattr(
        "app.workers.document_generation.generate_document_file",
        lambda *args, **kwargs: GeneratedDocument(
            content=b"%PDF-dummy-success",
            mime_type="application/pdf",
            filename=f"{issuance.id}.pdf",
            extension="pdf",
        ),
    )

    # Call worker task directly
    generate_document_pdf(issuance.id)

    # Reload from DB
    db_session.expire_all()
    updated = db_session.get(DocumentIssuance, issuance.id)
    assert updated.status == "success"
    assert updated.storage_key is not None
    assert updated.output_format == "pdf"
    assert updated.mime_type == "application/pdf"
    assert updated.filename == f"{issuance.id}.pdf"
    assert updated.completed_at is not None
    assert updated.started_at is not None
    assert updated.error_message is None

    # Verify storage contains the file
    from app.dependencies import get_storage_provider
    storage = get_storage_provider()
    assert storage.exists(updated.storage_key) is True
    assert storage.get(updated.storage_key, "issuances") == b"%PDF-dummy-success"

    # Verify tracelog
    tracelog = db_session.query(DocumentTracelog).filter_by(issuance_id=issuance.id).first()
    assert tracelog is not None
    assert tracelog.event_type == "generation"


def test_worker_failure_path(
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(sub=f"async-sub-{uuid.uuid4()}", email="worker-fail@example.com")
    db_session.add(user)
    db_session.commit()

    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={"name": "Worker Fail"},
        status="queued",
    )
    db_session.add(issuance)
    db_session.commit()

    # Force an exception during rendering
    def raise_err(*args, **kwargs):
        raise RuntimeError("PDF engine crashed horribly!")
    monkeypatch.setattr("app.workers.document_generation.generate_document_file", raise_err)

    # Call worker task
    with pytest.raises(Exception):
        generate_document_pdf(issuance.id)

    # Reload from DB
    db_session.expire_all()
    updated = db_session.get(DocumentIssuance, issuance.id)
    assert updated.status == "failure"
    assert updated.completed_at is not None
    assert "PDF engine crashed horribly" in updated.error_message


def test_worker_idempotency(
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(sub=f"async-sub-{uuid.uuid4()}", email="worker-idem@example.com")
    db_session.add(user)
    db_session.commit()

    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={"name": "Worker Idem"},
        status="success",
        storage_key="existing_key.pdf",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(issuance)
    db_session.commit()

    # Track if generator is called
    generator_called = False
    def track_call(*args, **kwargs):
        nonlocal generator_called
        generator_called = True
        raise AssertionError("generator should not be called for completed issuance")
    monkeypatch.setattr("app.workers.document_generation.generate_document_file", track_call)

    # Call task
    generate_document_pdf(issuance.id)

    assert generator_called is False
    # State should remain unchanged
    db_session.refresh(issuance)
    assert issuance.status == "success"
    assert issuance.storage_key == "existing_key.pdf"


def test_download_share_preview_guards_409(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={},
        status="queued",
    )
    db_session.add(issuance)
    db_session.commit()

    # Authenticated download -> 409
    resp_dl = client.get(f"/api/issuances/{issuance.id}/download")
    assert resp_dl.status_code == 409

    # Share -> 409
    resp_sh = client.post(f"/api/issuances/{issuance.id}/share")
    assert resp_sh.status_code == 409

    # Public download -> 409
    sig = generate_issuance_signature(issuance.id)
    resp_pub = client.get(f"/api/public/document-issuances/{issuance.id}/download?signature={sig}")
    assert resp_pub.status_code == 409

```

## File: backend/tests/test_document_tracelogs.py
```
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_type import DocumentType
from app.models.user import User
from app.services.document_generation import GeneratedDocument


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub=f"trace-sub-{uuid.uuid4()}", email=f"trace-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_design(db_session: SQLAlchemySession, user: User) -> DocumentDesign:
    document_type = DocumentType(
        name=f"Trace Type {uuid.uuid4()}",
        description="Trace test document type",
        created_by=user,
        fields=[],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Trace Design",
        description="Trace test design",
        status="active",
        version_group_id=uuid.uuid4(),
        version_number=1,
        created_by=user,
    )
    db_session.add_all([document_type, design])
    db_session.commit()
    db_session.refresh(design)
    return design


def _create_issuance(
    db_session: SQLAlchemySession,
    user: User,
    design: DocumentDesign,
    *,
    status: str = "success",
) -> DocumentIssuance:
    issuance = DocumentIssuance(
        design_version_id=design.id,
        file_path=f"/tmp/{uuid.uuid4()}.pdf",
        user_id=user.id,
        input_data={"cliente": "Acme"},
        status=status,
    )
    db_session.add(issuance)
    db_session.commit()
    db_session.refresh(issuance)
    return issuance


def test_document_tracelogs_persist_chronologically(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = _create_issuance(db_session, user, design)

    db_session.add_all(
        [
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=user.id,
                event_type="generation",
                metadata_={"source": "generate"},
            ),
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=user.id,
                event_type="download",
                metadata_={"source": "download"},
            ),
        ]
    )
    db_session.commit()

    db_session.refresh(issuance)
    assert [row.event_type for row in issuance.tracelogs] == ["generation", "download"]
    assert issuance.tracelogs[0].metadata_ == {"source": "generate"}


def test_deleting_issuance_cascades_document_tracelogs(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = _create_issuance(db_session, user, design)
    tracelog = DocumentTracelog(
        issuance_id=issuance.id,
        user_id=user.id,
        event_type="generation",
        metadata_={"source": "generate"},
    )
    db_session.add(tracelog)
    db_session.commit()
    tracelog_id = tracelog.id

    db_session.delete(issuance)
    db_session.commit()

    assert db_session.get(DocumentTracelog, tracelog_id) is None


def test_document_tracelog_rejects_invalid_event_type(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = _create_issuance(db_session, user, design)

    db_session.add(
        DocumentTracelog(
            issuance_id=issuance.id,
            user_id=user.id,
            event_type="preview",
            metadata_={},
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_document_issuance_rejects_invalid_status(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)

    db_session.add(
        DocumentIssuance(
            design_version_id=design.id,
            file_path=f"/tmp/{uuid.uuid4()}.pdf",
            user_id=user.id,
            input_data={},
            status="pending",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_generate_document_creates_generation_tracelog(
    client: TestClient,
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    
    # Mock generation in the Celery worker
    monkeypatch.setattr(
        "app.workers.document_generation.generate_document_file",
        lambda *args, **kwargs: GeneratedDocument(
            content=b"%PDF-1.4\n%%EOF",
            mime_type="application/pdf",
            filename="test.pdf",
            extension="pdf",
        ),
    )

    response = client.post(f"/api/document-designs/{design.id}/generate", json={"name": "Acme"})

    assert response.status_code == 202
    data = response.json()
    issuance = db_session.get(DocumentIssuance, data["id"])
    assert issuance is not None
    assert issuance.status == "success"
    assert len(issuance.tracelogs) == 1
    tracelog = issuance.tracelogs[0]
    assert tracelog.event_type == "generation"
    assert tracelog.user_id == user.id
    assert tracelog.metadata_["source"] == "Celery Worker"
    assert tracelog.metadata_["design_id"] == str(design.id)

```

## File: frontend/src/lib/xlsxTemplates.ts
```
import { apiFetch, jsonOrError } from "./api";

export interface XlsxTemplateDetail {
  id: string;
  document_type_id: string;
  document_type_name: string;
  name: string;
  description?: string | null;
  original_filename: string;
  detected_sheets: Array<Record<string, unknown>>;
  detected_tokens: string[];
  image_slots: Array<Record<string, unknown>>;
  validation_warnings: Array<Record<string, unknown>>;
  mock_data?: Record<string, unknown> | null;
  created_by_email: string;
  created_at: string;
}

export interface XlsxPreviewResponse {
  sheets: Array<{
    name: string;
    max_row: number;
    max_column: number;
    merged_ranges: string[];
    cells: Array<{
      address: string;
      value: string | number | boolean | null;
      style: Record<string, unknown>;
    }>;
  }>;
  warnings: Array<Record<string, unknown>>;
}

export async function listXlsxTemplates(documentTypeId?: string): Promise<XlsxTemplateDetail[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/xlsx-templates${query}`));
}

export async function getXlsxTemplate(id: string): Promise<XlsxTemplateDetail | null> {
  const res = await apiFetch(`/api/xlsx-templates/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function uploadXlsxTemplate(payload: {
  documentTypeId: string;
  name: string;
  description?: string | null;
  file: File;
}): Promise<XlsxTemplateDetail> {
  const formData = new FormData();
  formData.append("document_type_id", payload.documentTypeId);
  formData.append("name", payload.name);
  if (payload.description) formData.append("description", payload.description);
  formData.append("file", payload.file);
  return jsonOrError(await apiFetch("/api/xlsx-templates", { method: "POST", body: formData }));
}

export async function previewXlsxTemplate(
  id: string,
  mockData?: Record<string, unknown>,
): Promise<XlsxPreviewResponse> {
  return jsonOrError(
    await apiFetch(`/api/xlsx-templates/${id}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mock_data: mockData ?? null }),
    }),
  );
}

```

## File: frontend/src/pages/content/XlsxTemplatesPage.tsx
```
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function XlsxTemplatesPage() {
  const [items, setItems] = useState<XlsxTemplateDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listXlsxTemplates()
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "We couldn't load XLSX templates.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Content Library" }, { label: "XLSX Templates" }]}
        title="XLSX Templates"
        actions={
          <Link to="/content/xlsx-templates/upload" className="rounded bg-primary px-md py-xs text-sm font-bold text-on-primary">
            Upload XLSX
          </Link>
        }
      />
      {error ? <p className="mb-md text-sm text-error">{error}</p> : null}
      <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-outline-variant bg-surface-container-low">
              <th className="px-md py-sm text-label-caps text-secondary">Name</th>
              <th className="px-md py-sm text-label-caps text-secondary">Document Type</th>
              <th className="px-md py-sm text-label-caps text-secondary">Tokens</th>
              <th className="px-md py-sm text-label-caps text-secondary">Warnings</th>
              <th className="px-md py-sm text-label-caps text-secondary">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant">
            {(items ?? []).map((item) => (
              <tr key={item.id} className="hover:bg-surface">
                <td className="px-md py-md">
                  <Link className="font-bold text-primary hover:underline" to={`/content/xlsx-templates/${item.id}`}>
                    {item.name}
                  </Link>
                </td>
                <td className="px-md py-md">{item.document_type_name}</td>
                <td className="px-md py-md">{item.detected_tokens.length}</td>
                <td className="px-md py-md">{item.validation_warnings.length}</td>
                <td className="px-md py-md">{new Date(item.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

```

## File: frontend/src/pages/content/XlsxTemplateUploadPage.tsx
```
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listDocumentTypes, type DocumentTypeListItem } from "../../lib/documentTypes";
import { uploadXlsxTemplate } from "../../lib/xlsxTemplates";

export default function XlsxTemplateUploadPage() {
  const navigate = useNavigate();
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listDocumentTypes()
      .then((rows) => {
        if (cancelled) return;
        setDocumentTypes(rows);
        setDocumentTypeId(rows[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load document types.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!file) {
      setError("Choose an XLSX file.");
      return;
    }
    if (!documentTypeId) {
      setError("Choose a document type.");
      return;
    }
    try {
      const created = await uploadXlsxTemplate({
        documentTypeId,
        name,
        description: description || null,
        file,
      });
      navigate(`/content/xlsx-templates/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't upload this workbook.");
    }
  };

  return (
    <section className="rounded border border-outline-variant bg-surface-container-lowest p-lg">
      <h2 className="font-headings text-[18px] font-bold text-on-surface">Upload XLSX Template</h2>
      {error ? <p className="mt-md rounded border border-error/30 p-sm text-sm text-error">{error}</p> : null}
      <form onSubmit={handleSubmit} className="mt-md space-y-md">
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Document Type
          <select
            value={documentTypeId}
            onChange={(event) => setDocumentTypeId(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface"
          >
            {documentTypes.map((documentType) => (
              <option key={documentType.id} value={documentType.id}>
                {documentType.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Name
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface"
          />
        </label>
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface"
          />
        </label>
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          XLSX File
          <input
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-xs block w-full text-sm text-on-surface"
          />
        </label>
        <div className="flex justify-end">
          <button type="submit" className="rounded bg-primary px-lg py-sm text-sm font-bold text-white">
            Upload XLSX
          </button>
        </div>
      </form>
    </section>
  );
}

```

## File: frontend/src/pages/content/XlsxTemplateDetailPage.tsx
```
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import {
  getXlsxTemplate,
  previewXlsxTemplate,
  type XlsxPreviewResponse,
  type XlsxTemplateDetail,
} from "../../lib/xlsxTemplates";
import { XlsxPreviewGrid } from "./components/XlsxPreviewGrid";

export default function XlsxTemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [template, setTemplate] = useState<XlsxTemplateDetail | null>(null);
  const [preview, setPreview] = useState<XlsxPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getXlsxTemplate(id)
      .then((data) => {
        if (cancelled || !data) return;
        setTemplate(data);
        return previewXlsxTemplate(data.id, data.mock_data ?? {});
      })
      .then((data) => {
        if (!cancelled && data) setPreview(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "We couldn't load this template.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!template) {
    return <p className="text-sm text-on-surface-variant">{error ?? "Loading..."}</p>;
  }

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Content Library" }, { label: "XLSX Templates" }]}
        title={template.name}
        actions={
          <Link to="/content/xlsx-templates" className="rounded border border-outline px-md py-xs text-sm font-bold text-primary">
            Back
          </Link>
        }
      />
      {error ? <p className="mb-md text-sm text-error">{error}</p> : null}
      <div className="mb-lg grid gap-md md:grid-cols-3">
        <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <p className="text-label-caps text-secondary">Document Type</p>
          <p className="mt-xs font-bold text-on-surface">{template.document_type_name}</p>
        </div>
        <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <p className="text-label-caps text-secondary">Original File</p>
          <p className="mt-xs font-bold text-on-surface">{template.original_filename}</p>
        </div>
        <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <p className="text-label-caps text-secondary">Validation Warnings</p>
          <p className="mt-xs font-bold text-on-surface">{template.validation_warnings.length}</p>
        </div>
      </div>
      <div className="mb-lg rounded border border-outline-variant bg-surface-container-lowest p-md">
        <p className="mb-sm text-label-caps text-secondary">Detected Tokens</p>
        <div className="flex flex-wrap gap-xs">
          {template.detected_tokens.map((token) => (
            <span key={token} className="rounded bg-surface-container px-sm py-xs font-mono text-xs">
              {token}
            </span>
          ))}
        </div>
      </div>
      <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Preview</h2>
      {preview ? <XlsxPreviewGrid preview={preview} /> : <p className="text-sm text-on-surface-variant">Loading preview...</p>}
    </section>
  );
}

```

## File: frontend/src/pages/content/components/XlsxPreviewGrid.tsx
```
import type { XlsxPreviewResponse } from "../../../lib/xlsxTemplates";

function columnName(index: number): string {
  let value = "";
  let current = index;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    value = String.fromCharCode(65 + remainder) + value;
    current = Math.floor((current - 1) / 26);
  }
  return value;
}

export function XlsxPreviewGrid({ preview }: { preview: XlsxPreviewResponse }) {
  const sheet = preview.sheets[0];
  if (!sheet) {
    return <p className="text-sm text-on-surface-variant">No preview available.</p>;
  }

  const byAddress = new Map(sheet.cells.map((cell) => [cell.address, cell]));
  const columns = Array.from({ length: Math.min(sheet.max_column, 12) }, (_, index) => index + 1);
  const rows = Array.from({ length: Math.min(sheet.max_row, 40) }, (_, index) => index + 1);

  return (
    <div className="overflow-auto rounded border border-outline-variant bg-surface-container-lowest">
      <table className="min-w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="h-8 w-10 border border-outline-variant bg-surface-container-low" />
            {columns.map((column) => (
              <th
                key={column}
                className="h-8 min-w-24 border border-outline-variant bg-surface-container-low px-2 text-secondary"
              >
                {columnName(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row}>
              <th className="h-8 border border-outline-variant bg-surface-container-low px-2 text-secondary">
                {row}
              </th>
              {columns.map((column) => {
                const address = `${columnName(column)}${row}`;
                const cell = byAddress.get(address);
                return (
                  <td
                    key={column}
                    className="h-8 min-w-24 border border-outline-variant px-2 align-top text-on-surface"
                  >
                    {cell?.value == null ? "" : String(cell.value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

```

## File: frontend/src/App.tsx
```
import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthenticatedShell from "./pages/AuthenticatedShell";
import DocumentTypeListPage from "./pages/document-types/DocumentTypeListPage";
import DocumentTypeDetailPage from "./pages/document-types/DocumentTypeDetailPage";
import DocumentTypeCreatePage from "./pages/document-types/DocumentTypeCreatePage";
import TemplatesPage from "./pages/content/TemplatesPage";
import StaticPdfsPage from "./pages/content/StaticPdfsPage";
import HtmlTemplateCreatePage from "./pages/content/HtmlTemplateCreatePage";
import HtmlTemplateDetailPage from "./pages/content/HtmlTemplateDetailPage";
import StaticPdfUploadPage from "./pages/content/StaticPdfUploadPage";
import StaticPdfDetailPage from "./pages/content/StaticPdfDetailPage";
import XlsxTemplatesPage from "./pages/content/XlsxTemplatesPage";
import XlsxTemplateUploadPage from "./pages/content/XlsxTemplateUploadPage";
import XlsxTemplateDetailPage from "./pages/content/XlsxTemplateDetailPage";
import DocumentDesignListPage from "./pages/document-designs/DocumentDesignListPage";
import DocumentDesignCreatePage from "./pages/document-designs/DocumentDesignCreatePage";
import DocumentDesignDetailPage from "./pages/document-designs/DocumentDesignDetailPage";
import VersionHistoryPage from "./pages/document-designs/VersionHistoryPage";
import DocumentLibraryPage from "./pages/document-issuances/DocumentLibraryPage";
import DocumentIssuanceDetailPage from "./pages/document-issuances/DocumentIssuanceDetailPage";
import JobsMonitoringPage from "./pages/document-issuances/JobsMonitoringPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AuthenticatedShell />}>
        <Route index element={<Navigate to="/document-types" replace />} />
        <Route path="document-types" element={<DocumentTypeListPage />} />
        <Route path="document-types/new" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id/edit" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id" element={<DocumentTypeDetailPage />} />
        <Route path="document-designs" element={<DocumentDesignListPage />} />
        <Route path="document-designs/new" element={<DocumentDesignCreatePage />} />
        <Route path="document-designs/:id" element={<DocumentDesignDetailPage />} />
        <Route path="document-designs/:id/versions" element={<VersionHistoryPage />} />
        <Route path="document-issuances" element={<DocumentLibraryPage />} />
        <Route path="document-issuances/:id" element={<DocumentIssuanceDetailPage />} />
        <Route path="generation-jobs" element={<JobsMonitoringPage />} />
        <Route path="content/templates" element={<TemplatesPage />} />
        <Route path="content/templates/new" element={<HtmlTemplateCreatePage />} />
        <Route path="content/templates/:id" element={<HtmlTemplateDetailPage />} />
        <Route path="content/templates/:id/edit" element={<HtmlTemplateCreatePage />} />
        <Route path="content/static" element={<StaticPdfsPage />} />
        <Route path="content/static-pdfs/upload" element={<StaticPdfUploadPage />} />
        <Route path="content/static-pdfs/:id" element={<StaticPdfDetailPage />} />
        <Route path="content/xlsx-templates" element={<XlsxTemplatesPage />} />
        <Route path="content/xlsx-templates/upload" element={<XlsxTemplateUploadPage />} />
        <Route path="content/xlsx-templates/:id" element={<XlsxTemplateDetailPage />} />
      </Route>
    </Routes>
  );
}

export default App;

```

## File: frontend/src/pages/AuthenticatedShell.tsx
```
import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { type CurrentUser, fetchCurrentUser, logout } from "../lib/api";


const ROUTE_LABELS: Record<string, string> = {
  "document-types": "Document Types",
  "document-designs": "Document Designs",
  "document-issuances": "Documents Library",
  "generation-jobs": "Generation Jobs",
  content: "Content Library",
  new: "New",
  versions: "Version History",
  templates: "Templates",
  "static-pdfs": "Static PDFs",
  "xlsx-templates": "XLSX Templates",
  static: "Static PDFs",
  upload: "Upload",
};

function initialsFromEmail(email: string): string {
  if (!email) return "?";
  const [local] = email.split("@");
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return local.slice(0, 2).toUpperCase();
}

function buildBreadcrumbs(pathname: string): { label: string; to: string }[] {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return [];
  const crumbs: { label: string; to: string }[] = [];
  let acc = "";
  for (const seg of segments) {
    acc += `/${seg}`;
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg);
    const label = ROUTE_LABELS[seg] ?? (isUuid ? seg.slice(0, 8) + "…" : seg);
    crumbs.push({ label, to: acc });
  }
  return crumbs;
}

export default function AuthenticatedShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [hoverExpanded, setHoverExpanded] = useState(false);
  const [contentMenuOpen, setContentMenuOpen] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      try {
        const currentUser = await fetchCurrentUser();
        if (cancelled) return;
        if (currentUser === null) {
          navigate("/login?error=session_expired");
          return;
        }
        setUser(currentUser);
      } catch {
        if (!cancelled) navigate("/login?error=session_expired");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadUser();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const handleSignOut = async () => {
    await logout();
    navigate("/login");
  };

  const breadcrumbs = useMemo(() => buildBreadcrumbs(location.pathname), [location.pathname]);

  const sidebarExpanded = !collapsed || hoverExpanded;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-body text-body-md text-on-surface">
      <aside
        className={`flex h-full shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest py-md transition-all duration-200 ${
          sidebarExpanded ? "w-panel-width-side" : "w-[64px]"
        }`}
        onMouseEnter={() => collapsed && setHoverExpanded(true)}
        onMouseLeave={() => setHoverExpanded(false)}
      >
        <nav className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-sm">
          {/* Document Types */}
          <NavLink
            to="/document-types"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Document Types"
          >
            <span className="material-symbols-outlined shrink-0">schema</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Document Types
            </span>
          </NavLink>

          {/* Content Library (Dropdown/Submenu) */}
          <div className="space-y-1">
            <button
              onClick={() => sidebarExpanded && setContentMenuOpen(!contentMenuOpen)}
              className={`w-full flex items-center justify-between rounded px-sm py-sm text-secondary hover:bg-surface-container transition-colors`}
              title="Content Library"
              type="button"
            >
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined shrink-0">library_books</span>
                <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
                  Content Library
                </span>
              </div>
              {sidebarExpanded && (
                <span className="material-symbols-outlined text-sm transition-transform duration-200">
                  {contentMenuOpen ? "expand_less" : "expand_more"}
                </span>
              )}
            </button>

            {/* Submenu Items */}
            {sidebarExpanded && contentMenuOpen && (
              <div className="pl-6 space-y-1">
                <NavLink
                  to="/content/templates"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="Templates"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">description</span>
                  <span className="text-body-sm whitespace-nowrap">Templates</span>
                </NavLink>
                <NavLink
                  to="/content/static"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="Static PDFs"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">picture_as_pdf</span>
                  <span className="text-body-sm whitespace-nowrap">Static PDFs</span>
                </NavLink>
                <NavLink
                  to="/content/xlsx-templates"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="XLSX Templates"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">table</span>
                  <span className="text-body-sm whitespace-nowrap">XLSX Templates</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Document Designs */}
          <NavLink
            to="/document-designs"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Document Designs"
          >
            <span className="material-symbols-outlined shrink-0">dashboard_customize</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Document Designs
            </span>
          </NavLink>

          {/* Generation Jobs */}
          <NavLink
            to="/generation-jobs"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Generation Jobs"
          >
            <span className="material-symbols-outlined shrink-0">list_alt</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Generation Jobs
            </span>
          </NavLink>

          {/* Documents Library */}
          <NavLink
            to="/document-issuances"
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Documents Library"
          >
            <span className="material-symbols-outlined shrink-0">folder_open</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Documents Library
            </span>
          </NavLink>
        </nav>

        <div className="space-y-1 border-t border-outline-variant px-sm pt-md">
          <span
            className="flex cursor-default items-center gap-3 rounded px-sm py-sm text-secondary"
            title="Support"
          >
            <span className="material-symbols-outlined shrink-0">help</span>
            <span className={`whitespace-nowrap text-body-sm ${sidebarExpanded ? "opacity-100" : "opacity-0"}`}>
              Support
            </span>
          </span>
          <span
            className="flex cursor-default items-center gap-3 rounded px-sm py-sm text-secondary"
            title="Logs"
          >
            <span className="material-symbols-outlined shrink-0">history</span>
            <span className={`whitespace-nowrap text-body-sm ${sidebarExpanded ? "opacity-100" : "opacity-0"}`}>
              Logs
            </span>
          </span>
        </div>
      </aside>

      {loading ? null : (
        <main className="flex h-screen flex-1 flex-col overflow-hidden">
          <header className="z-50 flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface px-lg">
            <div className="flex items-center gap-md">
              <button
                className="rounded p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                onClick={() => setCollapsed((v) => !v)}
                title={collapsed ? "Expand menu" : "Collapse menu"}
                type="button"
              >
                <span className="material-symbols-outlined">menu</span>
              </button>
              <Link
                to="/"
                className="rounded p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Home"
              >
                <span className="material-symbols-outlined">home</span>
              </Link>
              {breadcrumbs.length > 0 ? (
                <nav className="flex items-center gap-sm">
                  {breadcrumbs.map((crumb, idx) => (
                    <span key={crumb.to} className="flex items-center gap-sm">
                      {idx > 0 ? (
                        <span className="material-symbols-outlined text-sm text-secondary">chevron_right</span>
                      ) : null}
                      <Link
                        to={crumb.to}
                        className={`text-body-sm transition-colors ${
                          idx === breadcrumbs.length - 1
                            ? "font-bold text-on-surface"
                            : "text-secondary hover:text-primary"
                        }`}
                      >
                        {crumb.label}
                      </Link>
                    </span>
                  ))}
                </nav>
              ) : null}
            </div>

            <div className="flex items-center gap-md">
              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-3 text-body-sm text-secondary">
                  search
                </span>
                <input
                  className="w-64 rounded-full border border-outline bg-surface-container-low py-1.5 pl-10 pr-4 text-body-sm focus:border-primary focus:outline-none"
                  placeholder="Global search..."
                  type="text"
                />
              </div>
              <button
                className="rounded-full p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Notifications"
                type="button"
              >
                <span className="material-symbols-outlined">notifications</span>
              </button>
              <button
                className="rounded-full p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Sync status"
                type="button"
              >
                <span className="material-symbols-outlined">cloud_done</span>
              </button>
              <div className="mx-1 h-8 w-px bg-outline-variant" />
              {user ? (
                <div className="flex items-center gap-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-outline bg-primary text-label-caps font-bold text-on-primary">
                    {initialsFromEmail(user.email)}
                  </div>
                  <button
                    className="rounded border border-outline-variant px-md py-xs text-label-caps text-secondary transition-colors hover:border-outline hover:text-primary"
                    type="button"
                    onClick={handleSignOut}
                  >
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-lg">
            <div className="w-full">
              <Outlet />
            </div>
          </div>
        </main>
      )}
    </div>
  );
}

```

## File: frontend/src/pages/content/ContentLibraryPage.tsx
```
import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import {
  listHtmlTemplates,
  listStaticPdfAssets,
  type HtmlTemplateListItem,
  type StaticPdfAssetListItem,
} from "../../lib/content";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function ContentLibraryPage() {
  const [templates, setTemplates] = useState<HtmlTemplateListItem[] | null>(null);
  const [pdfAssets, setPdfAssets] = useState<StaticPdfAssetListItem[] | null>(null);
  const [xlsxTemplates, setXlsxTemplates] = useState<XlsxTemplateDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([listHtmlTemplates(), listStaticPdfAssets(), listXlsxTemplates()])
      .then(([templateRows, pdfRows, xlsxRows]) => {
        if (cancelled) return;
        setTemplates(templateRows);
        setPdfAssets(pdfRows);
        setXlsxTemplates(xlsxRows);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load the content library. Please try again.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Admin" }, { label: "Content Library" }]}
        title="Content Library"
        actions={
          <>
            <Link
              to="/content/templates/new"
              className="rounded bg-primary px-md py-xs font-bold uppercase tracking-wide text-label-caps text-on-primary hover:opacity-90 active:scale-95"
            >
              Create Template
            </Link>
            <Link
              to="/content/static-pdfs/upload"
              className="rounded border border-primary px-md py-xs font-bold uppercase tracking-wide text-label-caps text-primary hover:bg-primary/10"
            >
              Upload PDF
            </Link>
            <Link
              to="/content/xlsx-templates/upload"
              className="rounded border border-primary px-md py-xs font-bold uppercase tracking-wide text-label-caps text-primary hover:bg-primary/10"
            >
              Upload XLSX
            </Link>
          </>
        }
      />

      {error ? <p className="text-sm text-error">{error}</p> : null}

      <div className="space-y-xl">
        {/* TEMPLATES */}
        <section id="templates">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h3 className="font-headings text-headline-md text-on-surface">Templates</h3>
            <Link to="/content/templates/new" className="text-sm font-bold text-primary hover:underline">
              New Template
            </Link>
          </div>

          {templates === null ? null : templates.length === 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No templates yet</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Name</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Document Type</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Tokens</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created By</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {templates.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-surface">
                      <td className="px-md py-md">
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-primary">description</span>
                          <Link to={`/content/templates/${item.id}`} className="font-bold text-primary hover:underline">
                            {item.name}
                          </Link>
                        </div>
                      </td>
                      <td className="px-md py-md text-on-surface">{item.document_type_name}</td>
                      <td className="px-md py-md text-on-surface">{item.token_count}</td>
                      <td className="px-md py-md text-on-surface">{item.created_by_email}</td>
                      <td className="px-md py-md text-on-surface">
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex items-center justify-between border-t border-outline-variant bg-surface-container-low p-md">
                <p className="text-body-sm text-secondary">
                  <span className="font-bold text-on-surface">{templates.length}</span> templates
                </p>
              </div>
            </div>
          )}
        </section>

        <section id="xlsx-templates">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h3 className="font-headings text-headline-md text-on-surface">XLSX Templates</h3>
            <Link to="/content/xlsx-templates/upload" className="text-sm font-bold text-primary hover:underline">
              Upload XLSX
            </Link>
          </div>

          {xlsxTemplates === null ? null : xlsxTemplates.length === 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No XLSX templates yet</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Name</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Document Type</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Tokens</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Warnings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {xlsxTemplates.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-surface">
                      <td className="px-md py-md">
                        <Link to={`/content/xlsx-templates/${item.id}`} className="font-bold text-primary hover:underline">
                          {item.name}
                        </Link>
                      </td>
                      <td className="px-md py-md text-on-surface">{item.document_type_name}</td>
                      <td className="px-md py-md text-on-surface">{item.detected_tokens.length}</td>
                      <td className="px-md py-md text-on-surface">{item.validation_warnings.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* STATIC PDFs */}
        <section id="static-pdfs">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h3 className="font-headings text-headline-md text-on-surface">Static PDFs</h3>
            <Link to="/content/static-pdfs/upload" className="text-sm font-bold text-primary hover:underline">
              Upload PDF
            </Link>
          </div>

          {pdfAssets === null ? null : pdfAssets.length === 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No PDF assets yet</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Filename</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Pages</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created By</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {pdfAssets.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-surface">
                      <td className="px-md py-md">
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-primary">picture_as_pdf</span>
                          <Link to={`/content/static-pdfs/${item.id}`} className="font-bold text-primary hover:underline">
                            {item.filename}
                          </Link>
                        </div>
                      </td>
                      <td className="px-md py-md text-on-surface">{item.page_count}</td>
                      <td className="px-md py-md text-on-surface">{item.created_by_email}</td>
                      <td className="px-md py-md text-on-surface">
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex items-center justify-between border-t border-outline-variant bg-surface-container-low p-md">
                <p className="text-body-sm text-secondary">
                  <span className="font-bold text-on-surface">{pdfAssets.length}</span> PDF assets
                </p>
              </div>
            </div>
          )}
        </section>
      </div>

      <div className="mt-xl">
        <Outlet />
      </div>
    </section>
  );
}

```

## File: frontend/src/lib/documentTypes.ts
```
import { apiFetch } from "./api";

export type FieldType = "string" | "number" | "date" | "boolean";
export type MetadataType = "text" | "number" | "date" | "datetime" | "boolean";
export type OutputFormat = "pdf" | "xlsx";

export interface DocumentTypeFieldIn {
  name: string;
  type: FieldType;
  description: string | null;
}

export interface DocumentTypeField extends DocumentTypeFieldIn {
  id: string;
}

export interface DocumentTypeMetadataIn {
  name: string;
  type: MetadataType;
  required: boolean;
}

export interface DocumentTypeMetadata extends DocumentTypeMetadataIn {
  id: string;
}

export interface DocumentTypeListItem {
  id: string;
  name: string;
  description: string | null;
  field_count: number;
  created_by_email: string;
  created_at: string;
}

export interface DocumentTypeDetail {
  id: string;
  name: string;
  description: string | null;
  fields: DocumentTypeField[];
  metadata_definitions: DocumentTypeMetadata[];
  allowed_output_formats: OutputFormat[];
  created_by_email: string;
  created_at: string;
}

export interface DocumentTypeCreatePayload {
  name: string;
  description: string | null;
  fields: DocumentTypeFieldIn[];
  metadata_definitions: DocumentTypeMetadataIn[];
  allowed_output_formats: OutputFormat[];
}

export async function listDocumentTypes(): Promise<DocumentTypeListItem[]> {
  const res = await apiFetch("/api/document-types");
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json();
}

export async function getDocumentType(id: string): Promise<DocumentTypeDetail | null> {
  const res = await apiFetch(`/api/document-types/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json();
}

export async function createDocumentType(
  payload: DocumentTypeCreatePayload,
): Promise<DocumentTypeDetail> {
  const res = await apiFetch("/api/document-types", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? JSON.stringify(body.detail) : `Unexpected status ${res.status}`);
  }
  return res.json();
}

export async function updateDocumentType(
  id: string,
  payload: DocumentTypeCreatePayload,
): Promise<DocumentTypeDetail> {
  const res = await apiFetch(`/api/document-types/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? JSON.stringify(body.detail) : `Unexpected status ${res.status}`);
  }
  return res.json();
}

```

## File: frontend/src/lib/documentDesigns.ts
```
import { apiFetch, jsonOrError, readErrorMessage } from "./api";
import type { OutputFormat } from "./documentTypes";

export type DesignStatus = "draft" | "active";
export type DesignBlockType = "html_template" | "static_pdf";

export interface DocumentDesignPage {
  id: string;
  block_type: DesignBlockType;
  content_id: string;
  position: number;
  title: string | null;
  notes: string | null;
  config: Record<string, unknown>;
  snapshot: Record<string, unknown>;
  created_at: string;
}

export interface DocumentDesignListItem {
  id: string;
  name: string;
  description: string | null;
  output_format: OutputFormat;
  xlsx_template_id: string | null;
  status: DesignStatus | "superseded";
  version_group_id: string | null;
  version_number: number | null;
  document_type_id: string;
  document_type_name: string;
  page_count: number;
  created_by_email: string;
  created_at: string;
}

export interface DocumentDesignDetail extends Omit<DocumentDesignListItem, "page_count"> {
  pages: DocumentDesignPage[];
  mock_data?: Record<string, unknown> | null;
}

export interface DocumentDesignCreatePayload {
  document_type_id: string;
  name: string;
  description: string | null;
  output_format?: OutputFormat;
  xlsx_template_id?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export interface AddTemplatePagePayload {
  template_id: string;
  title?: string | null;
  notes?: string | null;
  config?: Record<string, unknown>;
}

export interface AddStaticPdfPagePayload {
  static_pdf_asset_id: string;
  title?: string | null;
  notes?: string | null;
  config?: Record<string, unknown>;
}

export interface UpdateDesignPagePayload {
  title?: string | null;
  notes?: string | null;
  config?: Record<string, unknown>;
}

export async function listDocumentDesigns(): Promise<DocumentDesignListItem[]> {
  return jsonOrError(await apiFetch("/api/document-designs"));
}

export async function getDocumentDesign(id: string): Promise<DocumentDesignDetail | null> {
  const res = await apiFetch(`/api/document-designs/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function createDocumentDesign(
  payload: DocumentDesignCreatePayload,
): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch("/api/document-designs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function addTemplateDesignPage(
  designId: string,
  payload: AddTemplatePagePayload,
): Promise<DocumentDesignPage> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/template`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function addStaticPdfDesignPage(
  designId: string,
  payload: AddStaticPdfPagePayload,
): Promise<DocumentDesignPage> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/static-pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function reorderDesignPages(
  designId: string,
  pageIds: string[],
): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/reorder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_ids: pageIds }),
    }),
  );
}

export async function updateDesignPage(
  designId: string,
  pageId: string,
  payload: UpdateDesignPagePayload,
): Promise<DocumentDesignPage> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/${pageId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function deleteDesignPage(designId: string, pageId: string): Promise<void> {
  const res = await apiFetch(`/api/document-designs/${designId}/pages/${pageId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
}

export async function activateDocumentDesign(id: string): Promise<DocumentDesignDetail> {
  return jsonOrError(await apiFetch(`/api/document-designs/${id}/activate`, { method: "POST" }));
}

export async function forkDocumentDesignVersion(designId: string): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/versions`, {
      method: "POST",
    }),
  );
}

export async function listDocumentDesignVersions(designId: string): Promise<DocumentDesignListItem[]> {
  return jsonOrError(await apiFetch(`/api/document-designs/${designId}/versions`));
}

export async function discardDocumentDesignDraft(designId: string): Promise<void> {
  const res = await apiFetch(`/api/document-designs/${designId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
}

export async function previewDocumentDesign(
  designId: string,
  payload: Record<string, unknown>,
): Promise<Blob> {
  const res = await apiFetch(`/api/document-designs/${designId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
  return res.blob();
}

export interface DocumentDesignUpdatePayload {
  name: string;
  description: string | null;
  output_format?: OutputFormat;
  xlsx_template_id?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export async function updateDocumentDesign(
  id: string,
  payload: DocumentDesignUpdatePayload,
): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function generateDocumentDesign(
  designId: string,
  payload: Record<string, unknown> = {},
): Promise<any> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

```

## File: frontend/src/lib/documentIssuances.ts
```
import { apiFetch, jsonOrError } from "./api";

export type DocumentIssuanceStatus = "queued" | "processing" | "success" | "failure";
export type DocumentTracelogType = "generation" | "download" | "share" | string;

export interface DocumentIssuanceFilters {
  design_name?: string;
  id?: string;
  status?: DocumentIssuanceStatus | "";
  created_from?: string;
  created_to?: string;
  metadata_key?: string;
  metadata_value?: string;
}

export interface DocumentIssuanceListItem {
  id: string;
  design_version_id: string;
  design_name: string;
  output_format: "pdf" | "xlsx";
  mime_type?: string | null;
  filename?: string | null;
  preview_storage_key?: string | null;
  status: DocumentIssuanceStatus;
  design_status: string;
  design_version_number: number | null;
  user_id: string;
  generated_by_email: string;
  input_data: Record<string, unknown>;
  metadata_values: Record<string, unknown> | null;
  created_at: string;
  preview_url: string;
  download_url: string;
  celery_task_id?: string | null;
  error_message?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  retry_count?: number;
}

export type DocumentIssuanceDetail = DocumentIssuanceListItem;

export interface DocumentTracelog {
  id: string;
  issuance_id: string;
  event_type: DocumentTracelogType;
  user_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ShareDocumentResponse {
  public_url: string;
}

function buildQuery(filters: DocumentIssuanceFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listDocumentIssuances(
  filters: DocumentIssuanceFilters = {},
): Promise<DocumentIssuanceListItem[]> {
  return jsonOrError(await apiFetch(`/api/issuances${buildQuery(filters)}`));
}

export async function getDocumentIssuance(id: string): Promise<DocumentIssuanceDetail | null> {
  const res = await apiFetch(`/api/issuances/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function getDocumentTracelogs(id: string): Promise<DocumentTracelog[]> {
  return jsonOrError(await apiFetch(`/api/issuances/${id}/tracelogs`));
}

export async function shareDocumentIssuance(id: string): Promise<ShareDocumentResponse> {
  return jsonOrError(await apiFetch(`/api/issuances/${id}/share`, { method: "POST" }));
}

```

## File: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx
```
import { useEffect, useState, useMemo } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createDocumentType, getDocumentType, updateDocumentType, type DocumentTypeCreatePayload, type FieldType, type DocumentTypeMetadataIn, type OutputFormat } from "../../lib/documentTypes";
import { SchemaFieldEditor } from "./components/organisms/SchemaFieldEditor";
import { SchemaMetadataEditor } from "./components/organisms/SchemaMetadataEditor";
import { validateSchemaFields, normalizeSchemaFields } from "../../lib/schemaFields";

type FieldRow = {
  name: string;
  type: FieldType;
  description: string | null;
};

type FormValues = {
  name: string;
  description: string;
  fields: FieldRow[];
  metadata_definitions: DocumentTypeMetadataIn[];
  allowed_output_formats: OutputFormat[];
};

function generateMockPayload(fields: FieldRow[], metadata: DocumentTypeMetadataIn[]) {
  const data: Record<string, any> = {};
  fields.forEach(f => {
    if (!f.name) return;
    const parts = f.name.split(".");
    let current = data;
    parts.forEach((part, index) => {
      const isList = part.endsWith("[]");
      const cleanName = isList ? part.slice(0, -2) : part;
      
      if (index === parts.length - 1) {
        if (isList) {
          current[cleanName] = [f.type === "number" ? 123 : f.type === "boolean" ? true : f.type === "date" ? "2026-07-11" : "Sample"];
        } else {
          current[cleanName] = f.type === "number" ? 123 : f.type === "boolean" ? true : f.type === "date" ? "2026-07-11" : "Sample";
        }
      } else {
        if (isList) {
          if (!current[cleanName]) current[cleanName] = [{}];
          current = current[cleanName][0];
        } else {
          if (!current[cleanName]) current[cleanName] = {};
          current = current[cleanName];
        }
      }
    });
  });

  const meta: Record<string, any> = {};
  metadata.forEach(m => {
    if (!m.name) return;
    meta[m.name] = m.type === "number" ? 123.45 : m.type === "boolean" ? true : m.type === "date" ? "2026-07-11" : m.type === "datetime" ? "2026-07-11T20:00:00Z" : "Sample Text";
  });

  return { data, metadata: meta };
}

function getCurlCode(typeId: string, payload: any, firstMetaName: string): string {
  return `# 1. Generar Documento
curl -X POST "http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -d '${JSON.stringify(payload, null, 2)}'

# 2. Buscar por Metadatos
curl -X GET "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`;
}

function getJSCode(typeId: string, payload: any, firstMetaName: string): string {
  return `// 1. Generar Documento
const generateDoc = async () => {
  const res = await fetch("http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer YOUR_ACCESS_TOKEN"
    },
    body: JSON.stringify(${JSON.stringify(payload, null, 2).replace(/\n/g, "\n      ")})
  });
  const data = await res.json();
  console.log(data);
};

// 2. Buscar por Metadatos
const searchDocs = async () => {
  const url = "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}";
  const res = await fetch(url, {
    headers: {
      "Authorization": "Bearer YOUR_ACCESS_TOKEN"
    }
  });
  const list = await res.json();
  console.log(list);
};`;
}

function getPythonCode(typeId: string, payload: any, firstMetaName: string): string {
  return `import requests

# 1. Generar Documento
url = "http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
payload = ${JSON.stringify(payload, null, 4)}

response = requests.post(url, json=payload, headers=headers)
print("Creado:", response.json())

# 2. Buscar por Metadatos
search_url = "http://localhost:8000/api/issuances"
params = {
    "document_type_id": "${typeId}"${firstMetaName ? `,
    "metadata.${firstMetaName}": "Sample"` : ""}
}
response = requests.get(search_url, params=params, headers=headers)
print("Documentos:", response.json())`;
}

function getJavaCode(typeId: string, payload: any, firstMetaName: string): string {
  return `import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class DocGen {
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newHttpClient();

        // 1. Generar Documento
        String payload = """
${JSON.stringify(payload, null, 4)}
        """;

        HttpRequest reqGen = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer YOUR_ACCESS_TOKEN")
            .POST(HttpRequest.BodyPublishers.ofString(payload))
            .build();

        HttpResponse<String> resGen = client.send(reqGen, HttpResponse.BodyHandlers.ofString());
        System.out.println("Generado: " + resGen.body());

        // 2. Buscar por Metadatos
        String queryUrl = "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}";
        HttpRequest reqQuery = HttpRequest.newBuilder()
            .uri(URI.create(queryUrl))
            .header("Authorization", "Bearer YOUR_ACCESS_TOKEN")
            .GET()
            .build();

        HttpResponse<String> resQuery = client.send(reqQuery, HttpResponse.BodyHandlers.ofString());
        System.out.println("Busqueda: " + resQuery.body());
    }
}`;
}

export default function DocumentTypeCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(isEdit);
  const [activeLang, setActiveLang] = useState<"curl" | "js" | "py" | "java">("curl");
  
  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: "",
      description: "",
      fields: [{ name: "new_field", type: "string", description: "" }],
      metadata_definitions: [],
      allowed_output_formats: ["pdf"],
    },
  });

  const { append, remove, update } = useFieldArray({ control, name: "fields" });
  const { append: appendMeta, remove: removeMeta } = useFieldArray({ control, name: "metadata_definitions" });

  // Watch fields and metadata definitions dynamically
  const watchedFields = watch("fields") || [];
  const watchedMetadata = watch("metadata_definitions") || [];

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getDocumentType(id)
      .then((data) => {
        if (data) {
          reset({
            name: data.name,
            description: data.description || "",
            fields: data.fields.map((f) => ({
              name: f.name,
              type: f.type,
              description: f.description || "",
            })),
            metadata_definitions: data.metadata_definitions.map((m) => ({
              name: m.name,
              type: m.type,
              required: m.required,
            })),
            allowed_output_formats: data.allowed_output_formats ?? ["pdf"],
          });
        }
      })
      .catch((err) => {
        setSubmitError(err instanceof Error ? err.message : "Failed to load document type.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);

    const validationError = validateSchemaFields(values.fields);
    if (validationError) {
      setSubmitError(validationError);
      return;
    }

    const normalizedFields = normalizeSchemaFields(values.fields);
    const allowedOutputFormats = values.allowed_output_formats.filter(
      (format): format is OutputFormat => format === "pdf" || format === "xlsx",
    );

    try {
      const payload: DocumentTypeCreatePayload = {
        name: values.name,
        description: values.description || null,
        fields: normalizedFields,
        metadata_definitions: values.metadata_definitions,
        allowed_output_formats: allowedOutputFormats.length ? allowedOutputFormats : (["pdf"] as OutputFormat[]),
      };
      const saved = isEdit
        ? await updateDocumentType(id!, payload)
        : await createDocumentType(payload);
      navigate(`/document-types/${saved.id}`);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "We couldn't save this document type. Check the fields below and try again."
      );
    }
  });

  // Calculate dynamic mock payload and snippets
  const mockPayload = useMemo(() => {
    return generateMockPayload(watchedFields, watchedMetadata);
  }, [watchedFields, watchedMetadata]);

  const firstMetaName = useMemo(() => {
    return watchedMetadata[0]?.name || "";
  }, [watchedMetadata]);

  const snippetCode = useMemo(() => {
    const typeId = id || "YOUR_DOCUMENT_TYPE_ID";
    if (activeLang === "curl") return getCurlCode(typeId, mockPayload, firstMetaName);
    if (activeLang === "js") return getJSCode(typeId, mockPayload, firstMetaName);
    if (activeLang === "py") return getPythonCode(typeId, mockPayload, firstMetaName);
    return getJavaCode(typeId, mockPayload, firstMetaName);
  }, [activeLang, id, mockPayload, firstMetaName]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
      </div>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          {isEdit ? "Edit Document Type" : "New Document Type"}
        </h1>
        {isEdit && (
          <Link
            to={`/document-types/${id}`}
            className="text-sm font-bold text-primary hover:underline flex items-center gap-xs"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span> Cancel
          </Link>
        )}
      </div>

      <div className={isEdit ? "grid grid-cols-[1fr_400px] gap-lg items-start mt-xl" : "mt-xl"}>
        {/* Left Column: Form */}
        <form
          onSubmit={onSubmit}
          className="rounded-lg border border-outline-variant bg-surface-container-lowest p-lg shadow-sm"
        >
          {submitError ? (
            <div className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
              {submitError}
            </div>
          ) : null}

          <div className="space-y-md mb-lg">
            <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
              Name
              <input
                {...register("name", { required: "Name is required." })}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                placeholder="e.g. Invoice, Contract"
              />
            </label>
            {errors.name ? <p className="text-sm text-error">{errors.name.message}</p> : null}

            <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
              Description
              <textarea
                {...register("description")}
                rows={3}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                placeholder="Describe the purpose of this document type..."
              />
            </label>
          </div>

          <fieldset className="mb-lg rounded border border-outline-variant p-md">
            <legend className="px-xs text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Output Formats
            </legend>
            <div className="flex gap-md">
              <label className="flex items-center gap-xs text-sm text-on-surface">
                <input type="checkbox" value="pdf" {...register("allowed_output_formats")} />
                PDF
              </label>
              <label className="flex items-center gap-xs text-sm text-on-surface">
                <input type="checkbox" value="xlsx" {...register("allowed_output_formats")} />
                XLSX
              </label>
            </div>
          </fieldset>

          {/* Visual Schema Tree Builder */}
          <div className="mt-lg">
            <SchemaFieldEditor
              register={register}
              control={control}
              append={append}
              remove={remove}
              update={update}
            />
          </div>

          {/* Visual Metadata Builder */}
          <SchemaMetadataEditor
            register={register}
            control={control}
            append={appendMeta}
            remove={removeMeta}
          />

          <div className="mt-lg flex justify-end">
            <button
              type="submit"
              className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
            >
              {isEdit ? "Save Changes" : "Create Document Type"}
            </button>
          </div>
        </form>

        {/* Right Column: API Integration Panel (Only visible on Edit screen) */}
        {isEdit && (
          <aside className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md sticky top-4 max-h-[750px] overflow-y-auto flex flex-col gap-sm shadow-sm select-none">
            <div className="border-b border-outline-variant pb-xs">
              <h3 className="font-headings text-[14px] font-bold text-on-surface flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">api</span>
                INTEGRATION CODE EXAMPLES
              </h3>
              <p className="text-[11px] text-secondary mt-xs leading-relaxed">
                Connect your codebase to generate and query documents using this schema.
              </p>
            </div>

            {/* Language Selection Badges / Tabs */}
            <div className="flex flex-wrap gap-xs border border-outline-variant p-0.5 rounded-md bg-surface-container-low select-none">
              {(["curl", "js", "py", "java"] as const).map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => setActiveLang(lang)}
                  className={`flex-1 text-center py-1 rounded text-xs font-bold transition-all ${
                    activeLang === lang
                      ? "bg-white text-primary shadow-sm"
                      : "text-secondary hover:text-on-surface"
                  }`}
                >
                  {lang === "curl" ? "cURL" : lang === "js" ? "JS" : lang === "py" ? "Python" : "Java"}
                </button>
              ))}
            </div>

            {/* Code Workspace */}
            <div className="flex-1 min-h-0 relative">
              <pre className="w-full bg-slate-900 text-slate-100 p-sm rounded-lg font-mono text-[11px] leading-relaxed overflow-x-auto select-all max-h-[480px]">
                <code>{snippetCode}</code>
              </pre>
            </div>

            {/* Info badge */}
            <div className="rounded bg-surface-container p-xs border border-outline-variant text-[10px] leading-relaxed text-secondary">
              <div className="font-bold text-on-surface mb-0.5 flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] text-primary">key</span>
                Cookie Session Authentication
              </div>
              These endpoints require cookie authentication. Supply the session cookie <code className="bg-white px-0.5 border rounded font-mono">docmanagement_session</code> in your request headers.
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}

```

## File: frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx
```
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createDocumentDesign } from "../../lib/documentDesigns";
import { getDocumentType, listDocumentTypes, type DocumentTypeDetail, type DocumentTypeListItem, type OutputFormat } from "../../lib/documentTypes";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function DocumentDesignCreatePage() {
  const navigate = useNavigate();
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [xlsxTemplates, setXlsxTemplates] = useState<XlsxTemplateDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("pdf");
  const [xlsxTemplateId, setXlsxTemplateId] = useState("");
  const [mockDataJson, setMockDataJson] = useState("");
  const [mockDataError, setMockDataError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listDocumentTypes()
      .then((rows) => {
        if (cancelled) return;
        setDocumentTypes(rows);
        setDocumentTypeId(rows[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setSubmitError("We couldn't load document types.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!documentTypeId) return;
    let cancelled = false;
    Promise.all([getDocumentType(documentTypeId), listXlsxTemplates(documentTypeId)])
      .then(([documentType, templates]) => {
        if (cancelled) return;
        setSelectedDocumentType(documentType);
        setXlsxTemplates(templates);
        const allowed = documentType?.allowed_output_formats ?? ["pdf"];
        if (!allowed.includes(outputFormat)) {
          setOutputFormat(allowed[0] ?? "pdf");
        }
        setXlsxTemplateId(templates[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setSubmitError("We couldn't load format options.");
      });
    return () => {
      cancelled = true;
    };
  }, [documentTypeId, outputFormat]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!documentTypeId) {
      setSubmitError("Choose a document type.");
      return;
    }
    if (outputFormat === "xlsx" && !xlsxTemplateId) {
      setSubmitError("Choose an XLSX template before creating this design.");
      return;
    }

    let parsedMock: Record<string, unknown> | null = null;
    if (mockDataJson.trim()) {
      try {
        parsedMock = JSON.parse(mockDataJson);
        if (typeof parsedMock !== "object" || parsedMock === null || Array.isArray(parsedMock)) {
          setSubmitError("Mock Data JSON must be a valid JSON object.");
          return;
        }
      } catch (err) {
        setSubmitError(`Mock Data JSON has syntax errors: ${err instanceof Error ? err.message : "Error"}`);
        return;
      }
    }

    try {
      const created = await createDocumentDesign({
        document_type_id: documentTypeId,
        name,
        description: description || null,
        output_format: outputFormat,
        xlsx_template_id: outputFormat === "xlsx" ? xlsxTemplateId : null,
        mock_data: parsedMock,
      });
      navigate(`/document-designs/${created.id}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We couldn't save this design.");
    }
  };

  return (
    <section>
      <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
        New Document Design
      </h1>

      <form
        onSubmit={handleSubmit}
        className="mt-xl rounded border border-outline-variant bg-surface-container-lowest p-lg"
      >
        {submitError ? (
          <p className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
            {submitError}
          </p>
        ) : null}

        <div className="space-y-md">
          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Document Type
            <select
              value={documentTypeId}
              onChange={(event) => setDocumentTypeId(event.target.value)}
              disabled={loading}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {loading ? <option>Loading...</option> : null}
              {!loading && documentTypes.length === 0 ? (
                <option value="">No document types available</option>
              ) : null}
              {documentTypes.map((documentType) => (
                <option key={documentType.id} value={documentType.id}>
                  {documentType.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Output Format
            <select
              value={outputFormat}
              onChange={(event) => setOutputFormat(event.target.value as OutputFormat)}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {(selectedDocumentType?.allowed_output_formats ?? ["pdf"]).map((format) => (
                <option key={format} value={format}>
                  {format.toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          {outputFormat === "xlsx" ? (
            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              XLSX Template
              <select
                value={xlsxTemplateId}
                onChange={(event) => setXlsxTemplateId(event.target.value)}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
              >
                {xlsxTemplates.length === 0 ? <option value="">No XLSX templates available</option> : null}
                {xlsxTemplates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Mock JSON Payload (Optional)
            <textarea
              value={mockDataJson}
              onChange={(event) => {
                setMockDataJson(event.target.value);
                try {
                  if (event.target.value.trim()) {
                    JSON.parse(event.target.value);
                    setMockDataError(null);
                  } else {
                    setMockDataError(null);
                  }
                } catch (err) {
                  setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
                }
              }}
              rows={6}
              placeholder={`{\n  "cliente": {\n    "nombre": "Juan Pérez",\n    "edad": 30\n  }\n}`}
              className={`mt-xs w-full rounded border font-mono text-xs px-sm py-xs bg-white focus:outline-none ${
                mockDataError ? "border-error focus:border-error" : "border-outline focus:border-primary"
              }`}
            />
            {mockDataError && (
              <p className="text-xs text-error mt-xs font-mono">{mockDataError}</p>
            )}
          </label>
        </div>

        <div className="mt-lg flex justify-end">
          <button
            type="submit"
            className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
          >
            Create Design
          </button>
        </div>
      </form>
    </section>
  );
}

```

## File: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx
```
import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import {
  activateDocumentDesign,
  addStaticPdfDesignPage,
  addTemplateDesignPage,
  deleteDesignPage,
  discardDocumentDesignDraft,
  forkDocumentDesignVersion,
  getDocumentDesign,
  listDocumentDesignVersions,
  reorderDesignPages,
  updateDesignPage,
  previewDocumentDesign,
  updateDocumentDesign,
  type DocumentDesignDetail,
  type DocumentDesignListItem,
  type DocumentDesignPage,
} from "../../lib/documentDesigns";
import { getDocumentType, type DocumentTypeField, type DocumentTypeMetadata } from "../../lib/documentTypes";
import { generateMockDataFromFields } from "../../lib/schemaFields";
import AddContentModal from "./components/organisms/AddContentModal";
import DesignPageCard from "./components/molecules/DesignPageCard";
import DesignPageInspector from "./components/organisms/DesignPageInspector";
import { MockDataPanel } from "./components/organisms/MockDataPanel";
import { PreviewFrame } from "./components/organisms/PreviewFrame";

function sortPages(pages: DocumentDesignPage[]) {
  return [...pages].sort((a, b) => a.position - b.position);
}

function pageLabel(page: DocumentDesignPage | null) {
  if (!page) return "No page selected";
  if (page.title) return page.title;
  if (page.block_type === "html_template") return String(page.snapshot.name ?? "HTML template");
  return String(page.snapshot.filename ?? "Static PDF");
}

function pageMetadata(page: DocumentDesignPage | null) {
  if (!page) return "Select a fragment from the stack";
  if (page.block_type === "html_template") {
    const tokens = Array.isArray(page.snapshot.token_names) ? page.snapshot.token_names : [];
    return tokens.length ? `${tokens.length} token${tokens.length === 1 ? "" : "s"}` : "No tokens";
  }

  const pageCount = Number(page.snapshot.page_count ?? 0);
  const pageStart = page.snapshot.page_start;
  const pageEnd = page.snapshot.page_end;
  const range = pageStart && pageEnd ? `, pages ${pageStart}-${pageEnd}` : "";
  return `${pageCount} page${pageCount === 1 ? "" : "s"}${range}`;
}

function statusLabel(status: string) {
  if (status === "active") return "Current";
  return status;
}

function mergeMockData(
  loaded: Record<string, any>,
  fields: DocumentTypeField[],
  metadata: DocumentTypeMetadata[]
): Record<string, any> {
  const freshData = generateMockDataFromFields(fields);
  const freshMetadata: Record<string, any> = {};
  metadata.forEach((m) => {
    if (m.type === "number") freshMetadata[m.name] = 123.45;
    else if (m.type === "boolean") freshMetadata[m.name] = true;
    else if (m.type === "date") freshMetadata[m.name] = new Date().toISOString().split("T")[0];
    else if (m.type === "datetime") freshMetadata[m.name] = new Date().toISOString();
    else freshMetadata[m.name] = "Sample Text";
  });

  const loadedIsStructured = loaded && typeof loaded.data === "object" && loaded.data !== null && !Array.isArray(loaded.data);
  const needsStructure = metadata.length > 0;

  if (needsStructure) {
    const targetData = loadedIsStructured ? { ...loaded.data } : { ...loaded };
    const targetMetadata = loadedIsStructured && typeof loaded.metadata === "object" && loaded.metadata !== null ? { ...loaded.metadata } : {};

    // Remove metadata keys from targetData if they accidentally leaked there
    metadata.forEach((m) => {
      delete targetData[m.name];
    });

    // Fill missing data keys
    Object.keys(freshData).forEach((key) => {
      if (targetData[key] === undefined) {
        targetData[key] = freshData[key];
      }
    });

    // Fill missing metadata keys
    Object.keys(freshMetadata).forEach((key) => {
      if (targetMetadata[key] === undefined) {
        targetMetadata[key] = freshMetadata[key];
      }
    });

    return { data: targetData, metadata: targetMetadata };
  } else {
    const targetData = loadedIsStructured ? { ...loaded.data } : { ...loaded };
    Object.keys(freshData).forEach((key) => {
      if (targetData[key] === undefined) {
        targetData[key] = freshData[key];
      }
    });
    return targetData;
  }
}

export default function DocumentDesignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [design, setDesign] = useState<DocumentDesignDetail | null | undefined>(undefined);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [modalMode, setModalMode] = useState<"template" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<DocumentDesignPage | null>(null);
  const [versions, setVersions] = useState<DocumentDesignListItem[]>([]);
  const [showDiscardModal, setShowDiscardModal] = useState(false);
  const [discarding, setDiscarding] = useState(false);

  const [docTypeFields, setDocTypeFields] = useState<DocumentTypeField[]>([]);
  const [metadataDefs, setMetadataDefs] = useState<DocumentTypeMetadata[]>([]);
  const [mockJsonText, setMockJsonText] = useState<string>("{}");
  const [parsedPayload, setParsedPayload] = useState<Record<string, unknown>>({});
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [isSavingMock, setIsSavingMock] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);
  const [previewMode, setPreviewMode] = useState<"fragment" | "pdf">("fragment");
  const [activeRightTab, setActiveRightTab] = useState<"inspector" | "mockData">("inspector");

  const [leftWidth, setLeftWidth] = useState(380);
  const [rightWidth, setRightWidth] = useState(330);
  const [isResizing, setIsResizing] = useState(false);

  const handleLeftMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = leftWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.max(260, Math.min(600, startWidth + deltaX));
      setLeftWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleRightMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = rightWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = startX - moveEvent.clientX;
      const newWidth = Math.max(260, Math.min(600, startWidth + deltaX));
      setRightWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleSetPreviewMode = (mode: "fragment" | "pdf") => {
    setPreviewMode(mode);
    setActiveRightTab(mode === "pdf" ? "mockData" : "inspector");
  };

  const handleSetActiveRightTab = (tab: "inspector" | "mockData") => {
    setActiveRightTab(tab);
    setPreviewMode(tab === "mockData" ? "pdf" : "fragment");
  };

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getDocumentDesign(id)
      .then((data) => {
        if (cancelled) return;
        setDesign(data);
        setSelectedPageId(data?.pages[0]?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load this design.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!design?.id) return;
    listDocumentDesignVersions(design.id)
      .then(setVersions)
      .catch(() => {});
  }, [design?.id]);

  useEffect(() => {
    if (location.state?.justForked && location.state?.sourceVersion !== undefined) {
      setNotice(
        `New draft created from version ${location.state.sourceVersion}. Changes here won't affect the current version until you activate this one.`,
      );
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    if (!design?.document_type_id) return;
    let cancelled = false;
    getDocumentType(design.document_type_id)
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setDocTypeFields(data.fields);
          setMetadataDefs(data.metadata_definitions || []);
          let loadedMock: Record<string, unknown> | null = null;
          if (design?.id) {
            try {
              const saved = localStorage.getItem(`mock_payload_${design.id}`);
              if (saved) {
                const parsed = JSON.parse(saved);
                if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
                  loadedMock = parsed as Record<string, unknown>;
                }
              } else if (design.mock_data) {
                loadedMock = design.mock_data;
              }
            } catch (err) {
              console.error("Failed to parse saved mock payload", err);
            }
          }

          let initialMock: Record<string, any>;
          if (loadedMock) {
            initialMock = mergeMockData(loadedMock, data.fields, data.metadata_definitions || []);
            // Save the merged mock back to localStorage to keep it up to date
            localStorage.setItem(`mock_payload_${design.id}`, JSON.stringify(initialMock));
          } else {
            const mockData = generateMockDataFromFields(data.fields);
            if (data.metadata_definitions && data.metadata_definitions.length > 0) {
              const mockMetadata: Record<string, any> = {};
              data.metadata_definitions.forEach((meta) => {
                if (meta.type === "number") mockMetadata[meta.name] = 123.45;
                else if (meta.type === "boolean") mockMetadata[meta.name] = true;
                else if (meta.type === "date") mockMetadata[meta.name] = new Date().toISOString().split("T")[0];
                else if (meta.type === "datetime") mockMetadata[meta.name] = new Date().toISOString();
                else mockMetadata[meta.name] = "Sample Text";
              });
              initialMock = { data: mockData, metadata: mockMetadata };
            } else {
              initialMock = mockData;
            }
          }

          const text = JSON.stringify(initialMock, null, 2);
          setMockJsonText(text);
          setParsedPayload(initialMock);
          setJsonError(null);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setPreviewError("Could not load schema fields for preview setup.");
      });
    return () => {
      cancelled = true;
    };
  }, [design?.document_type_id, design?.id]);

  const handleResetMockData = () => {
    const mockData = generateMockDataFromFields(docTypeFields);
    let initialMock: Record<string, any> = mockData;
    if (metadataDefs && metadataDefs.length > 0) {
      const mockMetadata: Record<string, any> = {};
      metadataDefs.forEach((meta) => {
        if (meta.type === "number") mockMetadata[meta.name] = 123.45;
        else if (meta.type === "boolean") mockMetadata[meta.name] = true;
        else if (meta.type === "date") mockMetadata[meta.name] = new Date().toISOString().split("T")[0];
        else if (meta.type === "datetime") mockMetadata[meta.name] = new Date().toISOString();
        else mockMetadata[meta.name] = "Sample Text";
      });
      initialMock = { data: mockData, metadata: mockMetadata };
    }

    const text = JSON.stringify(initialMock, null, 2);
    setMockJsonText(text);
    setParsedPayload(initialMock);
    setJsonError(null);
    if (design?.id) {
      localStorage.removeItem(`mock_payload_${design.id}`);
    }
  };

  const handleMockJsonChange = (text: string) => {
    setMockJsonText(text);
    try {
      if (!text.trim()) {
        setJsonError("JSON payload cannot be empty");
        return;
      }
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        setJsonError("JSON root must be an object");
      } else {
        setParsedPayload(parsed);
        setJsonError(null);
        if (design?.id) {
          localStorage.setItem(`mock_payload_${design.id}`, JSON.stringify(parsed));
        }
      }
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "Invalid JSON syntax");
    }
  };

  const handleTriggerPdfPreview = async () => {
    if (!design) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const blob = await previewDocumentDesign(design.id, parsedPayload);
      setPreviewBlob(blob);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to generate PDF preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveMockData = async () => {
    if (!design) return;
    setIsSavingMock(true);
    setPreviewError(null);
    try {
      const updated = await updateDocumentDesign(design.id, {
        name: design.name,
        description: design.description,
        output_format: design.output_format,
        xlsx_template_id: design.xlsx_template_id,
        mock_data: parsedPayload,
      });
      setDesign(updated);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to persist mock data to server.");
    } finally {
      setIsSavingMock(false);
    }
  };

  const pages = useMemo(() => sortPages(design?.pages ?? []), [design?.pages]);
  const selectedPage = pages.find((page) => page.id === selectedPageId) ?? null;
  const existingPdfIds = useMemo(
    () => pages.filter((page) => page.block_type === "static_pdf").map((page) => page.content_id),
    [pages],
  );
  const readOnly = design ? design.status !== "draft" : true;
  const activeVersion = useMemo(() => versions.find((v) => v.status === "active"), [versions]);

  const setPages = (nextPages: DocumentDesignPage[]) => {
    setDesign((current) =>
      current ? { ...current, pages: nextPages.map((page, index) => ({ ...page, position: index })) } : current,
    );
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    if (!design || event.over === null || event.active.id === event.over.id) return;

    const oldIndex = pages.findIndex((page) => page.id === event.active.id);
    const newIndex = pages.findIndex((page) => page.id === event.over?.id);
    if (oldIndex < 0 || newIndex < 0) return;

    const previousPages = pages;
    const nextPages = arrayMove(pages, oldIndex, newIndex).map((page, index) => ({
      ...page,
      position: index,
    }));
    setPages(nextPages);
    setError(null);
    try {
      const updated = await reorderDesignPages(design.id, nextPages.map((page) => page.id));
      setDesign(updated);
    } catch (err) {
      setPages(previousPages);
      setError(err instanceof Error ? err.message : "We couldn't save the page order.");
    }
  };

  const handleAddTemplate = async (templateId: string) => {
    if (!design) return;
    const page = await addTemplateDesignPage(design.id, { template_id: templateId });
    setDesign({ ...design, pages: [...pages, page] });
    setSelectedPageId(page.id);
    setNotice("Template page added.");
  };

  const handleAddPdf = async (assetId: string) => {
    if (!design) return;
    const page = await addStaticPdfDesignPage(design.id, { static_pdf_asset_id: assetId });
    setDesign({ ...design, pages: [...pages, page] });
    setSelectedPageId(page.id);
    setNotice("PDF page added.");
  };

  const handleSavePage = async (
    pageId: string,
    values: { title: string | null; notes: string | null; config: Record<string, unknown> },
  ) => {
    if (!design) return;
    const updatedPage = await updateDesignPage(design.id, pageId, values);
    setDesign({
      ...design,
      pages: pages.map((page) => (page.id === pageId ? updatedPage : page)),
    });
    setNotice("Page saved.");
  };

  const handleRemove = (page: DocumentDesignPage) => {
    setPendingRemove(page);
    setPages(pages.filter((candidate) => candidate.id !== page.id));
    if (selectedPageId === page.id) setSelectedPageId(null);
    setNotice("Page removed locally. Undo or confirm removal.");
  };

  const undoRemove = () => {
    if (!pendingRemove) return;
    setPages([...pages, pendingRemove].sort((a, b) => a.position - b.position));
    setSelectedPageId(pendingRemove.id);
    setPendingRemove(null);
    setNotice("Page restored.");
  };

  const confirmRemove = async () => {
    if (!design || !pendingRemove) return;
    try {
      await deleteDesignPage(design.id, pendingRemove.id);
      setPendingRemove(null);
      setNotice("Page removal saved.");
    } catch (err) {
      setPages([...pages, pendingRemove].sort((a, b) => a.position - b.position));
      setError(err instanceof Error ? err.message : "We couldn't remove this page.");
      setPendingRemove(null);
    }
  };

  const handleActivate = async () => {
    if (!design) return;
    setError(null);
    try {
      const updated = await activateDocumentDesign(design.id);
      setDesign(updated);
      if (updated.version_number && updated.version_number > 1) {
        setNotice(
          `Version ${updated.version_number} is now current. Version ${updated.version_number - 1} has been preserved in version history.`,
        );
      } else {
        setNotice("Design activated.");
      }
      const hist = await listDocumentDesignVersions(updated.id);
      setVersions(hist);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't activate this design.");
    }
  };

  const handleEditDesign = async () => {
    if (!design) return;
    setError(null);
    try {
      const draft = await forkDocumentDesignVersion(design.id);
      navigate(`/document-designs/${draft.id}`, {
        state: { justForked: true, sourceVersion: design.version_number },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't create a new version. Try again.");
    }
  };

  const handleDiscardDraft = async () => {
    if (!design) return;
    setDiscarding(true);
    setError(null);
    try {
      await discardDocumentDesignDraft(design.id);
      setShowDiscardModal(false);
      const groupId = design.version_group_id || design.id;
      navigate(`/document-designs/${groupId}/versions`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't discard this draft. Try again.");
    } finally {
      setDiscarding(false);
    }
  };

  if (error && design === undefined) return <p className="text-sm text-error">{error}</p>;
  if (design === undefined) return null;

  if (design === null) {
    return (
      <div className="text-center">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
          Document design not found.
        </h1>
        <Link
          to="/document-designs"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Designs
        </Link>
      </div>
    );
  }

  return (
    <section className="-m-lg flex min-h-[calc(100vh-4rem)] overflow-hidden bg-surface-container">
      <aside
        className="flex min-h-0 flex-col bg-surface-bright shrink-0"
        style={{ width: leftWidth }}
      >
        <div className="border-b border-outline-variant p-lg">
          <div className="flex items-start justify-between gap-md">
            <div className="min-w-0">
              <h1 className="truncate font-headings text-headline-lg font-bold text-on-surface">
                {design.name}
              </h1>
              <p className="mt-xs line-clamp-2 text-body-sm text-on-surface-variant">
                {design.description || "No description"}
              </p>
            </div>
            <span className="shrink-0 rounded bg-surface-container-high px-sm py-xs text-label-caps font-bold uppercase text-primary">
              {statusLabel(design.status)}
            </span>
          </div>

          <div className="mt-lg grid grid-cols-2 gap-md text-body-sm">
            <div>
              <p className="font-label-caps text-on-surface-variant">Document Type</p>
              <p className="mt-base font-bold text-on-surface">{design.document_type_name}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Created By</p>
              <p className="mt-base truncate text-on-surface">{design.created_by_email}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Created At</p>
              <p className="mt-base text-on-surface">{new Date(design.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Fragments</p>
              <p className="mt-base text-on-surface">{pages.length}</p>
            </div>
          </div>

          <div className="mt-lg flex flex-wrap gap-sm">
            {design.status === "draft" ? (
              <>
                <button
                  type="button"
                  className="rounded border border-error px-md py-xs text-body-sm font-bold text-error hover:bg-error/10"
                  onClick={() => setShowDiscardModal(true)}
                >
                  Discard
                </button>
                <button
                  type="button"
                  className="rounded bg-primary px-md py-xs text-body-sm font-bold text-white hover:bg-primary/90"
                  onClick={handleActivate}
                >
                  Activate
                </button>
              </>
            ) : null}
            {design.status === "active" ? (
              <button
                type="button"
                className="rounded bg-primary px-md py-xs text-body-sm font-bold text-white hover:bg-primary/90"
                onClick={handleEditDesign}
              >
                Edit Design
              </button>
            ) : null}
            <Link
              to={`/document-designs/${design.id}/versions`}
              className="rounded border border-primary px-md py-xs text-body-sm font-bold text-primary hover:bg-primary/10"
            >
              Version History
            </Link>
          </div>

          {design.status === "superseded" && activeVersion ? (
            <div className="mt-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-body-sm font-bold text-on-surface">
              Past version.{" "}
              <Link to={`/document-designs/${activeVersion.id}`} className="text-primary hover:underline">
                View current version
              </Link>
            </div>
          ) : null}

          {error ? <p className="mt-md rounded border border-error/30 p-sm text-body-sm text-error">{error}</p> : null}
          {notice ? (
            <div className="mt-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-body-sm text-on-surface">
              <div className="flex flex-wrap items-center justify-between gap-sm">
                <span>{notice}</span>
                {pendingRemove ? (
                  <span className="flex gap-sm">
                    <button type="button" className="font-bold text-primary" onClick={undoRemove}>
                      Undo
                    </button>
                    <button type="button" className="font-bold text-error" onClick={confirmRemove}>
                      Confirm
                    </button>
                  </span>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>

        <div className="flex min-h-0 flex-1 flex-col p-md">
          <div className="mb-md flex items-center justify-between gap-sm">
            <div>
              <h2 className="font-headings text-headline-md text-on-surface">Fragments</h2>
              <p className="text-body-sm text-on-surface-variant">Ordered document body</p>
            </div>
            {!readOnly ? (
              <div className="flex gap-xs">
                <button
                  type="button"
                  className="rounded bg-primary px-sm py-xs text-label-caps font-bold text-white hover:bg-primary/90"
                  onClick={() => setModalMode("template")}
                >
                  Template
                </button>
                <button
                  type="button"
                  className="rounded border border-primary px-sm py-xs text-label-caps font-bold text-primary hover:bg-primary/10"
                  onClick={() => setModalMode("pdf")}
                >
                  PDF
                </button>
              </div>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto pr-xs">
            {pages.length === 0 ? (
              <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
                <p className="font-headings text-headline-md font-bold text-on-surface">Empty fragment stack</p>
                <p className="mt-xs text-body-sm text-on-surface-variant">
                  Add a template or static PDF page to start composing this design.
                </p>
              </div>
            ) : readOnly ? (
              <div className="space-y-sm">
                {pages.map((page) => (
                  <DesignPageCard
                    key={page.id}
                    page={page}
                    selected={page.id === selectedPageId}
                    onSelect={setSelectedPageId}
                    onRemove={handleRemove}
                    readOnly={true}
                  />
                ))}
              </div>
            ) : (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={pages.map((page) => page.id)} strategy={verticalListSortingStrategy}>
                  <div className="space-y-sm">
                    {pages.map((page) => (
                      <DesignPageCard
                        key={page.id}
                        page={page}
                        selected={page.id === selectedPageId}
                        onSelect={setSelectedPageId}
                        onRemove={handleRemove}
                        readOnly={false}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            )}
          </div>
        </div>
      </aside>

      {/* Left Resize Handle */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-primary/45 active:bg-primary transition-colors h-full shrink-0 z-40 border-r border-outline-variant hover:border-transparent"
        onMouseDown={handleLeftMouseDown}
      />

      <main className="flex min-h-[640px] flex-1 flex-col overflow-hidden bg-surface-container">
        <div className="flex items-center justify-between gap-md border-b border-outline-variant bg-surface px-lg py-md">
          <div className="min-w-0">
            <p className="font-label-caps text-on-surface-variant">
              {previewMode === "pdf"
                ? "Generated PDF"
                : selectedPage
                ? `Page ${selectedPage.position + 1}`
                : "Preview"}
            </p>
            <h2 className="truncate font-headings text-headline-md text-on-surface">
              {previewMode === "pdf" ? "Document Previsualization" : pageLabel(selectedPage)}
            </h2>
          </div>
          <div className="flex items-center gap-md">
            <div className="flex border border-outline-variant rounded bg-surface-container-low p-[2px]">
              <button
                type="button"
                className={`rounded px-sm py-xs text-xs font-bold ${
                  previewMode === "fragment"
                    ? "bg-surface text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
                onClick={() => handleSetPreviewMode("fragment")}
              >
                Fragment Preview
              </button>
              <button
                type="button"
                className={`rounded px-sm py-xs text-xs font-bold ${
                  previewMode === "pdf"
                    ? "bg-surface text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
                onClick={() => handleSetPreviewMode("pdf")}
              >
                PDF Preview
              </button>
            </div>
            {previewMode === "fragment" && (
              <span className="rounded border border-outline-variant bg-surface-container-low px-sm py-xs text-label-caps text-on-surface-variant">
                {pageMetadata(selectedPage)}
              </span>
            )}
          </div>
        </div>

        <div className={`page-canvas-bg flex min-h-0 flex-1 items-start justify-center overflow-auto p-xl ${isResizing ? 'pointer-events-none' : ''}`}>
          {previewMode === "pdf" ? (
            <div className="w-full max-w-[800px] bg-surface-container-lowest p-md border border-outline-variant rounded-lg shadow-lg">
              <PreviewFrame blob={previewBlob} loading={previewLoading} error={previewError} />
            </div>
          ) : (
            <div className="flex min-h-[760px] w-full max-w-[595px] flex-col border border-outline-variant bg-white p-xl shadow-lg">
              {selectedPage ? (
                selectedPage.block_type === "html_template" && typeof selectedPage.snapshot.html === "string" ? (
                  <iframe
                    title={`Preview ${pageLabel(selectedPage)}`}
                    className="h-full min-h-[680px] w-full flex-1 border-0 bg-white"
                    srcDoc={`
                      <style>
                        body {
                          font-family: Helvetica, Arial, sans-serif;
                          font-size: 10pt;
                          line-height: 1.4;
                        }
                        ${selectedPage.snapshot.css || ""}
                      </style>
                      ${selectedPage.snapshot.html || ""}
                    `}
                  />
                ) : (
                  <div className="flex flex-1 flex-col items-center justify-center gap-md text-center">
                    <span className="material-symbols-outlined text-[56px] text-primary">picture_as_pdf</span>
                    <div>
                      <h3 className="font-headings text-headline-md text-on-surface">{pageLabel(selectedPage)}</h3>
                      <p className="mt-xs text-body-sm text-on-surface-variant">{pageMetadata(selectedPage)}</p>
                    </div>
                  </div>
                )
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center gap-md text-center">
                  <span className="material-symbols-outlined text-[56px] text-on-surface-variant">
                    dashboard_customize
                  </span>
                  <div>
                    <h3 className="font-headings text-headline-md text-on-surface">Select a fragment</h3>
                    <p className="mt-xs text-body-sm text-on-surface-variant">
                      The selected page preview appears here.
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-auto flex justify-between border-t border-outline-variant pt-md text-[10px] text-on-surface-variant">
                <span>Precision Archival</span>
                <span>{selectedPage ? `Page ${selectedPage.position + 1} of ${pages.length}` : `${pages.length} pages`}</span>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Right Resize Handle */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-primary/45 active:bg-primary transition-colors h-full shrink-0 z-40 border-l border-outline-variant hover:border-transparent"
        onMouseDown={handleRightMouseDown}
      />

      <aside
        className="min-h-0 overflow-y-auto bg-surface p-md flex flex-col gap-md shrink-0"
        style={{ width: rightWidth }}
      >
        <div className="flex border border-outline-variant rounded bg-surface-container-low p-[2px] shrink-0">
          <button
            type="button"
            className={`flex-1 rounded py-xs text-xs font-bold text-center ${
              activeRightTab === "inspector"
                ? "bg-surface text-primary shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => handleSetActiveRightTab("inspector")}
          >
            Page Inspector
          </button>
          <button
            type="button"
            className={`flex-1 rounded py-xs text-xs font-bold text-center ${
              activeRightTab === "mockData"
                ? "bg-surface text-primary shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => handleSetActiveRightTab("mockData")}
          >
            Mock Data Preview
          </button>
        </div>

        <div className="flex-1 min-h-0">
          {activeRightTab === "inspector" ? (
            <DesignPageInspector page={selectedPage} onSave={handleSavePage} readOnly={readOnly} />
          ) : (
            <>
              {previewError ? (
                <div className="mb-sm text-xs text-error bg-error/5 border border-error/20 p-xs rounded font-mono">
                  {previewError}
                </div>
              ) : null}
              <MockDataPanel
                value={mockJsonText}
                onChange={handleMockJsonChange}
                onReset={handleResetMockData}
                onPreview={handleTriggerPdfPreview}
                onSave={handleSaveMockData}
                isValidJson={!jsonError}
                parseError={jsonError}
                loadingPreview={previewLoading}
                isSavingMock={isSavingMock}
              />
            </>
          )}
        </div>
      </aside>

      {modalMode ? (
        <AddContentModal
          mode={modalMode}
          documentTypeId={design.document_type_id}
          existingPdfIds={existingPdfIds}
          onClose={() => setModalMode(null)}
          onAddTemplate={handleAddTemplate}
          onAddPdf={handleAddPdf}
        />
      ) : null}

      {showDiscardModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-md">
          <div className="w-full max-w-xl rounded border border-outline-variant bg-surface-container-lowest p-lg shadow-xl">
            <div className="flex items-center justify-between gap-md">
              <h2 className="font-headings text-[14px] font-bold text-on-surface">
                Discard this draft?
              </h2>
              <button
                type="button"
                className="text-sm font-bold text-primary"
                onClick={() => setShowDiscardModal(false)}
                disabled={discarding}
              >
                Close
              </button>
            </div>

            <p className="mt-md text-sm text-on-surface">
              Changes since version {design.version_number ? design.version_number - 1 : 1} will be lost. Version{" "}
              {design.version_number ? design.version_number - 1 : 1} itself stays intact and remains the current
              version.
            </p>

            {error ? <p className="mt-md text-sm text-error">{error}</p> : null}

            <div className="mt-lg flex justify-end gap-sm">
              <button
                type="button"
                className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface"
                onClick={() => setShowDiscardModal(false)}
                disabled={discarding}
              >
                Keep Editing
              </button>
              <button
                type="button"
                disabled={discarding}
                className="rounded bg-error px-md py-xs text-sm font-bold text-white hover:bg-error/90 disabled:opacity-50"
                onClick={handleDiscardDraft}
              >
                {discarding ? "Discarding..." : "Discard Draft"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

```

## File: frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx
```
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import IssuanceProperties from "../../components/molecules/IssuanceProperties";
import { API_BASE_URL, apiFetch } from "../../lib/api";
import {
  getDocumentIssuance,
  getDocumentTracelogs,
  shareDocumentIssuance,
  type DocumentIssuanceDetail,
  type DocumentTracelog,
} from "../../lib/documentIssuances";

const EVENT_LABELS: Record<string, string> = {
  generation: "Generated",
  download: "Downloaded",
  share: "Shared",
};

function clipboardUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  if (API_BASE_URL) return `${API_BASE_URL}${path}`;
  return `${window.location.origin}${path}`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function metadataValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export default function DocumentIssuanceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<DocumentIssuanceDetail | null | undefined>(undefined);
  const [tracelogs, setTracelogs] = useState<DocumentTracelog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timeoutId: any = null;
    let pollCount = 0;

    const fetchStatus = () => {
      Promise.all([getDocumentIssuance(id), getDocumentTracelogs(id)])
        .then(([issuance, logs]) => {
          if (cancelled) return;
          setDetail(issuance);
          setTracelogs(logs);

          if (issuance && (issuance.status === "queued" || issuance.status === "processing")) {
            pollCount++;
            const delay = pollCount <= 30 ? 2000 : 5000;
            timeoutId = setTimeout(fetchStatus, delay);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : "We couldn't load this document issuance.");
          }
        });
    };

    fetchStatus();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [id]);

  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!detail || detail.status !== "success" || detail.output_format !== "pdf") {
      setBlobUrl(null);
      setPreviewError(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setBlobUrl(null);
    setPreviewError(null);
    apiFetch(detail.preview_url)
      .then((res) => {
        if (!res.ok) throw new Error(`Preview failed (${res.status})`);
        return res.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) {
          setPreviewError(err instanceof Error ? err.message : "Failed to load PDF preview.");
        }
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [detail]);

  const handleDownload = async () => {
    if (!detail) return;
    setDownloading(true);
    setError(null);
    try {
      const res = await apiFetch(detail.download_url);
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = detail.filename ?? `${detail.design_name}.${detail.output_format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      const logs = await getDocumentTracelogs(detail.id);
      setTracelogs(logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't download this document.");
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = async () => {
    if (!detail) return;
    setSharing(true);
    setError(null);
    setNotice(null);
    try {
      const response = await shareDocumentIssuance(detail.id);
      const url = clipboardUrl(response.public_url);
      await navigator.clipboard.writeText(url);
      setNotice("Public share URL copied.");
      const logs = await getDocumentTracelogs(detail.id);
      setTracelogs(logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't create or copy the share URL.");
    } finally {
      setSharing(false);
    }
  };

  if (error && detail === undefined) return <p className="text-sm text-error">{error}</p>;
  if (detail === undefined) return null;

  if (detail === null) {
    return (
      <div className="text-center">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
          Document issuance not found.
        </h1>
        <Link
          to="/document-issuances"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Documents Library
        </Link>
      </div>
    );
  }

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Operations" }, { label: "Documents Library", to: "/document-issuances" }, { label: detail.design_name }]}
        title={detail.design_name}
        actions={
          <>
            <button
              type="button"
              className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50"
              onClick={handleDownload}
              disabled={downloading || detail.status !== "success"}
            >
              {downloading ? "Downloading..." : `Download ${detail.output_format.toUpperCase()}`}
            </button>
            <button
              type="button"
              className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10 disabled:opacity-50"
              onClick={handleShare}
              disabled={sharing || detail.status !== "success"}
            >
              {sharing ? "Sharing..." : "Share"}
            </button>
          </>
        }
      />

      {error ? <p className="mb-md rounded border border-error/30 p-sm text-sm text-error">{error}</p> : null}
      {notice ? (
        <p className="mb-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-sm text-on-surface">
          {notice}
        </p>
      ) : null}

      <div className="grid gap-lg lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-lg">
          <div>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">
              {detail.output_format === "pdf" ? "PDF Preview" : "Generated Workbook"}
            </h2>
            {detail.status === "failure" ? (
              <div className="rounded-lg border border-error bg-surface-container-low p-lg text-center">
                <span className="material-symbols-outlined text-[48px] text-error mb-2">error</span>
                <h3 className="font-headings text-[18px] font-bold text-on-surface mb-2">Generation Failed</h3>
                <p className="text-sm text-error max-w-lg mx-auto font-mono bg-surface-container-lowest p-md rounded border border-outline-variant">
                  {detail.error_message || "An unknown error occurred during document generation."}
                </p>
              </div>
            ) : previewError ? (
              <p className="rounded border border-error/30 p-md text-sm text-error">{previewError}</p>
            ) : detail.output_format !== "pdf" && detail.status === "success" ? (
              <div className="flex h-[320px] w-full flex-col items-center justify-center gap-md rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined text-[40px] text-primary">table</span>
                <p className="text-sm font-bold text-secondary">Preview is available after download.</p>
              </div>
            ) : blobUrl ? (
              <iframe
                title={`PDF preview for ${detail.design_name}`}
                src={blobUrl}
                className="h-[720px] w-full rounded border border-outline-variant bg-surface-container-lowest"
              />
            ) : detail.status === "queued" || detail.status === "processing" ? (
              <div className="flex h-[720px] w-full flex-col items-center justify-center gap-md rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined animate-spin text-[32px] text-primary">progress_activity</span>
                <p className="text-sm font-bold text-secondary">
                  {detail.status === "queued" ? "Waiting in queue..." : `Generating ${detail.output_format.toUpperCase()} document...`}
                </p>
              </div>
            ) : (
              <div className="flex h-[720px] w-full items-center justify-center rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-lg">
          <IssuanceProperties detail={detail} />
          {detail.metadata_values && Object.keys(detail.metadata_values).length > 0 && (
            <section>
              <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Document Metadata</h2>
              <div className="rounded border border-outline-variant bg-surface-container-lowest p-md text-sm text-on-surface">
                <dl className="divide-y divide-outline-variant/40">
                  {Object.entries(detail.metadata_values).map(([key, value]) => (
                    <div key={key} className="py-xs flex justify-between gap-md">
                      <dt className="font-mono text-xs text-on-surface-variant font-semibold">{key}</dt>
                      <dd className="text-on-surface text-right font-semibold">
                        {typeof value === "boolean" ? (value ? "True" : "False") : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Input Data</h2>
            <pre className="max-h-80 overflow-auto rounded border border-outline-variant bg-surface-container-lowest p-md text-xs leading-5 text-on-surface">
              {JSON.stringify(detail.input_data, null, 2)}
            </pre>
          </section>

          <section>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Audit Timeline</h2>
            {tracelogs.length === 0 ? (
              <p className="rounded border border-outline-variant bg-surface-container-lowest p-md text-sm text-on-surface-variant">
                No tracelog events recorded.
              </p>
            ) : (
              <ol className="space-y-sm">
                {tracelogs.map((log) => (
                  <li key={log.id} className="border-l-2 border-outline-variant pl-md">
                    <div className="flex items-start justify-between gap-sm">
                      <div>
                        <div className="font-bold text-on-surface">
                          {EVENT_LABELS[log.event_type] ?? log.event_type}
                        </div>
                        <div className="text-xs text-on-surface-variant">{formatDate(log.created_at)}</div>
                      </div>
                      <span className="rounded bg-surface-container px-sm py-xs text-[11px] font-bold uppercase text-secondary">
                        {log.user_id ? "User" : "Anonymous"}
                      </span>
                    </div>
                    {log.user_id ? (
                      <div className="mt-xs break-all font-mono text-xs text-on-surface-variant">
                        {log.user_id}
                      </div>
                    ) : null}
                    {Object.keys(log.metadata).length > 0 ? (
                      <dl className="mt-sm space-y-xs text-xs">
                        {Object.entries(log.metadata).map(([key, value]) => (
                          <div key={key} className="grid grid-cols-[88px_minmax(0,1fr)] gap-sm">
                            <dt className="text-on-surface-variant">{key}</dt>
                            <dd className="break-words text-on-surface">{metadataValue(value)}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}

```

## File: .superpowers/sdd/xlsx-template-generation-task-8-report.md
```
# XLSX Template Generation Task 8 Report

## Status

Completed final verification pass with environment-limited backend tests.

## Verification

- `rtk proxy python -m compileall -q backend/app backend/tests`: passed.
- `rtk npm --prefix frontend run build`: passed. Vite emitted the existing large chunk warning.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_xlsx_format_contract.py tests/test_xlsx_analysis.py tests/test_xlsx_templates_api.py tests/test_xlsx_renderer.py tests/test_xlsx_preview.py tests/test_xlsx_designs.py tests/test_xlsx_issuance_generation.py -q }'`: blocked by `C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied`.
- Retried with workspace-local `UV_CACHE_DIR=backend/.uv-cache`: blocked while building `litellm==1.92.0` because `maturin==1.9.4` could not be fetched from PyPI due `invalid peer certificate: UnknownIssuer`.
- Regression pytest command with workspace-local uv cache was blocked by the same `litellm`/`maturin` certificate issue.

## Manual Smoke

Not run. Starting full Docker services and manually opening generated workbooks requires external service/runtime state beyond this turn. The backend/frontend code paths were compile/build checked and reviewed task-by-task.

## Worktree

`rtk git status --short` shows many unrelated pre-existing dirty/deleted/untracked files. I did not revert them. XLSX feature files are mixed with prior work because `.git/index.lock` creation has been blocked in this session.

```
