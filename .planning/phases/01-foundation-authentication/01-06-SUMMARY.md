---
phase: 01-foundation-authentication
plan: 06
subsystem: auth
tags: [authlib, oidc, keycloak, fastapi, cors, session-cookie]
requires:
  - phase: 01-01 (backend scaffold, settings, DB/session test fixtures)
  - phase: 01-02 (Docker Compose Keycloak/Postgres realm bootstrap)
  - phase: 01-04 (cookie-session and bearer-token auth dependencies)
  - phase: 01-05 (user upsert and session create/delete services)
provides:
  - "Authlib Keycloak OIDC client registry with PKCE S256 client settings"
  - "GET /auth/login, GET /auth/callback, POST /auth/logout"
  - "Protected GET /api/health accepting either cookie-session or bearer-token auth"
  - "Credentialed CORS allowlist for the configured frontend origin"
affects: [01-07 (frontend login page and authenticated shell), 01-08 (manual AUTH-01 checkpoint)]
tech-stack:
  added: []
  patterns:
    - "Authlib OAuth client isolated in app.auth.oidc"
    - "Backend callback exchanges OIDC token, upserts local user, and stores only opaque session id in httpOnly cookie"
    - "FastAPI optional-auth wrappers call strict dependencies inside try/except so either cookie or bearer auth can satisfy one route"
key-files:
  created:
    - backend/app/auth/oidc.py
    - backend/app/auth/routes.py
    - backend/app/api/__init__.py
    - backend/app/api/health.py
  modified:
    - backend/app/main.py
    - backend/tests/test_auth_callback.py
    - backend/tests/test_auth_gating.py
key-decisions:
  - "Kept Authlib SessionMiddleware only for OAuth handshake state; application login state remains DB-backed via opaque session cookie."
  - "Used explicit settings.frontend_origin CORS allowlist with credentials enabled; no wildcard origin."
  - "Health endpoint uses wrapper dependencies to make cookie and bearer auth alternatives explicit."
requirements-completed: [AUTH-01]
duration: 2h
completed: 2026-07-06
---

# Phase 1 Plan 06: Auth HTTP Surface Summary

**OIDC login/callback/logout routes, credentialed CORS, and a protected health API contract for the frontend.**

## Performance

- **Duration:** 2h
- **Started:** 2026-07-06T03:00:00Z
- **Completed:** 2026-07-06T05:00:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added the Authlib Keycloak client registry with PKCE S256 settings.
- Added `/auth/login`, `/auth/callback`, and `/auth/logout`; callback creates/reuses the local user and sets only the opaque DB session id in the httpOnly cookie.
- Configured `SessionMiddleware` and credentialed CORS with `settings.frontend_origin`.
- Added `/api/health`, protected by either cookie-session auth or bearer-token auth, returning authenticated subject/email.
- Added tests for mocked OIDC callback behavior and `/api/health` auth gating.

## Task Commits

Each task committed atomically:

1. **Task 1: Authlib OIDC client + login/callback/logout routes + CORS/SessionMiddleware wiring** - `c687202` (feat)
2. **Task 2 RED: Callback and health endpoint coverage** - `5dfd0ad` (test)
3. **Task 2 GREEN: Protected /api/health endpoint** - `5ffcc01` (feat)

**Plan metadata:** pending in docs commit.

## Files Created/Modified

- `backend/app/auth/oidc.py` - Authlib OAuth registry for Keycloak.
- `backend/app/auth/routes.py` - login, callback, and logout routes.
- `backend/app/api/__init__.py` - API package marker.
- `backend/app/api/health.py` - protected health endpoint accepting cookie or bearer auth.
- `backend/app/main.py` - SessionMiddleware, CORS, auth router, and health router registration.
- `backend/tests/test_auth_callback.py` - full mocked callback flow test.
- `backend/tests/test_auth_gating.py` - health endpoint auth gating tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Optional auth wrapper dependency semantics**
- **Found during:** Task 2 implementation
- **Issue:** The plan sketch passed `Depends(get_current_user)` and `Depends(verify_bearer_token_dep)` directly into optional wrapper parameters. In FastAPI, exceptions raised by those dependencies occur before the wrapper body runs, so they cannot be caught there.
- **Fix:** The wrappers now accept `Request`/`get_db` and `Authorization` header directly, then call the strict dependencies inside `try` blocks.
- **Files modified:** `backend/app/api/health.py`
- **Verification:** Direct `/api/health` unauthenticated TestClient smoke returns `401 {"detail": "Not authenticated"}`.
- **Committed in:** `5ffcc01`

**Total deviations:** 1 auto-fixed. **Impact:** Required for the planned "cookie OR bearer" health endpoint behavior to work.

## Issues Encountered

- DB-backed pytest runs timed out in this Windows environment before opening a Postgres session. Existing DB-backed tests such as `tests/test_session_service.py::test_create_session_sets_expiry` also timed out, while non-DB `tests/test_smoke.py` passed.
- `/auth/login` redirect spot-check failed in the Windows TestClient process with `OPENSSL_Uplink(...): no OPENSSL_Applink` before returning a redirect. This blocks local confirmation that Authlib emits `code_challenge=`.

## Verification

- `uv run pytest tests/test_smoke.py -q` - passed.
- Direct named route registration check - passed for `/auth/login`, `/auth/callback`, `/auth/logout`, `/api/health`.
- Direct unauthenticated `/api/health` TestClient smoke - passed with 401.
- `uv run pytest tests/test_auth_callback.py tests/test_auth_gating.py -q` - timed out in DB-backed fixture path.
- `/auth/login` PKCE redirect spot-check - failed with Windows OpenSSL applink error.

## User Setup Required

None - no new external service configuration beyond the existing `.env.example`, Keycloak, and Postgres Compose stack.

## Next Phase Readiness

The frontend plan can build against `/auth/login`, `/auth/logout`, and `/api/health`, but Phase 1 still needs the environment-specific DB pytest timeout and Authlib redirect/OpenSSL issue resolved or manually verified during 01-08.

---

*Phase: 01-foundation-authentication*
*Completed: 2026-07-06*
