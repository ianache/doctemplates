# Phase 14: implementar-scopes-prd4-md - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning
**Source:** `.scopes/PRD4.md` plus operator clarification to include job-management UI based on `.planning/v2.0-v2.0-MILESTONE-AUDIT.md`.

<domain>
## Phase Boundary

This phase implements asynchronous PDF document generation using Celery workers and Redis as the broker. The backend API remains the producer and the domain source of truth remains Postgres through `document_issuances`; Redis coordinates delivery only.

The phase is complete when:
1. `POST /api/document-designs/{design_id}/generate` validates and enqueues work, creates `DocumentIssuance(status="queued")`, stores the Celery task id, and returns `202 Accepted`.
2. A Celery worker processes queued issuances, updates `queued -> processing -> success|failure`, writes PDFs through the existing `StorageProvider`, and records audit trace events.
3. `GET /api/issuances/{id}` and listing/search endpoints expose `queued`, `processing`, `success`, and `failure` consistently.
4. Download/share/preview behavior rejects unfinished or failed issuances with correct `409 Conflict` responses instead of assuming a file exists.
5. Docker Compose includes Redis and a worker service sharing local issuance storage with the backend.
6. The BFF and Frontend treat generation as an asynchronous job workflow.
7. The UI includes management and visibility for document-creation jobs, aligned with the existing v2.0 generated-documents library and issuance detail patterns.
</domain>

<decisions>
## Implementation Decisions

### Async Generation Architecture
- Use Celery for task execution and Redis for broker/result backend.
- Postgres remains the source of truth for job status and issuance data.
- The worker receives only `issuance_id`, never bearer tokens or arbitrary client payloads.
- The backend authenticates and validates the request before enqueueing.
- If a design is still `draft`, the backend validates and activates it before enqueueing so the worker uses a stable version.

### Issuance Status Model
- Extend `DocumentIssuance.status` to exact values: `queued`, `processing`, `success`, `failure`.
- Allow `DocumentIssuance.storage_key` to be nullable while status is not `success`.
- Add nullable job fields:
  - `celery_task_id`
  - `error_message`
  - `queued_at`
  - `started_at`
  - `completed_at`
  - `retry_count` with default `0`
- Persist `input_data`, `metadata_values`, `user_id`, and `design_version_id` at enqueue time.

### Worker Behavior
- Create `backend/app/workers/celery_app.py` for Celery configuration.
- Create `backend/app/workers/document_generation.py` with `generate_document_pdf(issuance_id: str)`.
- The task must be idempotent: if an issuance is no longer `queued`, it exits without regenerating.
- On success, store the PDF via `StorageProvider`, set `storage_key`, mark `success`, and append a generation tracelog.
- On failure, mark `failure`, truncate and persist `error_message`, set `completed_at`, and append an error trace event if supported by the existing trace model.

### API/BFF Contract
- `POST /api/document-designs/{design_id}/generate` returns `202 Accepted` with the queued issuance.
- `GET /api/issuances/{issuance_id}` returns current job status and error metadata.
- `GET /api/issuances/{issuance_id}/download` returns `409 Conflict` for `queued`, `processing`, and `failure`.
- Existing preview remains synchronous for this phase.
- The BFF must forward the new async contract and expose status fields to the frontend without hiding backend states.

### Frontend Job Management UI
- The generated-documents experience from Phase 9 remains the user-facing base: searchable issuance list, detail page, preview/download/share actions, and audit timeline.
- Add UI affordances for document-creation jobs:
  - Status filters and labels for `queued`, `processing`, `success`, and `failure`.
  - Polling on recently created or open job details until terminal status.
  - Disabled download/share/preview actions with clear state for non-ready jobs.
  - Error display for `failure` using `error_message`.
  - A job-focused management surface in the existing content/templates or generated-documents flow, reusing the Phase 9 library/detail patterns rather than creating a disconnected screen.
- Polling baseline: every 2 seconds for the first 60 seconds, then every 5 seconds; stop at `success` or `failure`.

### Docker Compose
- Add `redis` service using `redis:7-alpine`.
- Add `worker` service using the backend image and `uv run celery -A app.workers.celery_app worker --loglevel=info`.
- Backend and worker must share local issuance storage volume when `STORAGE_PROVIDER_TYPE=local`.

### the agent's Discretion
- Exact frontend placement for the job management surface, as long as it is discoverable from the generated-documents/document-creation workflow.
- Whether to expose manual refresh in addition to polling.
- Exact retry classification in the first version, provided functional errors become `failure` and transient infrastructure errors are safe for Celery retries.
</decisions>

<requirements>
## Requirement IDs

- **ASYNC-01:** Generation endpoint enqueues work and returns `202 Accepted` with `queued` issuance.
- **ASYNC-02:** Celery worker processes queued issuances and updates lifecycle states through `success` or `failure`.
- **ASYNC-03:** `document_issuances` persists task id, timestamps, nullable storage key, retry count, and error message.
- **ASYNC-04:** Download/share/preview-facing endpoints handle non-terminal and failed states without file assumptions.
- **ASYNC-05:** Docker Compose runs backend, Redis, worker, Postgres, storage, BFF, and frontend coherently.
- **ASYNC-06:** Backend tests cover enqueue, worker success, worker failure, and download-before-complete conflicts.
- **JOBUI-01:** BFF and frontend support async generation status polling and terminal-state handling.
- **JOBUI-02:** UI provides job management visibility for queued, processing, success, and failure issuances using existing Phase 9 library/detail patterns.
- **JOBUI-03:** UI disables unavailable actions for unfinished/failed jobs and displays failure errors.
</requirements>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope
- `.scopes/PRD4.md` — Async PDF generation PRD using Celery and Redis.
- `.planning/v2.0-v2.0-MILESTONE-AUDIT.md` — Existing generated-documents library, detail page, preview/download/share, audit timeline, and complex schema UI capabilities to preserve and build upon.

### Likely Backend/BFF/Frontend Areas
- `backend/app/api/document_designs.py` — Current generation endpoint.
- `backend/app/api/issuances.py` — Issuance detail/download endpoints.
- `backend/app/models/document_issuance.py` — Issuance persistence model.
- `backend/app/schemas/document_issuance.py` — Public issuance schema.
- `backend/app/services/pdf_generator.py` — Existing synchronous composed PDF generation.
- `backend/app/services/storage_provider.py` or current storage provider module — Existing storage abstraction from Phase 13.
- `backend/app/models/document_tracelog.py` — Audit trace model from Phase 9.
- `docker-compose.yml` and related compose/env files — Runtime stack.
- `bff/` — API mediation layer used by the frontend.
- `portal/` — Frontend UI for generated documents, content/templates, and document workflows.
</canonical_refs>

<specifics>
## Specific Ideas

- Keep preview synchronous in this phase.
- Prefer status-driven UI over exposing raw Celery internals.
- Treat Redis as operational queue infrastructure only; never as the authoritative job history.
- Align job UI with the Phase 9 audit result: issuance search/filter, detail view, secure PDF preview, download, share URL, and timeline already exist and should be extended for async states.
</specifics>

<deferred>
## Deferred Ideas

- WebSockets/SSE.
- Manual retry from UI.
- Job cancellation.
- Priority queues.
- Percentage progress bars.
- Async preview.
- Stuck-job recovery scanner.
</deferred>

---

*Phase: 14-implementar-scopes-prd4-md*
*Context gathered: 2026-07-13 via PRD4 planning*
