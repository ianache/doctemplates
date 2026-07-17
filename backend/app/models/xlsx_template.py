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
