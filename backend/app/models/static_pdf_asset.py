import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class StaticPdfAsset(Base):
    __tablename__ = "static_pdf_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str]
    stored_filename: Mapped[str] = mapped_column(index=True)
    storage_key: Mapped[str]

    @property
    def stored_path(self) -> str:
        from pathlib import Path
        if Path(self.storage_key).is_absolute():
            return self.storage_key
        from app.config import settings
        import os
        return os.path.join(settings.content_storage_root, self.storage_key)

    @stored_path.setter
    def stored_path(self, value: str) -> None:
        self.storage_key = value
    page_count: Mapped[int]
    page_start: Mapped[int | None]
    page_end: Mapped[int | None]
    file_size: Mapped[int]
    document_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_types.id"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document_type: Mapped["DocumentType | None"] = relationship()
    created_by: Mapped["User"] = relationship()
