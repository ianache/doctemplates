# Task 1: Backend AI Model Catalog

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

The label helper must satisfy the test expectation: `gemini/gemini-2.0-flash` must produce label `Gemini 2.0 Flash`, not `Gemini Gemini 2.0 Flash`.

## Files

- Create: `backend/app/services/ai_model_catalog.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_ai_model_catalog.py`

## Interfaces

- Produces: `AiModelOption`, `AiModelCatalog`, `build_ai_model_catalog(settings)`, `resolve_ai_model(settings, requested_model)`, `is_provider_configured(settings, option)`.
- Consumes: `settings.ai_allowed_models`, `settings.ai_default_model`, `settings.ai_provider_model`, `settings.gemini_api_key`, `settings.groq_api_key`, `settings.ollama_api_base`.

## Steps

1. Add `backend/tests/test_ai_model_catalog.py` with tests for:
   - parsing Gemini/Groq/Ollama allowlist;
   - default model fallback;
   - non-allowlisted model rejection;
   - empty allowlist resolution error;
   - default model outside allowlist configuration error.
2. Run `rtk pytest backend/tests/test_ai_model_catalog.py -q` and verify it fails because the service does not exist.
3. Extend `backend/app/config.py` with:
   - `ai_default_model: str = "gpt-4o-mini"`
   - `ai_allowed_models: str = "gpt-4o-mini"`
   - `gemini_api_key: str = ""`
   - `groq_api_key: str = ""`
   - `ollama_api_base: str = "http://localhost:11434"`
4. Create `backend/app/services/ai_model_catalog.py` implementing the interfaces above.
5. Run `rtk pytest backend/tests/test_ai_model_catalog.py -q` and verify it passes.

## Required Test Code

Use this as the behavioral baseline, adjusting only if necessary for existing fixtures/import patterns:

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

## Report

Write full report to `.superpowers/sdd/ai-improve-models-task-1-report.md` and return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created: none, because `.git` is read-only
- One-line test summary
- Concerns, if any
- Report file path
