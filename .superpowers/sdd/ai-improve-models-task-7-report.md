# Task 7: Full Verification and Manual UAT Notes

## Status

DONE_WITH_CONCERNS

## Automated Verification

Backend focused tests were run from `backend/`:

```text
.venv/Scripts/python.exe -m pytest tests/test_ai_model_catalog.py tests/test_template_ai_proposals.py -q
```

Result:

```text
29 passed, 3 warnings in 21.15s
```

Warnings:

- Existing Starlette/FastAPI TestClient deprecation warning.
- Existing `datetime.utcnow()` deprecation warning in proposal apply endpoint.
- Environment-specific `.pytest_cache` permission warning.

Frontend production build was run from `frontend/`:

```text
rtk npm run build
```

Result:

```text
tsc -b && vite build
✓ built in 4.59s
```

Warnings:

- Existing/non-blocking Vite chunk-size warning.
- Vite plugin timing advisory.

## Scope Check

Implemented files for this phase:

- `backend/app/services/ai_model_catalog.py`
- `backend/app/api/ai_models.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/schemas/template_ai_proposal.py`
- `backend/app/api/template_ai_proposals.py`
- `backend/app/services/template_ai_agent.py`
- `backend/tests/test_ai_model_catalog.py`
- `backend/tests/test_template_ai_proposals.py`
- `frontend/src/lib/content.ts`
- `frontend/src/pages/content/components/AiProposalPanel.tsx`
- `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`
- `.env.example`
- `docker-compose.yml`

## Manual UAT Notes

Provider-backed manual UAT was not run because this environment does not include real Gemini, Groq, or Ollama credentials/services.

Recommended manual checks:

1. Configure Gemini:

```env
AI_REQUESTS_ENABLED=true
AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1
GEMINI_API_KEY=<local-key>
```

2. Configure Groq:

```env
AI_REQUESTS_ENABLED=true
AI_DEFAULT_MODEL=groq/llama-3.1-8b-instant
GROQ_API_KEY=<local-key>
```

3. Configure Ollama:

```env
AI_REQUESTS_ENABLED=true
AI_DEFAULT_MODEL=ollama/llama3.1
OLLAMA_API_BASE=http://host.docker.internal:11434
```

Restart backend after each config change:

```text
rtk docker compose up -d --build backend
```

## Concerns

- No Git commits were created because `.git/index.lock` cannot be created in this environment.
- `git status` shows some files as delete/untracked pairs because prior uncommitted work was already in a mixed index state. The working tree files exist and were used for build/test verification.
- Provider-backed manual UAT remains pending.
