# Phase 14: Async PDF Generation Jobs with Celery/Redis and Job UI - Research

**Researched:** 2026-07-13
**Domain:** FastAPI async job orchestration, Celery/Redis workers, issuance lifecycle persistence, BFF/frontend job UI
**Confidence:** HIGH for local code boundaries; MEDIUM for package legitimacy because `slopcheck` could not be run

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use Celery for task execution and Redis for broker/result backend.
- Postgres remains the source of truth for job status and issuance data.
- The worker receives only `issuance_id`, never bearer tokens or arbitrary client payloads.
- The backend authenticates and validates the request before enqueueing.
- If a design is still `draft`, the backend validates and activates it before enqueueing so the worker uses a stable version.
- Extend `DocumentIssuance.status` to exact values: `queued`, `processing`, `success`, `failure`.
- Allow `DocumentIssuance.storage_key` to be nullable while status is not `success`.
- Add nullable job fields: `celery_task_id`, `error_message`, `queued_at`, `started_at`, `completed_at`, and `retry_count` default `0`.
- Persist `input_data`, `metadata_values`, `user_id`, and `design_version_id` at enqueue time.
- Create `backend/app/workers/celery_app.py` for Celery configuration.
- Create `backend/app/workers/document_generation.py` with `generate_document_pdf(issuance_id: str)`.
- The task must be idempotent: if an issuance is no longer `queued`, it exits without regenerating.
- On success, store the PDF via `StorageProvider`, set `storage_key`, mark `success`, and append a generation tracelog.
- On failure, mark `failure`, truncate and persist `error_message`, set `completed_at`, and append an error trace event if supported by the existing trace model.
- `POST /api/document-designs/{design_id}/generate` returns `202 Accepted` with the queued issuance.
- `GET /api/issuances/{issuance_id}` returns current job status and error metadata.
- `GET /api/issuances/{issuance_id}/download` returns `409 Conflict` for `queued`, `processing`, and `failure`.
- Existing preview remains synchronous for this phase.
- The BFF must forward the new async contract and expose status fields to the frontend without hiding backend states.
- The generated-documents experience from Phase 9 remains the user-facing base: searchable issuance list, detail page, preview/download/share actions, and audit timeline.
- Add UI affordances for document-creation jobs: status filters/labels, polling, disabled actions before readiness, failure error display, and a job-focused management surface in the existing generated-documents/document-creation flow.
- Polling baseline: every 2 seconds for the first 60 seconds, then every 5 seconds; stop at `success` or `failure`.
- Add `redis` service using `redis:7-alpine`.
- Add `worker` service using the backend image and `uv run celery -A app.workers.celery_app worker --loglevel=info`.
- Backend and worker must share local issuance storage volume when `STORAGE_PROVIDER_TYPE=local`.

### the agent's Discretion
- Exact frontend placement for the job management surface, as long as it is discoverable from the generated-documents/document-creation workflow.
- Whether to expose manual refresh in addition to polling.
- Exact retry classification in the first version, provided functional errors become `failure` and transient infrastructure errors are safe for Celery retries.

### Deferred Ideas (OUT OF SCOPE)
- WebSockets/SSE.
- Manual retry from UI.
- Job cancellation.
- Priority queues.
- Percentage progress bars.
- Async preview.
- Stuck-job recovery scanner.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASYNC-01 | Generation endpoint enqueues work and returns `202 Accepted` with `queued` issuance. | Current sync endpoint is isolated in `backend/app/api/document_designs.py`; replace render/save block with issuance creation and Celery enqueue. [VERIFIED: codebase grep/read] |
| ASYNC-02 | Celery worker processes queued issuances and updates lifecycle states through `success` or `failure`. | `generate_composed_pdf(...)` is reusable from worker if the worker opens its own DB session and gets `StorageProvider`. [VERIFIED: codebase read] |
| ASYNC-03 | `document_issuances` persists task id, timestamps, nullable storage key, retry count, and error message. | Current model and migrations have non-null `storage_key` and status constraint only for `success|failure`; needs Alembic migration. [VERIFIED: codebase read] |
| ASYNC-04 | Download/share/preview-facing endpoints handle non-terminal and failed states without file assumptions. | `issuances.py` currently calls storage download helpers without status checks; all three endpoints need guards. [VERIFIED: codebase read] |
| ASYNC-05 | Docker Compose runs backend, Redis, worker, Postgres, storage, BFF, and frontend coherently. | Compose currently has backend/BFF/frontend/Postgres/Keycloak/MinIO and only backend mounts `content-storage`; add Redis and worker with shared volume. [VERIFIED: docker-compose.yml] |
| ASYNC-06 | Backend tests cover enqueue, worker success, worker failure, and download-before-complete conflicts. | Existing tests already cover generation, issuance library, tracelogs, and storage providers; extend those suites. [VERIFIED: backend/tests grep/read] |
| JOBUI-01 | BFF and frontend support async generation status polling and terminal-state handling. | BFF is a transparent streaming proxy; frontend types/pages need async statuses and polling. [VERIFIED: bff/app/proxy/router.py; frontend reads] |
| JOBUI-02 | UI provides job management visibility for queued, processing, success, and failure issuances using Phase 9 patterns. | `DocumentLibraryPage`, `DocumentIssuanceDetailPage`, and `IssuanceProperties` are the extension points. [VERIFIED: frontend reads] |
| JOBUI-03 | UI disables unavailable actions for unfinished/failed jobs and displays failure errors. | Current detail page always attempts preview/download/share; status-based disabling/error display is needed. [VERIFIED: frontend read] |
</phase_requirements>

## Summary

Phase 14 should be planned as an incremental conversion of the existing synchronous generation path into a durable issuance job lifecycle. The current flow is compact: `generate_document()` validates/activates the design, validates metadata, calls `generate_composed_pdf(...)`, saves bytes through `StorageProvider`, creates `DocumentIssuance(status="success")`, appends a `generation` tracelog, commits, and returns `201`. [VERIFIED: codebase read]

The safest implementation is to preserve the domain contract around `document_issuances`: create the issuance row before enqueue, store request data at enqueue time, and let the worker own only rendering/storage/final status. Redis should remain queue infrastructure, not user-visible state. [CITED: .planning/phases/14-implementar-scopes-prd4-md/14-CONTEXT.md]

**Primary recommendation:** split the phase into four waves: backend schema/API contract, Celery worker/compose runtime, BFF/frontend job UI, then focused integration tests and Docker smoke verification. [VERIFIED: codebase analysis]

## Project Constraints (from AGENTS.md)

- The root `AGENTS.md` file was not present on disk; the prompt supplied AGENTS instructions. [VERIFIED: command result]
- Shell commands should be prefixed with `rtk`; if debugging requires raw execution, use raw only deliberately. [CITED: prompt AGENTS.md]
- Do not modify application code during this research task. [CITED: user request]
- Write research output to `.planning/phases/14-implementar-scopes-prd4-md/14-RESEARCH.md`. [CITED: user request]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Request authentication and enqueue validation | API / Backend | BFF | Backend already owns auth dependencies, design activation, schema validation, metadata validation, and issuance persistence. [VERIFIED: codebase read] |
| Async PDF rendering | Worker / Backend process | Redis broker | Worker should reuse backend services and DB models; Redis only delivers task messages. [CITED: PRD4.md] |
| Job lifecycle source of truth | Database / Storage | API / Backend | `document_issuances` is the persisted domain record; final PDFs live in configured storage. [VERIFIED: codebase read] |
| User-visible job management | Browser / Client | BFF/API | Existing generated-documents pages render filters, detail, preview, actions, and timeline. [VERIFIED: frontend reads] |
| Authenticated proxying | BFF | API / Backend | BFF injects bearer tokens and streams backend responses without custom issuance business logic. [VERIFIED: bff/app/proxy/router.py] |
| Local file sharing | Docker runtime / Storage | Backend and worker | Local `StorageProvider` resolves issuance keys under `issuance_storage_root`; backend and worker need the same mounted volume. [VERIFIED: storage code and compose] |

## Current Synchronous Generation Flow

1. `backend/app/api/document_designs.py::generate_document` receives `POST /api/document-designs/{design_id}/generate`, loads the design via `_require_design`, activates drafts via `_activate_design`, splits `payload` into `data` and `metadata`, validates metadata via `validate_metadata_values`, calls `generate_composed_pdf(...)`, saves the PDF through `storage_provider.save(..., category="issuances")`, creates `DocumentIssuance(status="success")`, appends `DocumentTracelog(event_type="generation")`, commits, and returns `201`. [VERIFIED: codebase read]
2. `backend/app/services/pdf_generator.py::generate_composed_pdf` validates/coerces payload fields, loads template/static PDF content, renders HTML pages through Jinja/xhtml2pdf, reads static PDFs through `storage_provider.get_stream(..., "static_pdfs")`, merges with `pypdf.PdfWriter`, and returns bytes. [VERIFIED: codebase read]
3. `backend/app/services/storage/base.py`, `local.py`, `s3.py`, and `backend/app/dependencies.py` provide the Phase 13 `StorageProvider` abstraction. Local storage returns relative keys and S3 cleans absolute paths to object keys. [VERIFIED: codebase read]
4. `backend/app/models/document_issuance.py` currently defines `ISSUANCE_STATUSES = ("success", "failure")`, a non-null `storage_key: Mapped[str]`, and a backward-compatible `file_path` property that resolves local paths. [VERIFIED: codebase read]
5. `backend/app/schemas/document_issuance.py` currently exposes `DocumentIssuanceOut.file_path: str` and library/detail schemas without task fields or error metadata. [VERIFIED: codebase read]
6. `backend/app/api/issuances.py` listing filters `status: Literal["success", "failure"]`; detail returns library metadata; preview/download/public download call storage helpers without status guards; share always creates a signed public URL. [VERIFIED: codebase read]
7. Alembic history: `0007_document_issuances.py` created `file_path` non-null, `0008_document_tracelogs.py` added the `success|failure` status check, and `0012_storage_decoupling.py` renamed `file_path` to `storage_key` and extracted base filenames. [VERIFIED: alembic reads]

## Existing Phase 9 UI/BFF Patterns To Extend

| Pattern | Current Files | Extension Needed |
|---------|---------------|------------------|
| Transparent authenticated proxy | `bff/app/proxy/router.py`, `bff/app/main.py` | Keep BFF mostly pass-through; ensure 202 JSON and 409 JSON errors stream correctly. BFF timeout is 30 seconds, so generation must return quickly. [VERIFIED: codebase read] |
| Library filter/query model | `frontend/src/lib/documentIssuances.ts`, `frontend/src/pages/document-issuances/DocumentLibraryPage.tsx` | Add `queued` and `processing` to `DocumentIssuanceStatus`, status filter options, labels, styles, and optional auto-refresh when list contains non-terminal jobs. [VERIFIED: frontend reads] |
| Detail page PDF preview | `frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx` | Only request `detail.preview_url` when `status === "success"`; show queued/processing/failure state otherwise. [VERIFIED: frontend read] |
| Download/share actions | `DocumentIssuanceDetailPage.tsx`, `frontend/src/lib/documentIssuances.ts` | Disable download and share unless `success`; display backend `409`/`error_message` if action is attempted by stale UI. [VERIFIED: frontend read] |
| Properties side panel | `frontend/src/components/molecules/IssuanceProperties.tsx` | Add queued/started/completed timestamps, retry count, task id if acceptable, and failure error text. [VERIFIED: frontend read] |
| Audit timeline | `DocumentIssuanceDetailPage.tsx`, `backend/app/api/issuances.py`, `backend/app/models/document_tracelog.py` | Keep generation/download/share events; if adding failure events, update DB check constraint and frontend label map. Otherwise store worker failure only on issuance error fields. [VERIFIED: codebase read] |
| Document design preview flow | `frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx`, `frontend/src/lib/documentDesigns.ts` | Preview remains synchronous. If a generate button is added here, it should call new async generate API and navigate to `/document-issuances/{id}`. Current frontend library has preview but no generation helper. [VERIFIED: frontend grep/read] |

## Standard Stack

### Core

| Library / Runtime | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| `celery[redis]` | PyPI latest `5.6.3` | Python distributed task queue plus Redis transport dependency bundle. [VERIFIED: official Celery docs + PyPI JSON] | Official Celery docs document installing Redis support with `celery[redis]` and configuring Redis broker/result URLs. [CITED: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html] |
| Redis Docker image | `redis:7-alpine` locked by phase context | Broker/result backend service. [CITED: CONTEXT.md] | Docker Hub marks `redis` as a Docker Official Image and lists `7-alpine` tags. [CITED: https://hub.docker.com/_/redis] |
| Postgres | existing `postgres:16` in compose | Source of truth for job lifecycle and issuance metadata. [VERIFIED: docker-compose.yml] | Required by existing SQLAlchemy/Alembic app and phase decision. [CITED: CONTEXT.md] |
| Existing `StorageProvider` | local/S3 abstraction from Phase 13 | Store final PDFs from worker. [VERIFIED: codebase read] | Avoids duplicating local/S3 storage logic and keeps MinIO/S3 support. [VERIFIED: codebase read] |

### Supporting

| Library / Runtime | Version | Purpose | When to Use |
|-------------------|---------|---------|-------------|
| `redis` Python package | PyPI latest `8.0.1` | Redis client dependency used by Celery Redis transport. [VERIFIED: PyPI JSON] | Prefer indirect installation via `celery[redis]`; direct pin only if lock resolution requires it. [CITED: Celery Redis docs] |
| Existing FastAPI/SQLAlchemy/Alembic | versions in `backend/pyproject.toml` | API endpoints, DB model, migration. [VERIFIED: backend/pyproject.toml] | Extend current patterns rather than introducing a second persistence layer. [VERIFIED: codebase read] |
| Existing React/Vite frontend | versions in `frontend/package.json` | Generated-documents job UI. [VERIFIED: frontend/package.json] | Extend existing library/detail routes and components. [VERIFIED: frontend reads] |

**Installation:**

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv add 'celery[redis]>=5.6.3'"
```

## Package Legitimacy Audit

`slopcheck` installation was rejected by the sandbox approval reviewer because it would mutate the local Python environment during a research-only request. [VERIFIED: command result] Therefore the planner must add a human verification checkpoint before installing new packages. Package names below were discovered through official Celery documentation or PyPI JSON, but `slopcheck` verdicts are unavailable. [VERIFIED: official docs/PyPI; ASSUMED: legitimacy beyond source checks]

| Package | Registry | Current Version | Source Repo / Authority | slopcheck | Disposition |
|---------|----------|-----------------|-------------------------|-----------|-------------|
| `celery[redis]` | PyPI | `5.6.3` | Official Celery docs and PyPI JSON. [VERIFIED: official docs + PyPI JSON] | unavailable | Approved with `checkpoint:human-verify` before install |
| `redis` | PyPI | `8.0.1` | PyPI JSON; used transitively by Celery Redis extra. [VERIFIED: PyPI JSON; CITED: Celery Redis docs] | unavailable | Prefer transitive via `celery[redis]`; checkpoint if directly pinned |

**Packages removed due to slopcheck [SLOP] verdict:** none; slopcheck unavailable.
**Packages flagged as suspicious [SUS]:** none by tool; tool unavailable, so gate all installs.

## Architecture Patterns

### System Architecture Diagram

```text
Browser UI
  | POST generate / GET issuance status / GET download-share
  v
BFF catch-all proxy
  | injects bearer token, streams backend response
  v
FastAPI backend
  | validate auth, design, payload, metadata
  | activate draft if needed
  | INSERT document_issuances(status="queued", storage_key=NULL, input_data, metadata_values)
  | enqueue Celery task(generate_document_pdf, issuance_id)
  v
Redis broker/result backend
  | delivers task; may redeliver if unacked
  v
Celery worker
  | opens DB session
  | load issuance + design/pages/type
  | if status != queued: exit idempotently
  | set processing/started_at
  | generate_composed_pdf(...)
  | save via StorageProvider(category="issuances")
  | set success/storage_key/completed_at OR failure/error_message/completed_at
  v
Postgres document_issuances + document_tracelogs
  |
  v
StorageProvider local/S3 final PDF
```

### Recommended Project Structure

```text
backend/app/
├── api/
│   ├── document_designs.py      # enqueue API, no heavy render in request
│   └── issuances.py             # status-aware detail/preview/download/share
├── models/
│   └── document_issuance.py     # lifecycle fields and nullable storage_key
├── schemas/
│   └── document_issuance.py     # status/task/error/timestamp fields
├── workers/
│   ├── celery_app.py            # Celery instance/config/imports
│   └── document_generation.py   # generate_document_pdf task
└── services/
    ├── pdf_generator.py         # reused render/merge implementation
    └── storage/                 # reused provider abstraction

frontend/src/
├── lib/documentIssuances.ts
├── lib/documentDesigns.ts       # add async generate helper if UI generates jobs
├── pages/document-issuances/
└── components/molecules/IssuanceProperties.tsx
```

### Pattern 1: Enqueue-Then-Process

**What:** The API validates and persists an issuance first, then enqueues a worker task with only `issuance_id`. [CITED: PRD4.md]

**When to use:** Every public PDF generation request. Preview remains synchronous. [CITED: CONTEXT.md]

**Example:**

```python
# Source: PRD4.md + existing backend patterns
issuance = DocumentIssuance(
    design_version_id=design.id,
    storage_key=None,
    user_id=user.id,
    input_data=data,
    metadata_values=coerced_metadata,
    status="queued",
    queued_at=now,
)
db.add(issuance)
db.flush()
result = generate_document_pdf.delay(str(issuance.id))
issuance.celery_task_id = result.id
db.commit()
```

### Pattern 2: Idempotent Late-Ack Worker

**What:** Configure late acknowledgement and low prefetch for long PDF tasks, then make the task safe to run more than once. Celery docs state that late acknowledgment means a started task can be retried after power failure or abrupt worker kill, so the task must be idempotent. [CITED: https://docs.celeryq.dev/en/stable/userguide/optimizing.html]

**When to use:** The Phase 14 worker task should check `issuance.status == "queued"` before processing and avoid regenerating `success`/`failure` records. [CITED: CONTEXT.md]

**Example:**

```python
# Source: Celery optimizing docs + Phase 14 context
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
)
```

### Anti-Patterns to Avoid

- **Passing payloads or bearer tokens into Celery:** Persist the validated payload and user/design IDs in Postgres, then pass only `issuance_id`. [CITED: CONTEXT.md]
- **Using Redis as job history:** Redis visibility/result state is operational; user-visible lifecycle belongs in `document_issuances`. [CITED: PRD4.md]
- **Calling preview/download/share for unfinished jobs:** The current code assumes `storage_key` exists; add status guards before storage access or signing. [VERIFIED: codebase read]
- **Adding a disconnected jobs screen:** Extend the generated-documents library/detail patterns from Phase 9. [CITED: CONTEXT.md]
- **Creating a custom queue table instead of Celery:** Celery and Redis are locked decisions for this phase. [CITED: CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task delivery and worker execution | Custom polling loop or DB queue runner | Celery + Redis | Locked decision; Celery already supports Redis broker/result URLs and worker runtime. [CITED: Celery docs; CONTEXT.md] |
| Storage-specific PDF saving | New local/S3 logic in worker | Existing `StorageProvider` | Local and S3 providers already implement save/get/download by category. [VERIFIED: codebase read] |
| PDF composition | New renderer in worker | `generate_composed_pdf(...)` | Existing implementation already handles schema validation, Jinja rendering, static PDFs, and merge order. [VERIFIED: codebase read] |
| Job detail UI | New isolated page family | `DocumentLibraryPage` and `DocumentIssuanceDetailPage` | Phase 9 UI already has search, filters, detail, preview, download, share, and timeline. [VERIFIED: frontend reads] |
| Public sharing security | New token scheme | Existing HMAC signature helpers | Phase 9 share URLs already use signature verification. [VERIFIED: codebase read] |

## Recommended Plan Boundaries / Waves

### Wave 1 - Backend Model, Migration, API Contract

- Add Alembic migration after `0012_storage_decoupling.py`: update status check to `queued|processing|success|failure`, make `document_issuances.storage_key` nullable, add `celery_task_id`, `error_message`, `queued_at`, `started_at`, `completed_at`, and `retry_count`. [VERIFIED: alembic reads]
- Update `DocumentIssuance` model and schemas to make `storage_key`/`file_path` optional and expose status/timestamp/error fields. [VERIFIED: codebase read]
- Refactor `generate_document` so it validates and activates exactly as today, but creates `queued` issuance and returns `202` without calling `generate_composed_pdf`. [VERIFIED: codebase read]
- Add dependency seam for enqueueing so API tests can assert enqueue without running heavy PDF generation. [ASSUMED: recommended testability pattern]
- Add status guards to authenticated preview/download, public download, and share endpoints. Download/preview/public download should return `409` for non-success; share should either return `409` before success or explicitly never sign unfinished documents. [CITED: CONTEXT.md]

### Wave 2 - Celery Worker and Compose Runtime

- Add `celery[redis]` dependency to backend and settings for `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, and `CELERY_TASK_ALWAYS_EAGER`. [CITED: Celery docs; PRD4.md]
- Add `backend/app/workers/celery_app.py` and `backend/app/workers/document_generation.py`. [CITED: CONTEXT.md]
- Worker task opens its own SQLAlchemy session, reloads issuance/design/page/type relationships, checks idempotency, marks processing, calls `generate_composed_pdf`, saves through `get_storage_provider()`, updates success/failure fields, and appends tracelog. [CITED: CONTEXT.md; VERIFIED: reusable code paths]
- Add `redis` and `worker` services to `docker-compose.yml`; worker must receive the same DB/OIDC/storage env as backend, plus Celery URLs, and mount `content-storage:/app/.content-storage` when local storage is used. [VERIFIED: docker-compose.yml]
- Consider `worker_prefetch_multiplier=1` and `task_acks_late=True`; Celery docs explicitly tie this pattern to idempotent tasks. [CITED: Celery optimizing docs]

### Wave 3 - BFF and Frontend Job UI

- BFF likely needs no route-specific business logic because `bff/app/proxy/router.py` forwards status codes and streams response bodies; update tests only if `202`/`409` behavior needs explicit coverage. [VERIFIED: bff read]
- Update `frontend/src/lib/documentIssuances.ts` statuses to `queued | processing | success | failure`, add optional task/error/timestamp fields, and ensure error parsing handles backend `409` detail bodies. [VERIFIED: frontend read]
- Update library status filter and table labels/styles in `DocumentLibraryPage.tsx`; optionally poll the list if any visible item is non-terminal. [VERIFIED: frontend read]
- Update detail page to poll `getDocumentIssuance(id)` every 2 seconds for 60 seconds, then every 5 seconds, stopping at `success` or `failure`; fetch preview and tracelogs only when appropriate. [CITED: CONTEXT.md]
- Disable or hide download/share actions until `success`; render `error_message` on `failure`. [CITED: CONTEXT.md]
- If adding document creation from the designer, add `generateDocumentDesign(...)` to `frontend/src/lib/documentDesigns.ts` and navigate from design detail to issuance detail after the `202` response. Current frontend has preview helpers but no generation helper. [VERIFIED: frontend grep/read]

### Wave 4 - Tests and Operational Verification

- Extend backend generation tests for `202` enqueue and no PDF write in request path. [VERIFIED: backend/tests read]
- Add worker tests for success, functional failure, and duplicate/redelivered task idempotency. [CITED: Celery docs; CONTEXT.md]
- Extend issuance API tests for list/detail statuses, `409` download/preview/public download/share-before-success behavior, and failure error metadata. [VERIFIED: backend/tests read]
- Add BFF proxy tests for forwarding `202` and `409` JSON bodies if existing generic tests do not cover them. [VERIFIED: bff tests grep]
- Run frontend build after status/polling UI changes. [VERIFIED: frontend/package.json]
- Run compose config and targeted service startup checks for Redis/worker/backend storage sharing. [VERIFIED: docker-compose.yml]

## Common Pitfalls

### Pitfall 1: `storage_key` Null Assumptions

**What goes wrong:** Pydantic schemas, `file_path` property, preview/download/share endpoints, and frontend iframe/actions assume a stored PDF exists. [VERIFIED: codebase read]

**How to avoid:** Make `storage_key` optional at model/schema boundaries and guard every file operation with `status == "success" and storage_key`. [CITED: CONTEXT.md]

### Pitfall 2: Redis Redelivery Causes Duplicate PDF Writes

**What goes wrong:** Celery Redis visibility timeout can redeliver unacknowledged tasks; late-ack tasks can run again after worker failure. [CITED: Celery Redis and optimizing docs]

**How to avoid:** Worker exits unless DB status is exactly `queued`; save final PDF under deterministic key `{issuance_id}.pdf`; commit terminal status atomically after save where practical. [CITED: CONTEXT.md]

### Pitfall 3: Local Storage Not Shared With Worker

**What goes wrong:** Backend returns success/detail but preview/download 404s because worker wrote to a different container filesystem. [CITED: PRD4.md]

**How to avoid:** Mount `content-storage` volume into both backend and worker at the same path and use identical `CONTENT_STORAGE_ROOT`/`issuance_storage_root` semantics. [VERIFIED: storage code and compose]

### Pitfall 4: Functional Validation Happens Too Late

**What goes wrong:** If API only validates metadata and not payload before enqueue, bad payloads become async failures instead of immediate API errors. [ASSUMED]

**How to avoid:** Preserve current behavior as much as possible: activate design and validate metadata synchronously; decide explicitly whether full payload validation remains API-side or worker-side. Locked context says backend validates before enqueue, while PRD worker also re-reads/generates from DB. [CITED: CONTEXT.md; PRD4.md]

### Pitfall 5: Share URLs Before Success

**What goes wrong:** Existing share endpoint signs any issuance ID and public download later tries to read storage. [VERIFIED: codebase read]

**How to avoid:** Return `409 Conflict` from share for non-success or failed issuances; public download must independently guard status because signed URLs bypass auth. [CITED: CONTEXT.md]

### Pitfall 6: Polling Leaks and Preview Loops

**What goes wrong:** Detail page fetches preview on every detail update, causing repeated blob requests or errors while queued. [VERIFIED: frontend read]

**How to avoid:** Poll only issuance JSON while non-terminal; fetch preview once status becomes `success`; cleanup timers and object URLs on unmount. [ASSUMED: React implementation pattern]

## Code Examples

### Status Guard Pattern

```python
# Source: existing issuances.py + Phase 14 context
def _require_ready_pdf(issuance: DocumentIssuance) -> None:
    if issuance.status in ("queued", "processing"):
        raise HTTPException(status_code=409, detail="Document generation is not complete")
    if issuance.status == "failure":
        raise HTTPException(
            status_code=409,
            detail=issuance.error_message or "Document generation failed",
        )
    if not issuance.storage_key:
        raise HTTPException(status_code=409, detail="Issued PDF is not available")
```

### Worker Idempotency Pattern

```python
# Source: CONTEXT.md + Celery optimizing docs
issuance = db.get(DocumentIssuance, issuance_id)
if issuance is None:
    return
if issuance.status != "queued":
    return

issuance.status = "processing"
issuance.started_at = utcnow()
db.commit()
```

### Frontend Terminal Status Pattern

```typescript
// Source: existing React pages + CONTEXT.md polling baseline
const terminal = detail?.status === "success" || detail?.status === "failure";
const canUsePdf = detail?.status === "success";

useEffect(() => {
  if (!id || terminal) return;
  const delay = elapsedMs < 60_000 ? 2_000 : 5_000;
  const timer = window.setTimeout(refreshIssuance, delay);
  return () => window.clearTimeout(timer);
}, [id, detail?.status, elapsedMs]);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous PDF generation inside HTTP request | API enqueue + Celery worker generation | Phase 14 planned | Removes BFF/proxy/client timeout pressure and gives user-visible job state. [CITED: PRD4.md] |
| `success|failure` only | `queued|processing|success|failure` | Phase 14 planned | Requires DB constraint, API filters, schemas, and UI labels to change together. [CITED: CONTEXT.md] |
| Non-null `storage_key` | Nullable until success | Phase 14 planned | Requires endpoint guards and optional frontend fields. [CITED: CONTEXT.md] |
| Download/share always available in detail UI | Status-gated actions | Phase 14 planned | Prevents 404s and invalid public URLs for unfinished jobs. [CITED: CONTEXT.md] |

## Runtime State Inventory

This is a migration phase because it changes persisted issuance state and storage assumptions.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `document_issuances.storage_key` is currently non-null and status is constrained to `success|failure`; existing rows should remain valid. [VERIFIED: model/migrations] | Alembic migration must relax nullability, replace status check, and add job columns with safe defaults. |
| Live service config | Docker Compose currently lacks Redis and worker services. [VERIFIED: docker-compose.yml] | Add compose services and env vars; no external UI config found in repo. |
| OS-registered state | None found; project uses Docker Compose services, not OS service registration in repo. [VERIFIED: codebase/compose scan] | None. |
| Secrets/env vars | Need new `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER`; no current keys found. [VERIFIED: config.py] | Add settings and `.env.example`/compose values. |
| Build artifacts | Backend dependency lock/env will change when adding `celery[redis]`. [VERIFIED: backend/pyproject.toml] | Update dependency metadata through `uv add`; rebuild backend image. |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Backend tests and worker | yes | `3.12.11` from `python --version`. [VERIFIED: command result] | Existing backend uv environment |
| Docker | Compose runtime | yes with sandbox warning | Docker `29.4.1`, Compose `v5.1.3`; user Docker config was unreadable in sandbox. [VERIFIED: command result] | Run compose commands with approved access if needed |
| PyPI registry access | Dependency verification/install | partial | PyPI JSON fetched for Celery and Redis; local `pip index` unavailable because active venv has no pip. [VERIFIED: command results] | Use official docs/PyPI JSON and `uv add` during implementation |
| `slopcheck` | Package legitimacy audit | no | Install attempt rejected by approval reviewer. [VERIFIED: command result] | Planner must add human package verification checkpoint |
| Redis service | Runtime queue | not yet in compose | `redis:7-alpine` planned. [CITED: CONTEXT.md] | None for async runtime; tests can use Celery eager mode |

**Missing dependencies with no fallback:**
- Redis service is not present yet for real async runtime. [VERIFIED: docker-compose.yml]

**Missing dependencies with fallback:**
- `slopcheck`; fallback is human verification checkpoint before package install. [VERIFIED: command result]

## Validation Architecture

Skipped because `.planning/config.json` has `workflow.nyquist_validation` explicitly set to `false`. [VERIFIED: .planning/config.json]

## Concrete Verification Commands

Use these as likely planner verification commands:

```powershell
# Backend focused async generation/API tests
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_generation_preview.py tests/test_issuance_library_api.py tests/test_document_tracelogs.py -x -q"

# New worker tests once added
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_async_generation_jobs.py -x -q"

# Storage provider regression
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_storage_providers.py -x -q"

# Full backend suite
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest -q"

# BFF proxy regression
rtk proxy powershell -NoProfile -Command "Set-Location bff; uv run pytest -q"

# Frontend type/build regression
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"

# Compose config check after adding redis/worker
rtk docker compose config

# Runtime smoke after compose changes
rtk docker compose up -d postgres redis backend worker bff frontend
rtk docker compose ps
rtk docker compose logs worker
```

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | Existing FastAPI auth dependency and BFF bearer injection remain on enqueue/status/download/share endpoints. [VERIFIED: codebase read] |
| V3 Session Management | yes | Existing BFF encrypted session and token refresh logic; no tokens passed to worker. [VERIFIED: bff read; CITED: CONTEXT.md] |
| V4 Access Control | yes | Worker operates on already-authorized persisted issuance IDs; API must still authorize creation and status/download/share access. [CITED: CONTEXT.md] |
| V5 Input Validation | yes | Existing payload and metadata validation must run before enqueue; worker should treat DB data as persisted domain input, not untrusted task args. [VERIFIED: codebase read; CITED: CONTEXT.md] |
| V6 Cryptography | yes | Keep existing HMAC public share signatures; do not sign unfinished/failed documents. [VERIFIED: codebase read] |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthorized task execution with forged payload | Tampering | Celery task accepts only `issuance_id`; backend persists validated payload before enqueue. [CITED: CONTEXT.md] |
| Public share URL for unfinished or failed document | Information Disclosure / Integrity | Gate share and public download on `status == "success"` and non-null `storage_key`. [VERIFIED: codebase read; CITED: CONTEXT.md] |
| Duplicate redelivery writes multiple files | Tampering / Reliability | Idempotent DB status check and deterministic storage key. [CITED: Celery docs; CONTEXT.md] |
| Sensitive payload leaked in worker logs/errors | Information Disclosure | Truncate `error_message` and avoid logging full `input_data`. [CITED: PRD4.md] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | API should retain as much synchronous payload validation as possible before enqueue, beyond metadata/design validation. | Common Pitfalls / Wave 1 | If product expects all render failures to be async, API tests may need different expectations. |
| A2 | `generateDocumentDesign(...)` should be added only if UI needs a generate action in this phase. | Wave 3 | Planner may include unnecessary UI work if generation stays API-only. |
| A3 | React polling implementation can use `setTimeout` with elapsed-time tracking. | Code Examples | Minor implementation detail; wrong choice affects UI ergonomics, not architecture. |
| A4 | Package legitimacy is acceptable after human verification despite missing `slopcheck`. | Package Legitimacy Audit | Installing a suspicious package would be supply-chain risk. |

## Open Questions (RESOLVED)

1. **Worker failure tracelog event type**
   - Resolution: Do not add a new tracelog event type in Phase 14. Worker failures are represented by `DocumentIssuance.status = "failure"` plus bounded `error_message` and `completed_at`. This avoids expanding the existing `generation|download|share` tracelog constraint unless a later phase explicitly budgets DB/schema/UI changes for failure events.

2. **Synchronous versus asynchronous validation failures**
   - Resolution: Keep auth, design lookup, draft activation, metadata validation, and any cheap reusable request validation in the API before enqueue. Render/storage/template/static-asset failures are handled by the worker and persisted as `failure`.

3. **Frontend generate action**
   - Resolution: Phase 14 must deliver job management in the existing generated-documents library/detail experience. A typed `generateDocumentDesign(...)` helper may be added only where the current UI has or needs a generation action that navigates to the queued issuance detail; the mandatory UI scope is status visibility, polling, action gating, and failure display for jobs.

## Sources

### Primary (HIGH confidence)
- Local codebase reads: `backend/app/api/document_designs.py`, `backend/app/api/issuances.py`, `backend/app/models/document_issuance.py`, `backend/app/schemas/document_issuance.py`, `backend/app/services/pdf_generator.py`, `backend/app/services/storage/*`, `backend/app/dependencies.py`, `backend/app/config.py`, `docker-compose.yml`, `bff/app/proxy/router.py`, `frontend/src/lib/documentIssuances.ts`, `frontend/src/pages/document-issuances/*`, `frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx`.
- Phase context: `.planning/phases/14-implementar-scopes-prd4-md/14-CONTEXT.md`.
- Product PRD: `.scopes/PRD4.md`.
- Milestone audit: `.planning/v2.0-v2.0-MILESTONE-AUDIT.md`.
- Celery Redis docs: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html.
- Celery configuration/optimization docs: https://docs.celeryq.dev/en/stable/userguide/configuration.html and https://docs.celeryq.dev/en/stable/userguide/optimizing.html.
- Docker Redis official image: https://hub.docker.com/_/redis.
- PyPI JSON: https://pypi.org/pypi/celery/json and https://pypi.org/pypi/redis/json.

### Secondary (MEDIUM confidence)
- Package legitimacy audit without `slopcheck`; official docs and PyPI metadata were checked, but slopcheck was unavailable. [VERIFIED: command result]

### Tertiary (LOW confidence)
- None beyond assumptions listed above.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - Celery/Redis is locked and official docs/PyPI verified versions, but `slopcheck` was unavailable.
- Architecture: HIGH - derived from locked CONTEXT/PRD and exact local code paths.
- Pitfalls: HIGH - most risks map directly to current nullability/status/download/share/polling assumptions; Celery redelivery risk is cited from official docs.

**Research date:** 2026-07-13
**Valid until:** 2026-08-12 for codebase boundaries; re-check package versions before install.

## RESEARCH COMPLETE
