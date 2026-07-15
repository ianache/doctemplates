# Task 2: Backend Model Catalog API

Plan file: `docs/superpowers/plans/2026-07-15-ai-improve-models-and-panel.md`

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

## Execution Adjustment

Do not attempt `git add` or `git commit`. This environment cannot create `.git/index.lock`. Report changed files instead.

## Files

- Create: `backend/app/api/ai_models.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ai_model_catalog.py`

## Interfaces

- Consumes: `build_ai_model_catalog(settings)`.
- Produces: authenticated `GET /api/content/ai-models` with `enabled`, `default_model`, and `models`.

## Dependencies

Task 1 is complete. Use:

- `backend/app/services/ai_model_catalog.py`
- `build_ai_model_catalog(settings)`
- existing auth dependency pattern from other API modules.

## Steps

1. Add API test `test_get_ai_models_returns_catalog` to `backend/tests/test_ai_model_catalog.py`.
2. Run the single test and verify it fails before implementation if practical.
3. Create `backend/app/api/ai_models.py` with:
   - `router = APIRouter(prefix="/api/content/ai-models", tags=["ai-models"])`
   - `AiModelOptionOut`
   - `AiModelCatalogOut`
   - authenticated `get_ai_models(user: User = Depends(get_current_user))`
4. Register `ai_models.router` in `backend/app/main.py`.
5. Run:
   - from `backend/`: `.venv/Scripts/python.exe -m pytest tests/test_ai_model_catalog.py -q`

## Required API Test

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

## Report

Write full report to `.superpowers/sdd/ai-improve-models-task-2-report.md` and return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created: none, because `.git` is read-only
- One-line test summary
- Concerns, if any
- Report file path
