# AI Improve Models and Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend-controlled Gemini, Groq, and Ollama model selection for AI Improve and reorganize the template editor right panel into `AI Chat` and `Settings` tabs.

**Architecture:** Keep LiteLLM as the single provider adapter. Add a small backend model catalog service that parses an allowlist from env, exposes it through an authenticated endpoint, validates selected models during proposal creation, and normalizes provider configuration errors. Update the frontend panel to load the catalog, persist the selected model in `localStorage`, send it with proposal requests, and move CSS/mock JSON editing into a `Settings` tab.

**Tech Stack:** FastAPI, Pydantic Settings, SQLAlchemy, pytest, LiteLLM, React 19, TypeScript, Vite, Tailwind utility classes.

## Global Constraints

- AI requests remain disabled by default.
- Provider credentials stay server-side.
- Generated templates are validated before they can be applied.
- The BFF remains a generic proxy.
- Keep LiteLLM as the provider abstraction.
- The user chooses provider/model in UI from a backend-provided allowlist.
- Persist selected model in `localStorage`.
- AI Chat is a simple single-instruction proposal flow in this phase.
- Ollama uses an existing external/local instance through `OLLAMA_API_BASE`; do not add an Ollama Docker Compose service.
- Out of scope: multi-turn memory, streaming, UI-managed secrets, backend user preference persistence.

---

## File Structure

- Create `backend/app/services/ai_model_catalog.py`: parse allowed model IDs, derive provider/label/required config, validate defaults, check provider readiness.
- Modify `backend/app/config.py`: add `ai_default_model`, `ai_allowed_models`, provider API/base settings, and compatibility fallback for `ai_provider_model`.
- Create `backend/app/api/ai_models.py`: authenticated `GET /api/content/ai-models`.
- Modify `backend/app/main.py`: include the new AI model catalog router.
- Modify `backend/app/schemas/template_ai_proposal.py`: add optional `model` to create payload.
- Modify `backend/app/api/template_ai_proposals.py`: resolve/validate selected model and pass it into `TemplateAiAgent`.
- Modify `backend/app/services/template_ai_agent.py`: accept provider label and expose normalized provider/model in results; normalize missing provider configuration failures.
- Modify `backend/tests/test_template_ai_proposals.py`: add model-selection proposal tests and agent selected-model assertion.
- Create `backend/tests/test_ai_model_catalog.py`: focused model catalog parsing and API tests.
- Modify `frontend/src/lib/content.ts`: add model catalog types/client and `model` on proposal creation payload.
- Modify `frontend/src/pages/content/components/AiProposalPanel.tsx`: convert to tabbed AI Chat/Settings panel with model selector and localStorage persistence.
- Modify `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`: move CSS/mock data UI ownership into `AiProposalPanel`.
- Modify `.env.example` and `docker-compose.yml`: document/pass Gemini, Groq, and Ollama variables.

---

### Task 1: Backend AI Model Catalog

**Files:**
- Create: `backend/app/services/ai_model_catalog.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_ai_model_catalog.py`

**Interfaces:**
- Produces: `AiModelOption`, `AiModelCatalog`, `build_ai_model_catalog(settings)`, `resolve_ai_model(settings, requested_model)`, `is_provider_configured(settings, option)`.
- Consumes: `settings.ai_allowed_models`, `settings.ai_default_model`, `settings.ai_provider_model`, `settings.gemini_api_key`, `settings.groq_api_key`, `settings.ollama_api_base`.

- [ ] **Step 1: Write failing catalog tests**

Add `backend/tests/test_ai_model_catalog.py`:

```python
from types import SimpleNamespace

import pytest

from app.services.ai_model_catalog import build_ai_model_catalog, resolve_ai_model


def make_settings(**overrides):
    values = {
        "ai_requests_enabled": True,
        "ai_default_model": "gemini/gemini-2.0-flash",
        "ai_provider_model": "gpt-4o-mini",
        "ai_allowed_models": "gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1",
        "gemini_api_key": "gemini-key",
        "groq_api_key": "",
        "ollama_api_base": "http://localhost:11434",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_ai_model_catalog_parses_allowed_models():
    catalog = build_ai_model_catalog(make_settings())

    assert catalog.enabled is True
    assert catalog.default_model == "gemini/gemini-2.0-flash"
    assert [model.id for model in catalog.models] == [
        "gemini/gemini-2.0-flash",
        "groq/llama-3.1-8b-instant",
        "ollama/llama3.1",
    ]
    assert catalog.models[0].provider == "gemini"
    assert catalog.models[0].label == "Gemini 2.0 Flash"
    assert catalog.models[0].requires == "GEMINI_API_KEY"


def test_resolve_ai_model_uses_default_when_request_omits_model():
    option = resolve_ai_model(make_settings(), None)

    assert option.id == "gemini/gemini-2.0-flash"


def test_resolve_ai_model_rejects_non_allowlisted_model():
    with pytest.raises(ValueError, match="AI model is not allowed"):
        resolve_ai_model(make_settings(), "openai/gpt-5")


def test_empty_allowlist_is_configuration_error_for_resolution():
    with pytest.raises(ValueError, match="No AI models are configured"):
        resolve_ai_model(make_settings(ai_allowed_models=""), None)


def test_default_model_must_be_in_allowlist():
    with pytest.raises(ValueError, match="AI default model must be included"):
        build_ai_model_catalog(
            make_settings(
                ai_default_model="groq/llama-3.1-8b-instant",
                ai_allowed_models="gemini/gemini-2.0-flash",
            )
        )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
rtk pytest backend/tests/test_ai_model_catalog.py -q
```

Expected: FAIL because `app.services.ai_model_catalog` does not exist.

- [ ] **Step 3: Extend settings**

Modify `backend/app/config.py`:

```python
    ai_requests_enabled: bool = False
    ai_provider_model: str = "gpt-4o-mini"
    ai_default_model: str = "gpt-4o-mini"
    ai_allowed_models: str = "gpt-4o-mini"
    ai_request_timeout_seconds: int = 30
    ai_max_input_chars: int = 20000
    ai_max_output_tokens: int = 2000
    gemini_api_key: str = ""
    groq_api_key: str = ""
    ollama_api_base: str = "http://localhost:11434"
```

- [ ] **Step 4: Implement catalog service**

Create `backend/app/services/ai_model_catalog.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AiModelOption:
    id: str
    provider: str
    label: str
    requires: str


@dataclass(frozen=True)
class AiModelCatalog:
    enabled: bool
    default_model: str
    models: list[AiModelOption]


def _split_models(raw_value: str) -> list[str]:
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _provider_for_model(model_id: str) -> str:
    if "/" not in model_id:
        return "openai"
    return model_id.split("/", 1)[0]


def _label_for_model(model_id: str) -> str:
    provider = _provider_for_model(model_id)
    name = model_id.split("/", 1)[1] if "/" in model_id else model_id
    return f"{provider.title()} {name.replace('-', ' ').replace('_', ' ').title()}"


def _required_config(provider: str) -> str:
    return {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "ollama": "OLLAMA_API_BASE",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider, "")


def build_ai_model_catalog(settings) -> AiModelCatalog:
    model_ids = _split_models(settings.ai_allowed_models)
    default_model = settings.ai_default_model or settings.ai_provider_model
    if model_ids and default_model not in model_ids:
        raise ValueError("AI default model must be included in AI_ALLOWED_MODELS.")
    return AiModelCatalog(
        enabled=settings.ai_requests_enabled,
        default_model=default_model,
        models=[
            AiModelOption(
                id=model_id,
                provider=_provider_for_model(model_id),
                label=_label_for_model(model_id),
                requires=_required_config(_provider_for_model(model_id)),
            )
            for model_id in model_ids
        ],
    )


def resolve_ai_model(settings, requested_model: str | None) -> AiModelOption:
    catalog = build_ai_model_catalog(settings)
    if not catalog.models:
        raise ValueError("No AI models are configured.")
    selected_model = requested_model or catalog.default_model
    for option in catalog.models:
        if option.id == selected_model:
            return option
    raise ValueError("AI model is not allowed.")


def is_provider_configured(settings, option: AiModelOption) -> bool:
    if option.provider == "gemini":
        return bool(settings.gemini_api_key)
    if option.provider == "groq":
        return bool(settings.groq_api_key)
    if option.provider == "ollama":
        return bool(settings.ollama_api_base)
    return True
```

- [ ] **Step 5: Run catalog tests**

Run:

```powershell
rtk pytest backend/tests/test_ai_model_catalog.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
rtk git add backend/app/config.py backend/app/services/ai_model_catalog.py backend/tests/test_ai_model_catalog.py
rtk git commit -m "feat: add AI model catalog"
```

---

### Task 2: Backend Model Catalog API

**Files:**
- Create: `backend/app/api/ai_models.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ai_model_catalog.py`

**Interfaces:**
- Consumes: `build_ai_model_catalog(settings)`.
- Produces: `GET /api/content/ai-models` with `enabled`, `default_model`, and `models`.

- [ ] **Step 1: Add failing API test**

Append to `backend/tests/test_ai_model_catalog.py`:

```python
def test_get_ai_models_returns_catalog(client, monkeypatch, db_session, user):
    from app.auth.session_service import create_session
    from app.api import ai_models

    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    monkeypatch.setattr(ai_models.settings, "ai_requests_enabled", True)
    monkeypatch.setattr(ai_models.settings, "ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr(ai_models.settings, "ai_provider_model", "gpt-4o-mini")
    monkeypatch.setattr(
        ai_models.settings,
        "ai_allowed_models",
        "gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1",
    )

    response = client.get("/api/content/ai-models")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["default_model"] == "gemini/gemini-2.0-flash"
    assert body["models"][0]["id"] == "gemini/gemini-2.0-flash"
    assert body["models"][0]["requires"] == "GEMINI_API_KEY"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
rtk pytest backend/tests/test_ai_model_catalog.py::test_get_ai_models_returns_catalog -q
```

Expected: FAIL because `app.api.ai_models` or the route does not exist.

- [ ] **Step 3: Implement router**

Create `backend/app/api/ai_models.py`:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models.user import User
from app.services.ai_model_catalog import build_ai_model_catalog


router = APIRouter(prefix="/api/content/ai-models", tags=["ai-models"])


class AiModelOptionOut(BaseModel):
    id: str
    provider: str
    label: str
    requires: str


class AiModelCatalogOut(BaseModel):
    enabled: bool
    default_model: str
    models: list[AiModelOptionOut]


@router.get("", response_model=AiModelCatalogOut)
def get_ai_models(user: User = Depends(get_current_user)) -> AiModelCatalogOut:
    catalog = build_ai_model_catalog(settings)
    return AiModelCatalogOut(
        enabled=catalog.enabled,
        default_model=catalog.default_model,
        models=[
            AiModelOptionOut(
                id=model.id,
                provider=model.provider,
                label=model.label,
                requires=model.requires,
            )
            for model in catalog.models
        ],
    )
```

- [ ] **Step 4: Register router**

Modify `backend/app/main.py`:

```python
from app.api import ai_models
```

and include it beside the other content routers:

```python
app.include_router(ai_models.router)
```

- [ ] **Step 5: Run API test**

Run:

```powershell
rtk pytest backend/tests/test_ai_model_catalog.py::test_get_ai_models_returns_catalog -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
rtk git add backend/app/api/ai_models.py backend/app/main.py backend/tests/test_ai_model_catalog.py
rtk git commit -m "feat: expose AI model catalog"
```

---

### Task 3: Selected Model Validation in Proposal Creation

**Files:**
- Modify: `backend/app/schemas/template_ai_proposal.py`
- Modify: `backend/app/api/template_ai_proposals.py`
- Modify: `backend/app/services/template_ai_agent.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**
- Consumes: `resolve_ai_model(settings, payload.model)` and `is_provider_configured(settings, option)`.
- Produces: proposal creation that accepts optional `model`, validates allowlist, checks provider configuration, and stores selected model.

- [ ] **Step 1: Add failing proposal tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
def test_create_ai_proposal_passes_selected_model(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    captured = {}

    def fake_create_proposal(self, **kwargs):
        captured["model"] = self.model
        return TemplateAiProposalResult(
            proposed_html="<section><p>{{ customer.name }}</p></section>",
            proposed_css="section { padding: 24px; }",
            summary="Improved spacing.",
            status="valid",
            validation_errors=[],
            is_applyable=True,
            provider="gemini",
            model=self.model,
        )

    monkeypatch.setattr("app.services.template_ai_agent.TemplateAiAgent.create_proposal", fake_create_proposal)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "gemini/gemini-2.0-flash")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.gemini_api_key", "key")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "mock_data": template.mock_data,
            "model": "gemini/gemini-2.0-flash",
        },
    )

    assert response.status_code == 201
    assert captured["model"] == "gemini/gemini-2.0-flash"
    assert response.json()["model"] == "gemini/gemini-2.0-flash"


def test_create_ai_proposal_rejects_disallowed_model(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "gemini/gemini-2.0-flash")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "model": "groq/llama-3.1-8b-instant",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "AI model is not allowed."


def test_create_ai_proposal_returns_failed_when_provider_unconfigured(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "groq/llama-3.1-8b-instant")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "groq/llama-3.1-8b-instant")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.groq_api_key", "")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "model": "groq/llama-3.1-8b-instant",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["validation_errors"] == ["Provider is not configured."]
    assert body["is_applyable"] is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
rtk pytest backend/tests/test_template_ai_proposals.py::test_create_ai_proposal_passes_selected_model backend/tests/test_template_ai_proposals.py::test_create_ai_proposal_rejects_disallowed_model backend/tests/test_template_ai_proposals.py::test_create_ai_proposal_returns_failed_when_provider_unconfigured -q
```

Expected: FAIL because `model` is not accepted or validated yet.

- [ ] **Step 3: Extend create schema**

Modify `backend/app/schemas/template_ai_proposal.py`:

```python
class HtmlTemplateAiProposalCreate(BaseModel):
    instruction: str
    current_html: str
    current_css: str | None = ""
    mock_data: dict | None = None
    model: str | None = None
```

- [ ] **Step 4: Add an agent factory for failed provider configuration**

Modify `backend/app/services/template_ai_agent.py`:

```python
    def provider_configuration_failed(self) -> TemplateAiProposalResult:
        return self._failed("Provider is not configured.")
```

- [ ] **Step 5: Validate model in proposal endpoint**

Modify `backend/app/api/template_ai_proposals.py` imports:

```python
from app.services.ai_model_catalog import is_provider_configured, resolve_ai_model
```

Replace agent construction logic in `create_ai_proposal`:

```python
    try:
        selected_model = resolve_ai_model(settings, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    agent = TemplateAiAgent(
        model=selected_model.id,
        enabled=settings.ai_requests_enabled,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_input_chars=settings.ai_max_input_chars,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    if not is_provider_configured(settings, selected_model):
        result = agent.provider_configuration_failed()
    else:
        result = agent.create_proposal(
            instruction=payload.instruction,
            current_html=payload.current_html,
            current_css=payload.current_css or "",
            document_fields=[field.name for field in template.document_type.fields],
            mock_data=payload.mock_data or template.mock_data or {},
        )
```

Keep the existing proposal persistence block after this code.

- [ ] **Step 6: Run selected backend tests**

Run:

```powershell
rtk pytest backend/tests/test_template_ai_proposals.py backend/tests/test_ai_model_catalog.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
rtk git add backend/app/schemas/template_ai_proposal.py backend/app/api/template_ai_proposals.py backend/app/services/template_ai_agent.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: validate selected AI proposal model"
```

---

### Task 4: Environment and Docker Provider Configuration

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: backend settings added in Task 1.
- Produces: documented and container-passed `AI_DEFAULT_MODEL`, `AI_ALLOWED_MODELS`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OLLAMA_API_BASE`.

- [ ] **Step 1: Update `.env.example`**

Replace the AI block with:

```env
# AI Improve is disabled by default. To enable it, set AI_REQUESTS_ENABLED=true,
# configure the selected provider, and restart/recreate the backend service
# when running through Docker Compose.
AI_REQUESTS_ENABLED=false
AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
AI_PROVIDER_MODEL=gpt-4o-mini
AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_INPUT_CHARS=20000
AI_MAX_OUTPUT_TOKENS=2000
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# GEMINI_API_KEY=
# GROQ_API_KEY=
# OLLAMA_API_BASE=http://host.docker.internal:11434
```

- [ ] **Step 2: Update Docker Compose backend environment**

In `docker-compose.yml`, under `backend.environment`, ensure this block exists:

```yaml
      AI_REQUESTS_ENABLED: ${AI_REQUESTS_ENABLED:-false}
      AI_DEFAULT_MODEL: ${AI_DEFAULT_MODEL:-gemini/gemini-2.0-flash}
      AI_PROVIDER_MODEL: ${AI_PROVIDER_MODEL:-gpt-4o-mini}
      AI_ALLOWED_MODELS: ${AI_ALLOWED_MODELS:-gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1}
      AI_REQUEST_TIMEOUT_SECONDS: ${AI_REQUEST_TIMEOUT_SECONDS:-30}
      AI_MAX_INPUT_CHARS: ${AI_MAX_INPUT_CHARS:-20000}
      AI_MAX_OUTPUT_TOKENS: ${AI_MAX_OUTPUT_TOKENS:-2000}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
      OLLAMA_API_BASE: ${OLLAMA_API_BASE:-http://host.docker.internal:11434}
```

- [ ] **Step 3: Verify config text**

Run:

```powershell
rtk proxy powershell -NoProfile -Command "Select-String -Path .env.example,docker-compose.yml -Pattern 'GEMINI_API_KEY','GROQ_API_KEY','OLLAMA_API_BASE','AI_ALLOWED_MODELS'"
```

Expected: all four names appear in both files.

- [ ] **Step 4: Commit**

```powershell
rtk git add .env.example docker-compose.yml
rtk git commit -m "chore: document AI provider configuration"
```

---

### Task 5: Frontend API Client for Model Catalog

**Files:**
- Modify: `frontend/src/lib/content.ts`

**Interfaces:**
- Produces: `AiModelOption`, `AiModelCatalog`, `getAiModels()`, and `TemplateAiProposalCreatePayload.model`.
- Consumes: `GET /api/content/ai-models` and existing `createTemplateAiProposal`.

- [ ] **Step 1: Add TypeScript interfaces and client**

Modify `frontend/src/lib/content.ts` after preview types:

```ts
export interface AiModelOption {
  id: string;
  provider: string;
  label: string;
  requires: string;
}

export interface AiModelCatalog {
  enabled: boolean;
  default_model: string;
  models: AiModelOption[];
}

export async function getAiModels(): Promise<AiModelCatalog> {
  return jsonOrError(await apiFetch("/api/content/ai-models"));
}
```

Extend `TemplateAiProposalCreatePayload`:

```ts
export interface TemplateAiProposalCreatePayload {
  instruction: string;
  current_html: string;
  current_css?: string | null;
  mock_data?: Record<string, unknown> | null;
  model?: string | null;
}
```

- [ ] **Step 2: Run frontend type check/build**

Run:

```powershell
rtk npm run build
```

from `frontend/`.

Expected: PASS.

- [ ] **Step 3: Commit**

```powershell
rtk git add frontend/src/lib/content.ts
rtk git commit -m "feat: add AI model catalog client"
```

---

### Task 6: Right Panel Tabs and AI Chat Model Selection

**Files:**
- Modify: `frontend/src/pages/content/components/AiProposalPanel.tsx`
- Modify: `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`

**Interfaces:**
- Consumes: `getAiModels()`, `createTemplateAiProposal(..., { model })`.
- Produces: tabbed panel props that own AI chat, CSS editor, mock data editor, and model localStorage selection.

- [ ] **Step 1: Replace component props**

Modify `AiProposalPanelProps` in `frontend/src/pages/content/components/AiProposalPanel.tsx`:

```ts
interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  mockDataError: string | null;
  onCssChange: (value: string) => void;
  onMockDataJsonChange: (value: string) => void;
  onApply: (proposal: TemplateAiProposal) => void;
}
```

- [ ] **Step 2: Add model catalog state**

Import the new client:

```ts
import {
  createTemplateAiProposal,
  getAiModels,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type AiModelCatalog,
  type TemplateAiProposal,
} from "../../../lib/content";
```

Add constants and state:

```ts
const AI_MODEL_STORAGE_KEY = "docmanagement.aiImprove.selectedModel";

const [panelTab, setPanelTab] = useState<"chat" | "settings">("chat");
const [modelCatalog, setModelCatalog] = useState<AiModelCatalog | null>(null);
const [selectedModel, setSelectedModel] = useState<string>("");
```

- [ ] **Step 3: Load and persist selected model**

Add effect:

```ts
useEffect(() => {
  let cancelled = false;
  getAiModels()
    .then((catalog) => {
      if (cancelled) return;
      setModelCatalog(catalog);
      const stored = window.localStorage.getItem(AI_MODEL_STORAGE_KEY);
      const allowed = new Set(catalog.models.map((model) => model.id));
      const nextModel =
        stored && allowed.has(stored)
          ? stored
          : allowed.has(catalog.default_model)
          ? catalog.default_model
          : catalog.models[0]?.id ?? "";
      setSelectedModel(nextModel);
    })
    .catch(() => {
      if (!cancelled) setError("We couldn't load AI model settings.");
    });
  return () => {
    cancelled = true;
  };
}, []);
```

Add handler:

```ts
const handleSelectedModelChange = (value: string) => {
  setSelectedModel(value);
  window.localStorage.setItem(AI_MODEL_STORAGE_KEY, value);
};
```

- [ ] **Step 4: Include model in proposal request**

Update `requestProposal` body:

```ts
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
        model: selectedModel || null,
      });
```

Before sending, block invalid mock JSON and missing model:

```ts
    if (mockDataError) {
      setError("Fix Mock Preview Data JSON before generating.");
      return;
    }
    if (!selectedModel) {
      setError("Choose an AI model before generating.");
      return;
    }
```

- [ ] **Step 5: Render top-level tabs**

At the top of the returned section, render:

```tsx
<div className="flex rounded bg-surface-container p-[2px]">
  <button
    type="button"
    onClick={() => setPanelTab("chat")}
    className={`flex-1 rounded px-sm py-xs text-xs font-bold ${panelTab === "chat" ? "bg-white text-primary shadow-sm" : "text-secondary"}`}
  >
    AI Chat
  </button>
  <button
    type="button"
    onClick={() => setPanelTab("settings")}
    className={`flex-1 rounded px-sm py-xs text-xs font-bold ${panelTab === "settings" ? "bg-white text-primary shadow-sm" : "text-secondary"}`}
  >
    Settings
  </button>
</div>
```

- [ ] **Step 6: Render AI Chat tab**

For `panelTab === "chat"`, render model selector, instruction textarea, generate button, error/proposal/history. Use existing proposal rendering, but show provider/model metadata:

```tsx
{panelTab === "chat" ? (
  <div className="flex min-h-0 flex-1 flex-col gap-sm">
    <label className="block text-[11px] font-bold uppercase text-secondary">
      Model
      <select
        value={selectedModel}
        onChange={(event) => handleSelectedModelChange(event.target.value)}
        className="mt-xs w-full rounded border border-outline-variant px-sm py-xs text-xs text-on-surface focus:border-primary focus:outline-none"
      >
        {modelCatalog?.models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label}
          </option>
        ))}
      </select>
    </label>
    {/* keep existing instruction textarea, generate button, proposal summary, apply button, history */}
  </div>
) : null}
```

- [ ] **Step 7: Render Settings tab**

For `panelTab === "settings"`, render CSS and mock JSON editors:

```tsx
{panelTab === "settings" ? (
  <div className="flex min-h-0 flex-1 flex-col gap-sm">
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-xs flex items-center gap-xs">
        <span className="material-symbols-outlined text-primary text-[20px]">css</span>
        <h3 className="font-headings text-sm font-bold text-on-surface">CSS Style</h3>
      </div>
      <textarea
        value={css}
        onChange={(event) => onCssChange(event.target.value)}
        className="min-h-[180px] flex-1 rounded border border-outline-variant bg-slate-900 p-sm font-mono text-xs text-slate-100 focus:border-primary focus:outline-none"
      />
    </div>
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-xs flex items-center justify-between">
        <div className="flex items-center gap-xs">
          <span className="material-symbols-outlined text-primary text-[20px]">data_object</span>
          <h3 className="font-headings text-sm font-bold text-on-surface">Mock Preview Data</h3>
        </div>
        {mockDataError ? <span className="text-[10px] font-mono text-error">Error</span> : null}
      </div>
      <textarea
        value={mockDataJson}
        onChange={(event) => onMockDataJsonChange(event.target.value)}
        className={`min-h-[180px] flex-1 rounded border bg-slate-900 p-sm font-mono text-xs text-slate-100 focus:outline-none ${
          mockDataError ? "border-error focus:border-error" : "border-outline-variant focus:border-primary"
        }`}
      />
      {mockDataError ? <p className="mt-xs text-[10px] text-error">{mockDataError}</p> : null}
    </div>
  </div>
) : null}
```

- [ ] **Step 8: Update parent page usage**

In `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`, replace the right panel body with one full-height `AiProposalPanel`:

```tsx
<section className="col-span-3 border-l border-outline-variant flex flex-col bg-surface overflow-hidden h-full">
  <AiProposalPanel
    templateId={isEditMode && id ? id : null}
    html={html}
    css={css}
    mockDataJson={mockDataJson}
    mockDataError={mockDataError}
    onCssChange={setCss}
    onMockDataJsonChange={(value) => {
      setMockDataJson(value);
      try {
        if (value.trim()) {
          JSON.parse(value);
          setMockDataError(null);
        } else {
          setMockDataError(null);
        }
      } catch (err) {
        setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
      }
    }}
    onApply={handleApplyAiProposal}
  />
</section>
```

Remove the old separate CSS Styles and Mock Data sections from the parent.

- [ ] **Step 9: Run frontend build**

Run from `frontend/`:

```powershell
rtk npm run build
```

Expected: PASS.

- [ ] **Step 10: Commit**

```powershell
rtk git add frontend/src/pages/content/components/AiProposalPanel.tsx frontend/src/pages/content/HtmlTemplateCreatePage.tsx
rtk git commit -m "feat: add AI chat settings panel"
```

---

### Task 7: Full Verification and Manual UAT Notes

**Files:**
- Modify if needed: `docs/superpowers/specs/2026-07-15-ai-improve-models-and-panel-design.md` only if implementation uncovers a spec correction.

**Interfaces:**
- Consumes: completed Tasks 1-6.
- Produces: verified implementation ready for review.

- [ ] **Step 1: Run backend focused tests**

Run:

```powershell
rtk pytest backend/tests/test_ai_model_catalog.py backend/tests/test_template_ai_proposals.py -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run from `frontend/`:

```powershell
rtk npm run build
```

Expected: PASS.

- [ ] **Step 3: Inspect changed files**

Run:

```powershell
rtk git diff --stat
rtk git diff -- backend/app/services/ai_model_catalog.py backend/app/api/ai_models.py backend/app/api/template_ai_proposals.py frontend/src/pages/content/components/AiProposalPanel.tsx
```

Expected: changes are scoped to model catalog, proposal model selection, right panel UI, and env/docs.

- [ ] **Step 4: Manual UAT with Gemini**

Set `.env` locally:

```env
AI_REQUESTS_ENABLED=true
AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1
GEMINI_API_KEY=<local-key>
```

Restart backend:

```powershell
rtk docker compose up -d --build backend
```

Expected: `AI Chat` can generate a valid proposal with Gemini and apply it.

- [ ] **Step 5: Manual UAT with Groq**

Set `.env` locally:

```env
AI_REQUESTS_ENABLED=true
AI_DEFAULT_MODEL=groq/llama-3.1-8b-instant
GROQ_API_KEY=<local-key>
```

Restart backend:

```powershell
rtk docker compose up -d --build backend
```

Expected: selecting Groq in `AI Chat` can generate a proposal or returns a provider JSON/validation failure without crashing.

- [ ] **Step 6: Manual UAT with Ollama**

Run Ollama outside Compose and confirm it listens on `http://localhost:11434`. Set:

```env
AI_REQUESTS_ENABLED=true
AI_DEFAULT_MODEL=ollama/llama3.1
OLLAMA_API_BASE=http://host.docker.internal:11434
```

Restart backend:

```powershell
rtk docker compose up -d --build backend
```

Expected: selecting Ollama in `AI Chat` reaches the local Ollama instance. If the model is not pulled, the UI shows a failed proposal with provider error text.

- [ ] **Step 7: Final commit if any verification-only changes were made**

```powershell
rtk git add docs/superpowers/specs/2026-07-15-ai-improve-models-and-panel-design.md
rtk git commit -m "docs: clarify AI Improve verification"
```

Skip this step if no verification-only docs changed.

---

## Self-Review

Spec coverage:

- Backend model catalog: Task 1.
- Authenticated model endpoint: Task 2.
- Proposal request selected model validation: Task 3.
- Gemini/Groq/Ollama env and Compose pass-through: Task 4.
- Frontend API client: Task 5.
- `AI Chat` and `Settings` tabs with localStorage model selection: Task 6.
- Backend/frontend/manual verification: Task 7.

Placeholder scan:

- No placeholder-style plan steps are intentionally left.

Type consistency:

- `AiModelOption.id`, `provider`, `label`, and `requires` match backend JSON and frontend TypeScript.
- `TemplateAiProposalCreatePayload.model` matches backend `HtmlTemplateAiProposalCreate.model`.
- `resolve_ai_model(settings, requested_model)` returns an `AiModelOption` consumed by proposal creation.
