# Task 4: Environment and Docker Provider Configuration

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

- Modify: `.env.example`
- Modify: `docker-compose.yml`

## Interfaces

- Consumes: backend settings added in Tasks 1-3.
- Produces: documented and container-passed `AI_DEFAULT_MODEL`, `AI_ALLOWED_MODELS`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OLLAMA_API_BASE`.

## Steps

1. Update `.env.example` AI block so it includes:
   - `AI_REQUESTS_ENABLED=false`
   - `AI_DEFAULT_MODEL=gemini/gemini-2.0-flash`
   - `AI_PROVIDER_MODEL=gpt-4o-mini`
   - `AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1`
   - `AI_REQUEST_TIMEOUT_SECONDS=30`
   - `AI_MAX_INPUT_CHARS=20000`
   - `AI_MAX_OUTPUT_TOKENS=2000`
   - commented `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OLLAMA_API_BASE=http://host.docker.internal:11434`
2. Update `docker-compose.yml` backend service environment to pass through:
   - `AI_REQUESTS_ENABLED`
   - `AI_DEFAULT_MODEL`
   - `AI_PROVIDER_MODEL`
   - `AI_ALLOWED_MODELS`
   - `AI_REQUEST_TIMEOUT_SECONDS`
   - `AI_MAX_INPUT_CHARS`
   - `AI_MAX_OUTPUT_TOKENS`
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `OLLAMA_API_BASE`
3. Do not add an Ollama service.
4. Verify with:
   - `rtk proxy powershell -NoProfile -Command "Select-String -Path .env.example,docker-compose.yml -Pattern 'GEMINI_API_KEY','GROQ_API_KEY','OLLAMA_API_BASE','AI_ALLOWED_MODELS'"`

## Report

Write full report to `.superpowers/sdd/ai-improve-models-task-4-report.md` and return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created: none, because `.git` is read-only
- One-line verification summary
- Concerns, if any
- Report file path
