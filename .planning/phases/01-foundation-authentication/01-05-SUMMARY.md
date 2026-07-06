---
phase: 01-foundation-authentication
plan: 05
subsystem: auth
tags: [sqlalchemy, postgres, session-management, tdd]

requires:
  - phase: 01-01 (backend scaffold, User/Session SQLAlchemy models, pytest infra)
provides:
  - "upsert_user(db, sub, email) -> User — create-or-reuse local user record on IdP login (D-07)"
  - "create_session(db, user) -> Session — opaque DB-backed session issuance with expiry (D-08)"
  - "delete_session(db, token) -> None — idempotent real server-side session deletion (D-08)"
affects: [01-06-PLAN (wires these into /auth/callback and /auth/logout HTTP routes)]

tech-stack:
  added: []
  patterns:
    - "Service functions are pure and directly unit-tested against db_session fixture, with no HTTP layer — HTTP route wiring deferred to the next plan"
    - "Opaque session tokens via secrets.token_urlsafe(32), not JWTs, so server-side deletion is a real revocation (RESEARCH.md Pattern 3)"

key-files:
  created:
    - backend/app/auth/user_service.py
    - backend/app/auth/session_service.py
    - backend/tests/test_auth_callback.py
    - backend/tests/test_session_service.py
  modified: []

key-decisions:
  - "upsert_user updates email in place on repeat login if it changed at the IdP, rather than leaving stale local data"
  - "delete_session is a no-op (not an error) when called on an already-deleted/nonexistent token, since /auth/logout must be safe to call more than once"

requirements-completed: [AUTH-01]

metrics:
  duration: 25min
  completed: 2026-07-05
---

# Phase 01 Plan 05: User Upsert & Session Lifecycle Services Summary

**Local user upsert-on-login and DB-backed opaque session create/delete, both TDD'd against a live Postgres test DB, ready for 01-06's route wiring.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-05T21:09:00-05:00 (approx, including local Postgres stack startup)
- **Completed:** 2026-07-05T21:34:00-05:00
- **Tasks:** 2 completed
- **Files modified:** 4 (all new)

## Accomplishments

- `upsert_user` creates exactly one local `User` row on first login by a given IdP `sub`, reuses it on repeat logins (no duplicates), and refreshes the stored email if it changed at the IdP — proving D-07.
- `create_session`/`delete_session` issue opaque, unique `secrets.token_urlsafe(32)` session tokens with a correct `expires_at` (`now + settings.session_ttl_seconds`), and `delete_session` performs a real DB row deletion — a genuine server-side logout per RESEARCH.md Pattern 3, not a client-side expiring cookie — and is idempotent when called twice.
- Both services are covered by 6 passing DB-backed unit tests run against the live `docmanagement_test` Postgres database (no mocking of the DB layer), following the TDD RED→GREEN flow per task.

## Task Commits

Each task committed atomically (TDD RED then GREEN):

1. **Task 1: User upsert-on-login service**
   - `ea48964` (test) — failing tests: `test_first_login_creates_user`, `test_repeat_login_reuses_user`, `test_repeat_login_updates_email_if_changed`
   - `e3a9df9` (feat) — `upsert_user` implementation, all 3 tests pass
2. **Task 2: Session create/delete service**
   - `8450f34` (test) — failing tests: `test_create_session_sets_expiry`, `test_create_session_generates_opaque_unique_id`, `test_delete_session_removes_row`
   - `865f951` (feat) — `create_session`/`delete_session` implementation, all 3 tests pass

_Note: TDD tasks produce two commits each (test → feat); no refactor step was needed since the plan's specified implementation matched the minimal-code-to-pass version exactly._

## Files Created/Modified

- `backend/app/auth/user_service.py` — `upsert_user(db, sub, email) -> User`
- `backend/app/auth/session_service.py` — `create_session(db, user) -> Session`, `delete_session(db, token) -> None`
- `backend/tests/test_auth_callback.py` — 3 tests for `upsert_user` against `db_session` fixture
- `backend/tests/test_session_service.py` — 3 tests for `create_session`/`delete_session` against `db_session` fixture

## Decisions Made

- Followed the plan's specified implementation for both service functions exactly (no changes to the reference code in the plan's `<action>` blocks).
- Local Postgres dev stack (`docker compose up -d postgres`) was not already running in this worktree at plan start; started it and created a local `.env` (gitignored, copied from `.env.example`) to make `settings.test_database_url` resolvable — required for `db_session` fixture used by all tests in this plan and matches the setup already established in 01-02-PLAN's docker-compose.yml.

## Deviations from Plan

None - plan executed exactly as written. The only unplanned work was environment setup (starting the already-provisioned Postgres container and creating a local `.env` from `.env.example`), which is standard local dev setup rather than a code deviation.

## Issues Encountered

None. All 6 tests passed on first implementation attempt for each task; no debugging iterations required.

## User Setup Required

None - no external service configuration required. (Local Postgres was already defined by 01-02-PLAN's `docker-compose.yml`; this plan only started the existing container.)

## Next Phase Readiness

`upsert_user`, `create_session`, and `delete_session` are fully implemented and unit-tested. 01-06-PLAN can now wire these directly into the `/auth/callback` and `/auth/logout` HTTP routes without needing to re-derive any of the user-upsert or session-lifecycle logic — it only needs to call these functions with the right arguments (validated JWT claims for `upsert_user`, the session cookie/token for `delete_session`).

No blockers.

---
*Phase: 01-foundation-authentication*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created files verified present on disk; all 4 task commit hashes (`ea48964`, `e3a9df9`, `8450f34`, `865f951`) verified present in git history.
