import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


ISSUANCE_STATUSES = ("queued", "processing", "success", "failure")


class DocumentIssuance(Base):
    __tablename__ = "document_issuances"
    __table_args__ = (
        CheckConstraint(f"status IN {ISSUANCE_STATUSES!r}", name="ck_document_issuance_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    design_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_designs.id", ondelete="RESTRICT")
    )
    storage_key: Mapped[str | None] = mapped_column(nullable=True, default=None)

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
