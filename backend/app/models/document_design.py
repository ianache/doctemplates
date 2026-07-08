import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


DESIGN_STATUSES = ("draft", "active")
DESIGN_BLOCK_TYPES = ("html_template", "static_pdf")


class DocumentDesign(Base):
    __tablename__ = "document_designs"
    __table_args__ = (
        CheckConstraint(f"status IN {DESIGN_STATUSES!r}", name="ck_document_design_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_types.id"))
    name: Mapped[str]
    description: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="draft")
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document_type: Mapped["DocumentType"] = relationship()
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
