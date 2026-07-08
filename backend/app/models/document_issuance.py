import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class DocumentIssuance(Base):
    __tablename__ = "document_issuances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    design_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_designs.id", ondelete="RESTRICT")
    )
    file_path: Mapped[str]
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    input_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    design_version: Mapped["DocumentDesign"] = relationship()
    user: Mapped["User"] = relationship()
