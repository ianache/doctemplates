# Task 1: Backend AI Model Catalog Report

## Status

Implemented with verification concern: the focused test suite could not execute because the available Windows Python runtime is unavailable in this environment.

## Changes

- Added the required AI catalog settings to `backend/app/config.py`:
  - `ai_default_model = "gpt-4o-mini"`
  - `ai_allowed_models = "gpt-4o-mini"`
  - `gemini_api_key = ""`
  - `groq_api_key = ""`
  - `ollama_api_base = "http://localhost:11434"`
- Added `backend/app/services/ai_model_catalog.py` with:
  - frozen `AiModelOption` and `AiModelCatalog` dataclasses;
  - comma-separated allowlist parsing;
  - provider and required-configuration mapping;
  - provider-aware display labels;
  - default-model validation and resolution;
  - allowlist rejection and empty-catalog errors;
  - provider-configuration checks.
- Added `backend/tests/test_ai_model_catalog.py` covering the five required behaviors.

The label logic handles `gemini/gemini-2.0-flash` as `Gemini 2.0 Flash`, without repeating `Gemini`.

## Verification

Required command attempted:

```text
rtk pytest backend/tests/test_ai_model_catalog.py -q
```

It could not start successfully in this environment. Direct `python -m pytest` failed because `python.exe` reported that a required Windows logon session no longer existed. `py -3.12 -m pytest` reported that no suitable Python runtime was installed. `rtk uv run pytest ...` was blocked by access denied while opening the local uv cache.

The implementation and test files were self-reviewed after editing. No Git staging or commits were attempted.

Controller follow-up verification succeeded with the backend virtualenv from the backend working directory:

```text
.venv/Scripts/python.exe -m pytest tests/test_ai_model_catalog.py -q
..... [100%]
5 passed, 2 warnings in 1.56s
```

Warnings were:

- `StarletteDeprecationWarning` from FastAPI/TestClient dependency path.
- `PytestCacheWarning` because this environment cannot write `.pytest_cache`.

## Changed Files

- `backend/app/config.py`
- `backend/app/services/ai_model_catalog.py`
- `backend/tests/test_ai_model_catalog.py`
- `.superpowers/sdd/ai-improve-models-task-1-report.md`

## Review Finding Fix

- Added `openai_api_key` and `anthropic_api_key` settings with empty-string defaults.
- Updated `is_provider_configured` to evaluate every declared requirement, including OpenAI and Anthropic credentials.
- Preserved unknown-provider behavior: providers with no required configuration are considered configured.
- Added focused tests covering configured and missing OpenAI/Anthropic keys and unknown providers without required configuration.

Verification from `backend/`:

```text
.venv/Scripts/python.exe -m pytest tests/test_ai_model_catalog.py -q
........                                                                 [100%]
8 passed, 2 warnings in 0.62s
```

Warnings remain limited to the existing Starlette/httpx deprecation and an environment permission error writing `.pytest_cache`.
