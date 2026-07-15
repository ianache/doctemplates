## Task 1: Proposal Persistence Model and Migration

**Files:**

- Create: `backend/alembic/versions/0014_template_ai_proposals.py`
- Create: `backend/app/models/template_ai_proposal.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces SQLAlchemy class `HtmlTemplateAiProposal`.
- Later tasks import `HtmlTemplateAiProposal` from `app.models.template_ai_proposal`.
- Status values are exact strings: `valid`, `invalid`, `failed`.

- [ ] **Step 1: Write failing model persistence test**

Add this test to `backend/tests/test_template_ai_proposals.py`:

```python
import uuid

from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal


def test_template_ai_proposal_persists_full_history(db_session, user):
    document_type = DocumentType(name="Invoice", description="Invoice document", created_by=user)
    template = HtmlTemplate(
        document_type=document_type,
        name="Invoice base",
        html="<p>{{ customer.name }}</p>",
        css="p { color: black; }",
        token_names=["customer.name"],
        created_by=user,
        mock_data={"customer": {"name": "Ada"}},
    )
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it more formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Added a section wrapper and spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )

    db_session.add(proposal)
    db_session.commit()

    saved = db_session.get(HtmlTemplateAiProposal, proposal.id)
    assert saved is not None
    assert isinstance(saved.id, uuid.UUID)
    assert saved.template_id == template.id
    assert saved.created_by_id == user.id
    assert saved.status == "valid"
    assert saved.validation_errors == []
    assert saved.is_applyable is True
    assert saved.applied_at is None
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_template_ai_proposal_persists_full_history -v"
```

Expected: FAIL with import error for `app.models.template_ai_proposal`.

- [ ] **Step 3: Add model**

Create `backend/app/models/template_ai_proposal.py`:

```python
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
```

Modify `backend/app/models/__init__.py`:

```python
from app.models.template_ai_proposal import HtmlTemplateAiProposal
```

- [ ] **Step 4: Add migration**

Create `backend/alembic/versions/0014_template_ai_proposals.py`:

```python
"""Create HTML template AI proposal history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "html_template_ai_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("template_id", sa.Uuid(), sa.ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("input_html", sa.Text(), nullable=False),
        sa.Column("input_css", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_css", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider", sa.String(), nullable=False, server_default="litellm"),
        sa.Column("model", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="invalid"),
        sa.Column("validation_errors", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False, server_default="[]"),
        sa.Column("is_applyable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('valid', 'invalid', 'failed')",
            name="ck_html_template_ai_proposal_status",
        ),
    )
    op.create_index("ix_html_template_ai_proposals_template_id", "html_template_ai_proposals", ["template_id"])
    op.create_index("ix_html_template_ai_proposals_created_by_id", "html_template_ai_proposals", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_html_template_ai_proposals_created_by_id", table_name="html_template_ai_proposals")
    op.drop_index("ix_html_template_ai_proposals_template_id", table_name="html_template_ai_proposals")
    op.drop_table("html_template_ai_proposals")
```

- [ ] **Step 5: Run test and verify it passes**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_template_ai_proposal_persists_full_history -v"
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add backend/alembic/versions/0014_template_ai_proposals.py backend/app/models/template_ai_proposal.py backend/app/models/__init__.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: add template ai proposal model"
```

