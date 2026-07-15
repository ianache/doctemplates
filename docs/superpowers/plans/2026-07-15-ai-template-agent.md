# AI Template Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a proposal-first AI improvement workflow for existing HTML templates that returns validated, persisted HTML/CSS proposals and lets users apply them into the editor before saving.

**Architecture:** Backend owns proposal creation, LiteLLM orchestration, strict validation, proposal persistence, and apply tracking under the existing content-template API. Frontend adds an edit-mode AI panel that requests proposals, displays history, and applies valid proposals into local editor state without auto-saving. The synchronous backend service boundary must be narrow enough to move proposal creation to async jobs later.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, Jinja2 sandbox validation, LiteLLM, React 19, TypeScript, Vite, existing BFF proxy.

## Global Constraints

- Use LiteLLM as the first AI runtime abstraction.
- Keep AI requests synchronous in Phase 16, but isolate the service boundary for future async jobs.
- Persist full proposal history, including invalid and failed proposals.
- Do not add admin or auditor roles in Phase 16.
- Proposal history is visible to users who can edit the template.
- AI output must be review-first and never auto-save a template.
- Valid proposals can change CSS and full HTML formatting, but must preserve every existing Jinja expression and statement.
- A proposal is applyable only after strict backend validation and preview rendering pass.
- BFF stays a session-aware proxy; do not add custom AI orchestration there.
- Use `rtk` prefixes in verification commands.

---

## File Structure

Create:

- `backend/alembic/versions/0014_template_ai_proposals.py` - migration for proposal history.
- `backend/app/models/template_ai_proposal.py` - proposal persistence model.
- `backend/app/schemas/template_ai_proposal.py` - API request and response schemas.
- `backend/app/services/template_ai_agent.py` - prompt construction, LiteLLM call, response parsing, and validation orchestration.
- `backend/app/api/template_ai_proposals.py` - proposal routes.
- `backend/tests/test_template_ai_proposals.py` - backend API/service tests.
- `frontend/src/pages/content/components/AiProposalPanel.tsx` - editor-side AI proposal panel.

Modify:

- `backend/app/models/__init__.py` - export the proposal model.
- `backend/app/main.py` - include the proposal router.
- `backend/app/config.py` - add AI configuration fields.
- `backend/pyproject.toml` - add `litellm` if not already installed in the backend environment.
- `backend/app/services/content_validation.py` - expose helpers for extracting Jinja expressions/statements when needed.
- `frontend/src/lib/content.ts` - add typed proposal API helpers.
- `frontend/src/pages/content/HtmlTemplateCreatePage.tsx` - mount AI panel in edit mode and wire Apply into local state.

---

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

---

## Task 2: Validation Helpers for AI Proposals

**Files:**

- Modify: `backend/app/services/content_validation.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces `extract_jinja_markers(html: str) -> set[str]`.
- Produces `validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]`.
- Later service task uses these helpers to enforce token and statement preservation.

- [ ] **Step 1: Write failing validation helper tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers


def test_extract_jinja_markers_includes_expressions_and_statements():
    html = """
    <h1>{{ customer.name }}</h1>
    {% for item in items %}
      <p>{{ item.total | date_format }}</p>
    {% endfor %}
    """

    markers = extract_jinja_markers(html)

    assert "{{ customer.name }}" in markers
    assert "{% for item in items %}" in markers
    assert "{{ item.total | date_format }}" in markers
    assert "{% endfor %}" in markers


def test_validate_preserved_jinja_markers_reports_removed_marker():
    original = "<p>{{ customer.name }}</p>{% for item in items %}{{ item.total }}{% endfor %}"
    proposed = "<p>{{ customer.name }}</p>"

    errors = validate_preserved_jinja_markers(original, proposed)

    assert "Missing preserved Jinja marker: {% for item in items %}" in errors
    assert "Missing preserved Jinja marker: {{ item.total }}" in errors
    assert "Missing preserved Jinja marker: {% endfor %}" in errors
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_extract_jinja_markers_includes_expressions_and_statements tests/test_template_ai_proposals.py::test_validate_preserved_jinja_markers_reports_removed_marker -v"
```

Expected: FAIL with import error for the new helper functions.

- [ ] **Step 3: Implement marker helpers**

Add near the top of `backend/app/services/content_validation.py`:

```python
JINJA_MARKER_PATTERN = re.compile(r"(\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\})")


def normalize_jinja_marker(marker: str) -> str:
    marker = " ".join(marker.strip().split())
    if marker.startswith("{{") and marker.endswith("}}"):
        inner = marker[2:-2].strip()
        return f"{{{{ {inner} }}}}"
    if marker.startswith("{%") and marker.endswith("%}"):
        inner = marker[2:-2].strip()
        return f"{{% {inner} %}}"
    return marker


def extract_jinja_markers(html: str) -> set[str]:
    return {normalize_jinja_marker(match.group(0)) for match in JINJA_MARKER_PATTERN.finditer(html or "")}


def validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]:
    original_markers = extract_jinja_markers(original_html)
    proposed_markers = extract_jinja_markers(proposed_html)
    missing = sorted(original_markers - proposed_markers)
    return [f"Missing preserved Jinja marker: {marker}" for marker in missing]
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_extract_jinja_markers_includes_expressions_and_statements tests/test_template_ai_proposals.py::test_validate_preserved_jinja_markers_reports_removed_marker -v"
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
rtk git add backend/app/services/content_validation.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: validate preserved jinja markers"
```

---

## Task 3: AI Agent Service with Strict Validation

**Files:**

- Create: `backend/app/services/template_ai_agent.py`
- Modify: `backend/app/config.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces `TemplateAiAgent.create_proposal(...) -> TemplateAiProposalResult`.
- Produces `TemplateAiProposalResult` dataclass with `proposed_html`, `proposed_css`, `summary`, `status`, `validation_errors`, `is_applyable`, `provider`, `model`.
- Later API route calls `TemplateAiAgent(settings).create_proposal(...)`.

- [ ] **Step 1: Write failing service tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
import pytest

from app.services.template_ai_agent import TemplateAiAgent


def test_template_ai_agent_returns_applyable_result_for_valid_response(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<section><p>{{ customer.name }}</p></section>","css":"section { padding: 24px; }","summary":"Improved spacing."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Make it more formal",
        current_html="<p>{{ customer.name }}</p>",
        current_css="p { color: black; }",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "valid"
    assert result.is_applyable is True
    assert result.validation_errors == []
    assert result.proposed_html == "<section><p>{{ customer.name }}</p></section>"
    assert result.proposed_css == "section { padding: 24px; }"


def test_template_ai_agent_blocks_removed_existing_token(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<section>No token</section>","css":"","summary":"Removed token."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert "Missing preserved Jinja marker: {{ customer.name }}" in result.validation_errors


def test_template_ai_agent_blocks_script_tags(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<script>alert(1)</script><p>{{ customer.name }}</p>","css":"","summary":"Unsafe."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert "Generated HTML cannot include <script> tags." in result.validation_errors


def test_template_ai_agent_reports_failed_invalid_json(monkeypatch):
    def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "not json"}}]}

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert any("valid JSON" in error for error in result.validation_errors)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k template_ai_agent -v"
```

Expected: FAIL with import error for `app.services.template_ai_agent`.

- [ ] **Step 3: Add backend dependency and config**

Modify `backend/pyproject.toml` dependencies:

```toml
"litellm>=1.80.0",
```

Modify `backend/app/config.py` inside `Settings`:

```python
ai_requests_enabled: bool = False
ai_provider_model: str = "gpt-4o-mini"
ai_request_timeout_seconds: int = 30
ai_max_input_chars: int = 20000
ai_max_output_tokens: int = 2000
```

- [ ] **Step 4: Implement service**

Create `backend/app/services/template_ai_agent.py`:

```python
import json
import re
from dataclasses import dataclass

from litellm import completion

from app.services.content_validation import validate_preserved_jinja_markers, validate_template_tokens
from app.services.pdf_generator import render_html_page_to_pdf


UNSAFE_URL_PATTERN = re.compile(r"(https?:)?//", re.IGNORECASE)
INLINE_EVENT_PATTERN = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)


@dataclass
class TemplateAiProposalResult:
    proposed_html: str
    proposed_css: str
    summary: str
    status: str
    validation_errors: list[str]
    is_applyable: bool
    provider: str
    model: str


class TemplateAiAgent:
    def __init__(
        self,
        model: str,
        enabled: bool,
        timeout_seconds: int,
        max_input_chars: int,
        max_output_tokens: int,
    ) -> None:
        self.model = model
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.max_input_chars = max_input_chars
        self.max_output_tokens = max_output_tokens

    def create_proposal(
        self,
        instruction: str,
        current_html: str,
        current_css: str,
        document_fields: list[str],
        mock_data: dict | None,
    ) -> TemplateAiProposalResult:
        if not self.enabled:
            return self._failed("AI requests are disabled.")

        input_size = len(instruction) + len(current_html) + len(current_css) + sum(len(field) for field in document_fields)
        if input_size > self.max_input_chars:
            return self._failed("Template is too large for synchronous AI improvement.")

        messages = self._build_messages(instruction, current_html, current_css, document_fields)

        try:
            response = completion(
                model=self.model,
                messages=messages,
                timeout=self.timeout_seconds,
                max_tokens=self.max_output_tokens,
            )
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:
            return self._failed(f"AI provider did not return valid JSON: {exc}")

        proposed_html = str(parsed.get("html", ""))
        proposed_css = str(parsed.get("css", ""))
        summary = str(parsed.get("summary", ""))
        errors = self._validate(current_html, proposed_html, proposed_css, document_fields, mock_data or {})
        status = "valid" if not errors else "invalid"

        return TemplateAiProposalResult(
            proposed_html=proposed_html,
            proposed_css=proposed_css,
            summary=summary,
            status=status,
            validation_errors=errors,
            is_applyable=status == "valid",
            provider="litellm",
            model=self.model,
        )

    def _build_messages(
        self,
        instruction: str,
        current_html: str,
        current_css: str,
        document_fields: list[str],
    ) -> list[dict[str, str]]:
        system = (
            "You improve print-friendly HTML templates. Return only JSON with keys html, css, summary. "
            "Preserve every existing Jinja expression and statement exactly. Do not add JavaScript, external URLs, "
            "external assets, or new business tokens."
        )
        user = json.dumps(
            {
                "instruction": instruction,
                "current_html": current_html,
                "current_css": current_css,
                "allowed_document_fields": document_fields,
            },
            ensure_ascii=False,
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _validate(
        self,
        current_html: str,
        proposed_html: str,
        proposed_css: str,
        document_fields: list[str],
        mock_data: dict,
    ) -> list[str]:
        errors: list[str] = []
        if not proposed_html.strip():
            errors.append("Generated HTML cannot be empty.")
        if "<script" in proposed_html.lower():
            errors.append("Generated HTML cannot include <script> tags.")
        if INLINE_EVENT_PATTERN.search(proposed_html):
            errors.append("Generated HTML cannot include inline event handlers.")
        if UNSAFE_URL_PATTERN.search(proposed_html) or UNSAFE_URL_PATTERN.search(proposed_css):
            errors.append("Generated HTML/CSS cannot reference external network assets.")

        errors.extend(validate_preserved_jinja_markers(current_html, proposed_html))

        try:
            validate_template_tokens(proposed_html, document_fields)
        except Exception as exc:
            errors.append(str(getattr(exc, "detail", exc)))

        try:
            render_html_page_to_pdf(proposed_html, mock_data, proposed_css)
        except Exception as exc:
            errors.append(str(getattr(exc, "detail", exc)))

        return errors

    def _failed(self, message: str) -> TemplateAiProposalResult:
        return TemplateAiProposalResult(
            proposed_html="",
            proposed_css="",
            summary="",
            status="failed",
            validation_errors=[message],
            is_applyable=False,
            provider="litellm",
            model=self.model,
        )
```

- [ ] **Step 5: Run service tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k template_ai_agent -v"
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add backend/pyproject.toml backend/app/config.py backend/app/services/template_ai_agent.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: add template ai agent service"
```

---

## Task 4: Proposal API Routes

**Files:**

- Create: `backend/app/schemas/template_ai_proposal.py`
- Create: `backend/app/api/template_ai_proposals.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces API routes:
  - `POST /api/content/templates/{template_id}/ai-proposals`
  - `GET /api/content/templates/{template_id}/ai-proposals`
  - `POST /api/content/templates/{template_id}/ai-proposals/{proposal_id}/apply`
- Later frontend task consumes exact response fields from `HtmlTemplateAiProposalOut`.

- [ ] **Step 1: Write failing API tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
from datetime import datetime

from app.services.template_ai_agent import TemplateAiProposalResult


def test_create_ai_proposal_persists_and_returns_applyable(client, db_session, user, monkeypatch):
    template = create_template_fixture(db_session, user)

    def fake_create_proposal(**kwargs):
        return TemplateAiProposalResult(
            proposed_html="<section><p>{{ customer.name }}</p></section>",
            proposed_css="section { padding: 24px; }",
            summary="Improved spacing.",
            status="valid",
            validation_errors=[],
            is_applyable=True,
            provider="litellm",
            model="gpt-4o-mini",
        )

    monkeypatch.setattr("app.api.template_ai_proposals.TemplateAiAgent.create_proposal", fake_create_proposal)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "mock_data": template.mock_data,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["template_id"] == str(template.id)
    assert body["proposed_html"] == "<section><p>{{ customer.name }}</p></section>"
    assert body["is_applyable"] is True
    assert body["status"] == "valid"


def test_apply_ai_proposal_marks_applied_without_mutating_template(client, db_session, user):
    template = create_template_fixture(db_session, user)
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Improved spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )
    db_session.add(proposal)
    db_session.commit()

    response = client.post(f"/api/content/templates/{template.id}/ai-proposals/{proposal.id}/apply")

    assert response.status_code == 200
    body = response.json()
    assert body["applied_at"] is not None
    db_session.refresh(template)
    assert template.html == "<p>{{ customer.name }}</p>"
```

Add this fixture helper above the API tests:

```python
def create_template_fixture(db_session, user):
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
    db_session.add(template)
    db_session.commit()
    return template
```

- [ ] **Step 2: Run API tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k 'create_ai_proposal or apply_ai_proposal' -v"
```

Expected: FAIL with route not found or import error.

- [ ] **Step 3: Add schemas**

Create `backend/app/schemas/template_ai_proposal.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HtmlTemplateAiProposalCreate(BaseModel):
    instruction: str
    current_html: str
    current_css: str | None = ""
    mock_data: dict | None = None


class HtmlTemplateAiProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    created_by_id: UUID
    instruction: str
    input_html: str
    input_css: str
    proposed_html: str
    proposed_css: str
    summary: str
    provider: str
    model: str
    status: str
    validation_errors: list[str]
    is_applyable: bool
    applied_at: datetime | None
    created_at: datetime
```

- [ ] **Step 4: Add routes**

Create `backend/app/api/template_ai_proposals.py`:

```python
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.schemas.template_ai_proposal import HtmlTemplateAiProposalCreate, HtmlTemplateAiProposalOut
from app.services.template_ai_agent import TemplateAiAgent

router = APIRouter(prefix="/api/content/templates/{template_id}/ai-proposals", tags=["template-ai-proposals"])


def _load_template(template_id: UUID, db: SQLAlchemySession) -> HtmlTemplate:
    template = (
        db.query(HtmlTemplate)
        .options(joinedload(HtmlTemplate.document_type).joinedload("fields"), joinedload(HtmlTemplate.created_by))
        .filter(HtmlTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("", response_model=HtmlTemplateAiProposalOut, status_code=201)
def create_ai_proposal(
    template_id: UUID,
    payload: HtmlTemplateAiProposalCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateAiProposalOut:
    template = _load_template(template_id, db)
    agent = TemplateAiAgent(
        model=settings.ai_provider_model,
        enabled=settings.ai_requests_enabled,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_input_chars=settings.ai_max_input_chars,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    result = agent.create_proposal(
        instruction=payload.instruction,
        current_html=payload.current_html,
        current_css=payload.current_css or "",
        document_fields=[field.name for field in template.document_type.fields],
        mock_data=payload.mock_data or template.mock_data or {},
    )
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction=payload.instruction,
        input_html=payload.current_html,
        input_css=payload.current_css or "",
        proposed_html=result.proposed_html,
        proposed_css=result.proposed_css,
        summary=result.summary,
        provider=result.provider,
        model=result.model,
        status=result.status,
        validation_errors=result.validation_errors,
        is_applyable=result.is_applyable,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get("", response_model=list[HtmlTemplateAiProposalOut])
def list_ai_proposals(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[HtmlTemplateAiProposalOut]:
    _load_template(template_id, db)
    return (
        db.query(HtmlTemplateAiProposal)
        .filter(HtmlTemplateAiProposal.template_id == template_id)
        .order_by(HtmlTemplateAiProposal.created_at.desc())
        .all()
    )


@router.post("/{proposal_id}/apply", response_model=HtmlTemplateAiProposalOut)
def mark_ai_proposal_applied(
    template_id: UUID,
    proposal_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateAiProposalOut:
    _load_template(template_id, db)
    proposal = (
        db.query(HtmlTemplateAiProposal)
        .filter(
            HtmlTemplateAiProposal.id == proposal_id,
            HtmlTemplateAiProposal.template_id == template_id,
        )
        .first()
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    if not proposal.is_applyable:
        raise HTTPException(status_code=400, detail="AI proposal is not applyable")
    proposal.applied_at = datetime.utcnow()
    db.commit()
    db.refresh(proposal)
    return proposal
```

If SQLAlchemy rejects the string-based nested `joinedload`, replace `_load_template` options with the typed field import:

```python
from app.models.document_type import DocumentType

.options(joinedload(HtmlTemplate.document_type).joinedload(DocumentType.fields), joinedload(HtmlTemplate.created_by))
```

- [ ] **Step 5: Include router**

Modify `backend/app/main.py`:

```python
from app.api.template_ai_proposals import router as template_ai_proposals_router
```

And add:

```python
app.include_router(template_ai_proposals_router)
```

- [ ] **Step 6: Run API tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k 'create_ai_proposal or apply_ai_proposal' -v"
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
rtk git add backend/app/schemas/template_ai_proposal.py backend/app/api/template_ai_proposals.py backend/app/main.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: expose template ai proposal api"
```

---

## Task 5: Frontend API Client

**Files:**

- Modify: `frontend/src/lib/content.ts`

**Interfaces:**

- Produces `TemplateAiProposal` interface.
- Produces `createTemplateAiProposal(templateId, payload)`.
- Produces `listTemplateAiProposals(templateId)`.
- Produces `markTemplateAiProposalApplied(templateId, proposalId)`.
- Later UI task imports these functions.

- [ ] **Step 1: Add TypeScript interfaces and client functions**

Modify `frontend/src/lib/content.ts`:

```ts
export interface TemplateAiProposal {
  id: string;
  template_id: string;
  created_by_id: string;
  instruction: string;
  input_html: string;
  input_css: string;
  proposed_html: string;
  proposed_css: string;
  summary: string;
  provider: string;
  model: string;
  status: "valid" | "invalid" | "failed";
  validation_errors: string[];
  is_applyable: boolean;
  applied_at: string | null;
  created_at: string;
}

export interface TemplateAiProposalCreatePayload {
  instruction: string;
  current_html: string;
  current_css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export async function createTemplateAiProposal(
  templateId: string,
  payload: TemplateAiProposalCreatePayload,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function listTemplateAiProposals(templateId: string): Promise<TemplateAiProposal[]> {
  return jsonOrError(await apiFetch(`/api/content/templates/${templateId}/ai-proposals`));
}

export async function markTemplateAiProposalApplied(
  templateId: string,
  proposalId: string,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals/${proposalId}/apply`, {
      method: "POST",
    }),
  );
}
```

- [ ] **Step 2: Run frontend type build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
rtk git add frontend/src/lib/content.ts
rtk git commit -m "feat: add template ai proposal client"
```

---

## Task 6: AI Proposal Panel UI

**Files:**

- Create: `frontend/src/pages/content/components/AiProposalPanel.tsx`
- Modify: `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`

**Interfaces:**

- `AiProposalPanel` props:
  - `templateId: string | null`
  - `html: string`
  - `css: string`
  - `mockDataJson: string`
  - `onApply(proposal: TemplateAiProposal): void`
- Consumes frontend API helpers from Task 5.

- [ ] **Step 1: Create panel component**

Create `frontend/src/pages/content/components/AiProposalPanel.tsx`:

```tsx
import { useEffect, useState } from "react";

import {
  createTemplateAiProposal,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type TemplateAiProposal,
} from "../../../lib/content";

interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  onApply: (proposal: TemplateAiProposal) => void;
}

function parseMockData(mockDataJson: string): Record<string, unknown> | null {
  if (!mockDataJson.trim()) return null;
  const parsed = JSON.parse(mockDataJson);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Mock data must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

export default function AiProposalPanel({ templateId, html, css, mockDataJson, onApply }: AiProposalPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [proposals, setProposals] = useState<TemplateAiProposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<TemplateAiProposal | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "html" | "css">("summary");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!templateId) return;
    let cancelled = false;
    listTemplateAiProposals(templateId)
      .then((rows) => {
        if (cancelled) return;
        setProposals(rows);
        setActiveProposal(rows[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load AI proposal history.");
      });
    return () => {
      cancelled = true;
    };
  }, [templateId]);

  const requestProposal = async () => {
    if (!templateId || !instruction.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
      });
      setProposals((current) => [proposal, ...current]);
      setActiveProposal(proposal);
      setActiveTab("summary");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI proposal failed.");
    } finally {
      setLoading(false);
    }
  };

  const applyProposal = async () => {
    if (!templateId || !activeProposal || !activeProposal.is_applyable) return;
    const applied = await markTemplateAiProposalApplied(templateId, activeProposal.id);
    onApply(applied);
    setProposals((current) => current.map((proposal) => (proposal.id === applied.id ? applied : proposal)));
    setActiveProposal(applied);
  };

  if (!templateId) {
    return (
      <div className="rounded border border-outline-variant bg-surface-container-low p-sm text-xs text-secondary">
        AI improvements are available after this template is created.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-sm rounded border border-outline-variant bg-white p-sm">
      <div className="flex items-center gap-xs">
        <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
        <h3 className="font-headings text-sm font-bold text-on-surface">AI Improve</h3>
      </div>

      <textarea
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
        rows={3}
        aria-label="AI improvement instruction"
        className="w-full rounded border border-outline-variant p-sm text-xs text-on-surface focus:border-primary focus:outline-none"
      />

      <button
        type="button"
        onClick={requestProposal}
        disabled={loading || !instruction.trim()}
        className="rounded bg-primary px-md py-xs text-xs font-bold text-white disabled:opacity-50"
      >
        {loading ? "Generating..." : "Suggest improvement"}
      </button>

      {error ? <p className="text-xs text-error">{error}</p> : null}

      {activeProposal ? (
        <div className="space-y-sm border-t border-outline-variant pt-sm">
          <div className="flex gap-xs">
            {(["summary", "html", "css"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded px-sm py-xs text-xs font-bold ${
                  activeTab === tab ? "bg-primary text-white" : "bg-surface-container text-secondary"
                }`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>

          {activeTab === "summary" ? (
            <div className="space-y-xs text-xs">
              <p className="text-on-surface">{activeProposal.summary || "No summary provided."}</p>
              {activeProposal.validation_errors.length ? (
                <ul className="list-disc pl-md text-error">
                  {activeProposal.validation_errors.map((validationError) => (
                    <li key={validationError}>{validationError}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <textarea
              readOnly
              value={activeTab === "html" ? activeProposal.proposed_html : activeProposal.proposed_css}
              rows={10}
              className="w-full rounded border border-outline-variant bg-slate-900 p-sm font-mono text-xs text-slate-100"
            />
          )}

          <button
            type="button"
            onClick={applyProposal}
            disabled={!activeProposal.is_applyable}
            className="rounded border border-primary px-md py-xs text-xs font-bold text-primary disabled:border-outline-variant disabled:text-secondary"
          >
            Apply proposal
          </button>
        </div>
      ) : null}

      {proposals.length ? (
        <div className="border-t border-outline-variant pt-sm">
          <h4 className="text-[11px] font-bold uppercase text-secondary">History</h4>
          <div className="mt-xs max-h-32 overflow-y-auto space-y-xs">
            {proposals.map((proposal) => (
              <button
                key={proposal.id}
                type="button"
                onClick={() => setActiveProposal(proposal)}
                className="block w-full rounded border border-outline-variant px-sm py-xs text-left text-xs hover:bg-surface-container"
              >
                <span className="font-bold">{proposal.status}</span> - {new Date(proposal.created_at).toLocaleString()}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
```

- [ ] **Step 2: Mount panel in editor**

Modify `frontend/src/pages/content/HtmlTemplateCreatePage.tsx` imports:

```tsx
import AiProposalPanel from "./components/AiProposalPanel";
import type { TemplateAiProposal } from "../../lib/content";
```

Add handler inside `HtmlTemplateCreatePage`:

```tsx
const handleApplyAiProposal = (proposal: TemplateAiProposal) => {
  setHtml(proposal.proposed_html);
  setCss(proposal.proposed_css);
  setHtmlTouched(true);
};
```

Insert the panel at the top of the right panel before the CSS section. Change the CSS and mock-data panel heights from `h-1/2` to flexible thirds:

```tsx
<div className="h-1/3 overflow-y-auto border-b border-outline-variant p-sm bg-surface">
  <AiProposalPanel
    templateId={isEditMode && id ? id : null}
    html={html}
    css={css}
    mockDataJson={mockDataJson}
    onApply={handleApplyAiProposal}
  />
</div>
```

Then update the CSS and mock-data wrappers to:

```tsx
<div className="h-1/3 flex flex-col border-b border-outline-variant overflow-hidden">
```

and:

```tsx
<div className="h-1/3 flex flex-col overflow-hidden">
```

- [ ] **Step 3: Run frontend build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
rtk git add frontend/src/pages/content/components/AiProposalPanel.tsx frontend/src/pages/content/HtmlTemplateCreatePage.tsx
rtk git commit -m "feat: add ai proposal panel"
```

---

## Task 7: End-to-End Verification and Documentation

**Files:**

- Modify: `.env.example`
- Modify: `.planning/ROADMAP.md`
- Create or modify: `.planning/phases/16-ai-agent-for-page-templating/16-01-PLAN.md`

**Interfaces:**

- Documents required environment variables and verification commands.
- Marks Phase 16 planning artifacts consistently with GSD conventions.

- [ ] **Step 1: Document AI environment configuration**

Add to `.env.example`:

```dotenv
AI_REQUESTS_ENABLED=false
AI_PROVIDER_MODEL=gpt-4o-mini
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_INPUT_CHARS=20000
AI_MAX_OUTPUT_TOKENS=2000
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
```

- [ ] **Step 2: Run backend proposal tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -v"
```

Expected: PASS.

- [ ] **Step 3: Run existing template regression tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_content_templates.py tests/test_template_ast_validation.py tests/test_pdf_generator.py -v"
```

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 5: Manual UAT**

Run the app with the existing local development flow, then verify:

```text
1. Open an existing HTML template in edit mode.
2. Confirm AI Improve panel is visible.
3. Enter: Make this template more formal and print-friendly.
4. Confirm a valid proposal appears.
5. Confirm invalid validation errors block Apply when the mocked/provider output removes a token.
6. Apply a valid proposal.
7. Confirm local HTML and CSS fields update.
8. Click Save Changes.
9. Preview or generate a document using the saved template.
```

- [ ] **Step 6: Commit documentation and planning updates**

Run:

```bash
rtk git add .env.example .planning/ROADMAP.md .planning/phases/16-ai-agent-for-page-templating/16-01-PLAN.md
rtk git commit -m "docs: document ai template agent verification"
```

---

## Self-Review Notes

Spec coverage:

- Proposal-first backend agent is covered by Tasks 3 and 4.
- LiteLLM abstraction is covered by Task 3.
- Strict validation is covered by Tasks 2 and 3.
- Persisted full proposal history is covered by Tasks 1 and 4.
- Frontend review/apply flow is covered by Tasks 5 and 6.
- No admin/auditor role work is introduced.
- Sync-first, async-ready service boundary is covered by `TemplateAiAgent`.

Completeness scan:

- No deferred implementation markers are used.
- Every task has files, interfaces, commands, and expected outcomes.

Type consistency:

- Backend proposal status values are consistent across model, service, schemas, and frontend types.
- API response field names match Pydantic schema and frontend interfaces.
- Frontend Apply uses `proposed_html` and `proposed_css`, matching backend response fields.
