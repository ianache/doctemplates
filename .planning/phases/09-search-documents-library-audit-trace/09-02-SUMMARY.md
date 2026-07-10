---
phase: 09-search-documents-library-audit-trace
plan: "02"
subsystem: backend-api
tags:
  - issuance-library
  - signed-share
  - audit-trace
  - fastapi
requires:
  - phase: 09-01
    provides: issuance status and document tracelog persistence
provides:
  - Authenticated issuance library list and detail endpoints
  - Authenticated PDF preview and explicit download endpoints
  - Signed public issuance download endpoint
  - Share URL generation and download/share audit logging
affects:
  - phase-09-frontend
  - document-issuances
  - audit-trace
tech-stack:
  added: []
  patterns:
    - HMAC-SHA256 signatures using the configured app secret
    - Preview and download routes separated so preview does not log download events
key-files:
  created:
    - backend/app/utils/signature.py
    - backend/tests/test_issuance_library_api.py
  modified:
    - backend/app/config.py
    - backend/app/main.py
    - backend/app/api/issuances.py
    - backend/app/schemas/document_issuance.py
key-decisions:
  - "Use settings.secret_key when configured, falling back to settings.session_secret for local compatibility."
  - "Expose public share URLs as backend-generated relative URLs containing the signed issuance UUID."
patterns-established:
  - "Issuance API responses include stable preview_url and download_url fields for frontend consumers."
  - "Server-side audit events record route, user agent, IP, and authenticated or anonymous actor context."
requirements-completed:
  - SRCH-01
  - SRCH-02
  - SRCH-03
  - SRCH-04
  - SRCH-05
coverage:
  - id: D1
    description: "Authenticated users can retrieve and filter generated issuances by design name, id, issuance-level status, and date range with AND semantics."
    requirement: SRCH-01
    verification:
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_list_issuances_applies_all_filters_against_issuance_status"
        status: pass
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_list_issuances_filters_failure_status_and_rejects_unknown_status"
        status: pass
    human_judgment: false
  - id: D2
    description: "Authenticated users can fetch issuance detail metadata including design, user, input data, preview URL, and download URL."
    requirement: SRCH-02
    verification:
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_get_issuance_detail_returns_library_metadata"
        status: pass
    human_judgment: false
  - id: D3
    description: "Authenticated preview serves the PDF without creating a download audit event."
    requirement: SRCH-03
    verification:
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_preview_serves_pdf_without_download_tracelog"
        status: pass
    human_judgment: false
  - id: D4
    description: "Authenticated download serves the PDF and records a download tracelog for the user."
    requirement: SRCH-04
    verification:
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_authenticated_download_logs_download_tracelog"
        status: pass
    human_judgment: false
  - id: D5
    description: "Authenticated share creates a signed public URL, public download validates the signature, and download/share tracelogs are chronological."
    requirement: SRCH-05
    verification:
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_share_returns_public_url_and_logs_share_tracelog"
        status: pass
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_valid_public_download_logs_anonymous_download"
        status: pass
      - kind: integration
        ref: "backend/tests/test_issuance_library_api.py#test_tracelogs_are_returned_chronologically"
        status: pass
    human_judgment: false
duration: recovered
completed: 2026-07-10
status: complete
---

# Phase 09 Plan 02: Documents Library API Summary

Authenticated issuance search, detail, preview, download, signed share, public download, and audit trace endpoints for the Documents Library.

## Performance

- **Duration:** recovered from interrupted execution
- **Started:** previous interrupted execution before summary recovery
- **Completed:** 2026-07-10
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added deterministic HMAC-SHA256 issuance signatures and mounted the unauthenticated public download router.
- Added issuance list/detail endpoints with AND filters for design name, issuance id, issuance-level Success/Failure status, and date range.
- Added authenticated preview, explicit download, share, public download, and chronological tracelog endpoints.
- Added integration tests covering SRCH-01 through SRCH-05 backend behavior.

## Task Commits

1. **Task 1: Add HMAC signature helper and public router registration** - `06ba6f0` (test), `6e45986` (feat)
2. **Task 2: Implement issuance listing, detail, tracelog, share, and download endpoints** - `0be6f4b` (test), `96aab34` (feat)

**Plan metadata:** created in this summary commit.

## Files Created/Modified

- `backend/app/utils/signature.py` - HMAC signature generation and timing-safe verification.
- `backend/app/config.py` - Optional `secret_key` setting with session-secret fallback.
- `backend/app/main.py` - Public issuance router registration.
- `backend/app/api/issuances.py` - Issuance library, detail, preview, download, share, public download, and tracelog routes.
- `backend/app/schemas/document_issuance.py` - Library item, share response, and tracelog response schemas.
- `backend/tests/test_issuance_library_api.py` - API tests for signatures, filters, metadata, preview/download/share, public download, and timeline ordering.

## Decisions Made

- Used the configured `secret_key` when present and `session_secret` as the fallback so local environments do not need immediate `.env` changes.
- Kept public share URLs relative to the API host; frontend can prefix them for clipboard use.
- Used the issuance-level `DocumentIssuance.status` for Success/Failure search, not design-version status.
- Separated preview from download so embedded PDF viewing does not create a download audit event.

## Deviations from Plan

### Auto-fixed Issues

None - plan scope was completed as specified during recovery.

---

**Total deviations:** 0 auto-fixed.
**Impact on plan:** No scope change.

## Issues Encountered

- Previous execution produced `09-02` production/test commits without `09-02-SUMMARY.md`; safe-resume recovery inspected the implementation, ran verification, committed the remaining backend API files, and wrote this summary.
- Sandboxed direct `pytest` failed because the environment lacked `xhtml2pdf`; verification used the backend `uv run` environment instead.
- Sandboxed `uv run` could not read the user-profile uv cache, so verification was rerun with approved elevated access.

## Verification

Command run:

```powershell
Set-Location backend; uv run pytest tests\test_issuance_library_api.py tests\test_document_tracelogs.py tests\test_generation_preview.py -x
```

Result:

```text
21 passed, 1 warning in 161.93s
```

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 09-03 can build the frontend Documents Library against the stable backend API:

- `GET /api/issuances`
- `GET /api/issuances/{id}`
- `GET /api/issuances/{id}/preview`
- `GET /api/issuances/{id}/download`
- `POST /api/issuances/{id}/share`
- `GET /api/issuances/{id}/tracelogs`
- `GET /api/public/document-issuances/{id}/download?signature=...`

## Self-Check

PASSED - summary reconciles the interrupted plan state, task commits exist, and all plan verification tests pass.

---
*Phase: 09-search-documents-library-audit-trace*
*Completed: 2026-07-10*
