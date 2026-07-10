# Phase 9: Search Documents Library & Audit Trace - Research

## User Constraints (from CONTEXT.md)

- **D-01 Dedicated Audit Tracelog Table:** Create `DocumentTracelog` in `backend/app/models/document_tracelog.py` with table `document_tracelogs`, UUID primary key, `issuance_id` cascading to `document_issuances.id`, nullable `user_id`, event types `generation`, `download`, `share`, JSON metadata, and server-side `created_at`. Add an Alembic migration.
- **D-02 HMAC Signed Share Links:** Public document access uses `GET /api/public/document-issuances/{id}/download?signature={hmac_signature}`. Signature generation/verification uses HMAC-SHA256 with backend secret configuration. Valid public access logs `download` with `user_id = None`.
- **D-03 Documents Library Navigation:** Add top-level authenticated nav link `Documents Library` at `/document-issuances` in `AuthenticatedShell.tsx` using `description` or `folder_open`.
- **Deferred:** Share-link expiration/access authorization beyond HMAC validation is post-MVP and must not be added in Phase 09.

## Backend Research Notes

### Audit Trail Model

- Use SQLAlchemy 2 typed mappings matching the existing backend model style.
- `DocumentTracelog.event_type` should be constrained to exact values `generation`, `download`, and `share` at the database layer.
- `DocumentIssuance.tracelogs` should use `back_populates`, delete-orphan cascade, and chronological ordering.
- `metadata` may need a different internal model attribute name with schema aliasing because SQLAlchemy reserves `metadata`.

### Issuance Status Semantics

- SRCH-01 status filtering is issuance-level Success/Failure.
- Add `DocumentIssuance.status` with exact stored values `success` and `failure`; default existing/successfully generated issuances to `success`.
- Do not use parent design-version status for SRCH-01 filtering.
- Tests must seed both `success` and `failure` issuances and prove status filtering combines with design name, id, and date range using AND semantics.

### Public and Authenticated File Routes

- Keep signed public download exactly at `GET /api/public/document-issuances/{id}/download?signature={hmac_signature}` per D-02.
- Use stdlib `hmac`, `hashlib.sha256`, and `hmac.compare_digest` for timing-safe verification.
- Add an authenticated preview route, `GET /api/issuances/{id}/preview`, for embedded PDF rendering without writing a `download` tracelog.
- Keep authenticated `GET /api/issuances/{id}/download` as the explicit SRCH-04 user action that logs `download`.
- Signed public download also logs `download` with `user_id = None`.

### API Contract

- `GET /api/issuances` filters by `design_name`, `id`, `status`, `created_from`, and `created_to` using AND semantics.
- `status` accepts only `success` and `failure`.
- Detail responses should include `id`, `design_version_id`, `design_name`, `status`, `design_status`, `design_version_number`, `user_id`, `generated_by_email`, `input_data`, `created_at`, `preview_url`, and `download_url`.
- `POST /api/issuances/{id}/share` returns the signed public URL and logs `share`.
- `GET /api/issuances/{id}/tracelogs` returns chronological audit events.

## Frontend Research Notes

- Use existing `apiFetch`, `jsonOrError`, and `readErrorMessage` conventions.
- Add `/document-issuances` and `/document-issuances/:id` routes.
- Listing UI should offer status options `All`, `Success`, and `Failure`, sending `success`/`failure` values to the backend.
- Detail UI should embed `preview_url` in a browser-native iframe/object for PDF preview.
- Detail UI should reserve `download_url` for the explicit `Download PDF` button/link.
- Share UI should copy only the backend-generated signed URL; the browser must not construct signatures.
- Tracelog timeline layout is at the agent's discretion, but must show `generation`, `download`, and `share` chronologically.

## Pitfalls & Mitigation

| Pitfall | Risk | Mitigation |
|---------|------|------------|
| Status filter drift | Filtering by design-version status would fail SRCH-01 Success/Failure semantics. | Persist and filter `DocumentIssuance.status` values `success`/`failure`; test both values with AND filters. |
| Preview inflates audit trail | Embedding the PDF through the download URL would create false `download` events. | Use separate authenticated preview route that serves the PDF without logging download. |
| Anonymous enumeration | Public users could try UUID scraping. | Require HMAC-SHA256 signature and reject invalid signatures before file access. |
| Proxy IP ambiguity | `request.client.host` may show proxy/container IP. | Prefer trusted forwarded headers only if already used locally; otherwise record available request metadata consistently. |
| Cascading deletes | Audit rows could orphan or block issuance deletion. | Use `ondelete="CASCADE"` for issuance and `ondelete="SET NULL"` for user. |

## Open Questions (RESOLVED)

### 1. What does "Status" filter match against?

- **Resolved decision:** Status is issuance-level Success/Failure, implemented as `DocumentIssuance.status` with exact stored values `success` and `failure`.
- **Implementation impact:** SRCH-01 filtering must query `DocumentIssuance.status` with AND semantics alongside design name, issuance id, and date range. It must not use parent design-version status.

### 2. Share URL Signature Expiration

- **Resolved decision:** No default expiry for MVP, per deferred context. Signature validation uses HMAC-SHA256 over the canonical issuance UUID string; optional expiration is not required in Phase 09 plans.

### 3. Client Name Mapping

- **Resolved decision:** The Phase 09 list/detail contract exposes `generated_by_email` from `DocumentIssuance.user`. If UI wants a client label and a recognizable client field exists in `input_data`, it may display that value; otherwise display the generator email.

### 4. Does PDF preview count as a download audit event?

- **Resolved decision:** Preview does not count as download. Use an authenticated preview route for embedded PDF rendering, and reserve `download` tracelog creation for explicit authenticated `Download PDF` clicks and signed public download access.
