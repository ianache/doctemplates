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
