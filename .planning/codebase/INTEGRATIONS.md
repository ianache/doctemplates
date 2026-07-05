# External Integrations

**Analysis Date:** 2026-07-05

## Status

**Currently:** Not integrated. Project is in initial phase (`main.py` contains only a stub function). The following integrations are available via dependencies but not yet implemented in code.

## APIs & External Services

**LLM Providers (Optional - via headroom-ai[all]):**
- Anthropic API - Available via `anthropic` package
  - SDK: `anthropic` Python package
  - Use: Claude models for document processing and AI features
  - Auth: Expects `ANTHROPIC_API_KEY` environment variable
- OpenAI API - Available via `openai` package
  - SDK: `openai` Python package
  - Auth: Expects `OPENAI_API_KEY` environment variable

**HuggingFace (Optional - via headroom-ai[all]):**
- HuggingFace Hub - Model hosting and management
  - SDK: `huggingface-hub`, `datasets`, `transformers` packages
  - Auth: Expects `HF_TOKEN` environment variable (optional, for private models)

**File Type Detection:**
- Magika (local) - No external API, uses local model for file type detection

## Data Storage

**Databases:**
- SQLite with vector extension available
  - Package: `sqlite-vec` for vector operations
  - Use: Document template storage, metadata indexing, semantic search
  - Connection: Local file-based, no remote database required

**File Storage:**
- Local filesystem only - No cloud storage integration configured
- Expected use: Store static PDF files in storage/repositorio/ (per PRD)
- Documents would be composed server-side

**Caching:**
- None currently configured

## Authentication & Identity

**Auth Provider:**
- Custom (none currently implemented)
- Potential future integration: The BFF endpoints in PRD suggest JWT or session-based auth for template management
- Note: PRD mentions "usuarios operativos de DocManagement" but no auth mechanism specified yet

## Monitoring & Observability

**Error Tracking:**
- None currently integrated
- Available via OpenTelemetry SDK if configured

**Logs:**
- Console/stdout logging via rich library
- OpenTelemetry logging available for structured logging
- Watchdog available for file system event monitoring

## CI/CD & Deployment

**Hosting:**
- Not configured - likely Python-on-host or containerized deployment
- Uvicorn available for running as ASGI web service

**CI Pipeline:**
- CodeGraph initialized (`.codegraph/` present) - local code analysis tooling
- GSD (Get-Shit-Done) initialized (`.codex/` present) - local development workflow
- No GitHub Actions, GitLab CI, or other remote CI/CD detected

## Environment Configuration

**Required env vars:**
- None currently enforced (no code reads env vars)
- Planned env vars (if implementing integrations):
  - `ANTHROPIC_API_KEY` - For Claude API access
  - `OPENAI_API_KEY` - For OpenAI API access
  - `HF_TOKEN` - For HuggingFace private model access

**Secrets location:**
- Not configured
- Should be added: `.env` file (not committed) for local development
- Should use: `python-dotenv` or pydantic-settings for secrets management

## Webhooks & Callbacks

**Incoming:**
- Not implemented
- PRD specifies `POST /api/bff/maquetas` and `POST /api/bff/maquetas/previsualizar` endpoints that would be implemented in FastAPI if built

**Outgoing:**
- None

## PDF Processing

**Not yet implemented:**
- PRD specifies need for PDF manipulation library
  - Recommended in PRD: PyPDF2 (Python) or pdf-lib (Node)
  - Neither currently in dependencies - will need to be added

## Document Template System

**Per PRD architecture:**
- Server-side document composition required:
  1. Retrieve static PDFs from storage/repositorio/ path
  2. Replace tokens in HTML templates with data from operational systems
  3. Merge pages in order using PDF manipulation library
  4. Return combined PDF as binary response

**Current readiness:** Dependencies available (FastAPI, Jinja2 for templating), but PDF library missing

---

*Integration audit: 2026-07-05*
