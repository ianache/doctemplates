import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

AI_PROPOSAL_STATUSES = ("valid", "invalid", "failed")


class HtmlTemplateAiProposal(Base):
    __tablename__ = "html_template_ai_proposals"
    __table_args__ = (
        CheckConstraint(
            f"status IN {AI_PROPOSAL_STATUSES!r}",
            name="ck_html_template_ai_proposal_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("html_templates.id", ondelete="CASCADE"),
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    instruction: Mapped[str] = mapped_column(Text)
    input_html: Mapped[str] = mapped_column(Text)
    input_css: Mapped[str] = mapped_column(Text, default="")
    proposed_html: Mapped[str] = mapped_column(Text, default="")
    proposed_css: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(default="litellm")
    model: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="invalid")
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_applyable: Mapped[bool] = mapped_column(default=False)
    applied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    template: Mapped["HtmlTemplate"] = relationship()
    created_by: Mapped["User"] = relationship()
