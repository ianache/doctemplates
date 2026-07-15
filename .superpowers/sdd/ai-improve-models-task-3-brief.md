# Task 3: Selected Model Validation in Proposal Creation

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

- Modify: `backend/app/schemas/template_ai_proposal.py`
- Modify: `backend/app/api/template_ai_proposals.py`
- Modify: `backend/app/services/template_ai_agent.py`
- Test: `backend/tests/test_template_ai_proposals.py`

## Interfaces

- Consumes: `resolve_ai_model(settings, payload.model)` and `is_provider_configured(settings, option)`.
- Produces: proposal creation that accepts optional `model`, validates allowlist, checks provider configuration, and stores selected model.

## Dependencies

Tasks 1-2 are complete. Use:

- `backend/app/services/ai_model_catalog.py`
- `resolve_ai_model(settings, requested_model)`
- `is_provider_configured(settings, option)`

## Steps

1. Add tests to `backend/tests/test_template_ai_proposals.py` for:
   - selected model passed to `TemplateAiAgent`;
   - disallowed model returns `400`;
   - unconfigured provider returns a persisted failed proposal with `Provider is not configured.`
2. Extend `HtmlTemplateAiProposalCreate` with `model: str | None = None`.
3. Add `provider_configuration_failed()` to `TemplateAiAgent`, returning `_failed("Provider is not configured.")`.
4. In `create_ai_proposal`, resolve/validate selected model before creating the agent.
5. If provider is unconfigured, create failed result without calling LiteLLM.
6. Persist result as existing code does.
7. Run from `backend/`:
   - `.venv/Scripts/python.exe -m pytest tests/test_template_ai_proposals.py tests/test_ai_model_catalog.py -q`

## Required Tests

Use these as the behavioral baseline, adapting imports only if existing patterns require:

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

## Report

Write full report to `.superpowers/sdd/ai-improve-models-task-3-report.md` and return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created: none, because `.git` is read-only
- One-line test summary
- Concerns, if any
- Report file path
