import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class HtmlTemplate(Base):
    __tablename__ = "html_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(index=True)
    html: Mapped[str]
    css: Mapped[str | None] = mapped_column(nullable=True, default="")
    token_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    mock_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document_type: Mapped["DocumentType"] = relationship()
    created_by: Mapped["User"] = relationship()
