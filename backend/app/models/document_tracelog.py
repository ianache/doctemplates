import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


TRACELOG_EVENT_TYPES = ("generation", "download", "share")


class DocumentTracelog(Base):
    __tablename__ = "document_tracelogs"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN {TRACELOG_EVENT_TYPES!r}",
            name="ck_document_tracelog_event_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    issuance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_issuances.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str]
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    issuance: Mapped["DocumentIssuance"] = relationship(back_populates="tracelogs")
    user: Mapped["User | None"] = relationship()
