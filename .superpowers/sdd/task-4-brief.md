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

