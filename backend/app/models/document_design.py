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
