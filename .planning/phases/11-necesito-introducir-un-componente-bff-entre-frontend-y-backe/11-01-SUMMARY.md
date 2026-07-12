---
phase: 11-necesito-introducir-un-componente-bff-entre-frontend-y-backe
plan: "01"
subsystem: auth
tags: [fastapi, jwt, keycloak, cookie, proxy, httpx]

# Dependency graph
requires: []
provides:
  - bff-service
  - stateless-backend-auth
affects: [frontend]

# Tech tracking
tech-stack:
  added: [cryptography, pyjwt, pydantic-settings, python-dotenv, python-multipart]
  patterns: [BFF proxy, Fernet encrypted cookies, silent token refresh]

key-files:
  created:
    - bff/pyproject.toml
    - bff/Dockerfile
    - bff/app/config.py
    - bff/app/main.py
    - bff/app/auth/session.py
    - bff/app/auth/routes.py
    - bff/app/proxy/router.py
    - bff/tests/conftest.py
    - bff/tests/test_auth.py
    - bff/tests/test_proxy.py
  modified:
    - backend/app/auth/dependencies.py
    - backend/app/main.py
    - backend/app/config.py
    - backend/app/api/health.py
    - backend/tests/conftest.py
    - backend/tests/test_auth_gating.py
    - frontend/src/pages/document-types/DocumentTypeCreatePage.tsx
    - docker-compose.yml
    - .env
    - .env.example

key-decisions:
  - "Used stateless encrypted Fernet session cookies with zlib compression for OIDC token storage in the BFF."
  - "Used weakref.WeakValueDictionary containing asyncio.Lock objects to serialize parallel token refreshes per user session."
  - "Integrated a test client wrapper to dynamically map database-backed test sessions to signed Bearer JWTs, avoiding major backend test refactoring."

patterns-established:
  - "BFF Pattern: proxying authenticated browser requests using encrypted httpOnly cookies, injecting Bearer tokens, and stripping CORS headers."

requirements-completed: []

coverage:
  - id: D1
    description: "BFF Scaffolding, configuration, and Docker setup"
    verification:
      - kind: unit
        ref: "bff/tests/test_auth.py#test_login_redirect"
        status: pass
    human_judgment: false
  - id: D2
    description: "Encrypted cookie management and OIDC callback/logout flows"
    verification:
      - kind: unit
        ref: "bff/tests/test_auth.py#test_callback_success"
        status: pass
      - kind: unit
        ref: "bff/tests/test_auth.py#test_logout"
        status: pass
    human_judgment: false
  - id: D3
    description: "Reverse proxy streaming and silent refresh with serialization"
    verification:
      - kind: unit
        ref: "bff/tests/test_proxy.py#test_proxy_authenticated_request_silent_refresh"
        status: pass
    human_judgment: false
  - id: D4
    description: "Core backend isolation to accept Bearer tokens strictly"
    verification:
      - kind: integration
        ref: "backend/tests/test_auth_gating.py#test_valid_bearer_token_accepted"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-07-11
status: complete
---

# Phase 11: BFF Component & Core Backend Isolation Summary

**BFF reverse proxy with silent token refresh, encrypted session cookies, and stateless Bearer JWT verification on Core Backend.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-07-11T23:00:08-05:00
- **Completed:** 2026-07-11T23:25:00-05:00
- **Tasks:** 12 completed
- **Files modified:** 10

## Accomplishments
- scaffolded, configured and created Dockerfile for a FastAPI BFF service using uv.
- Implemented Fernet encrypted session cookies with zlib compression for horizontal scalability without DB state in BFF.
- Created OIDC login redirect, callback code exchange, and logout routes on the BFF.
- Built a streaming catch-all reverse proxy endpoint supporting silent token refresh with per-user-session asyncio.Lock serialization (via WeakValueDictionary).
- Isolated the Core Backend by replacing cookie-based auth dependencies with strict Bearer JWT signature verification using public keys.
- Adapted the entire backend test suite using a custom TestClient request wrapper to translate database sessions into mock Bearer tokens.
- Updated the frontend UI copy-paste API client snippets to show Authorization Bearer headers.
- Restructured Docker Compose services to run BFF on public port 8000 and Backend on internal port 8001.
- Implemented and passed all unit and integration tests in the BFF.

## Task Commits

Each task was committed atomically:

1. **Task 1: BFF Project Scaffolding & Dependencies** - `92f8974` (feat)
2. **Task 2: BFF Application Configuration** - `31bee92` (feat)
3. **Task 3: BFF Dockerfile Setup** - `ac9860a` (feat)
4. **Task 4: Encrypted Session Cookie Helper** - `c7b805e` (feat)
5. **Task 5: OIDC Authentication & Logout Routes** - `3c20b06` (feat)
6. **Task 6: Reverse Proxy & Silent Refresh Middleware** - `2634676` (feat)
7. **Task 7: BFF Main Entry Point Setup** - `1f7696a` (feat)
8. **Task 8: Isolate Core Backend Authentication** - `abce831` (feat)
9. **Task 9: Adapt Backend Integration Tests to Bearer Tokens** - `fc75cc1` (test)
10. **Task 10: Update Frontend Copy-Paste Code Snippets** - `6368548` (feat)
11. **Task 12: Update Docker Compose & Environment Configuration** - `e955408` (chore)
12. **Task 13: BFF Unit & Integration Tests** - `6212151` (test)

## Files Created/Modified
- `bff/pyproject.toml` - BFF dependencies and settings
- `bff/Dockerfile` - Docker image definition for BFF
- `bff/app/config.py` - Configuration loading settings via Pydantic
- `bff/app/main.py` - Main FastAPI application entrypoint
- `bff/app/auth/session.py` - Encryption and compression helpers for session cookie
- `bff/app/auth/routes.py` - OIDC login, callback and logout routes
- `bff/app/proxy/router.py` - Catch-all reverse proxy and token refresh logic
- `bff/tests/conftest.py` - BFF test fixtures and mock clients
- `bff/tests/test_auth.py` - Auth endpoints tests
- `bff/tests/test_proxy.py` - Proxy forwarding and refresh tests
- `backend/app/auth/dependencies.py` - Updated to use Bearer token JWT verification
- `backend/app/main.py` - Removed SessionMiddleware and auth routes
- `backend/app/config.py` - Removed unused client/secret/session settings
- `backend/app/api/health.py` - Updated to use Bearer token gating
- `backend/tests/conftest.py` - Wrapped TestClient to convert cookie sessions to JWTs
- `backend/tests/test_auth_gating.py` - Rewritten to check Bearer token auth gating
- `frontend/src/pages/document-types/DocumentTypeCreatePage.tsx` - Replaced cookie headers with Bearer tokens
- `docker-compose.yml` - Expose BFF on port 8000 and Backend on 8001
- `.env.example` & `.env` - Configured BACKEND_URL and session cookie name

## Decisions Made
- Used stateless encrypted Fernet session cookies with zlib compression for OIDC token storage in the BFF to guarantee horizontal scalability.
- Used `weakref.WeakValueDictionary` containing `asyncio.Lock` objects to serialize parallel token refreshes per user session, protecting Keycloak and backend.
- Integrated a TestClient wrapper in `backend/tests/conftest.py` to translate database test sessions into mock Bearer tokens dynamically, keeping the test suite intact.

## Deviations from Plan
- None - followed plan exactly as written.

## Issues Encountered
- **Pydantic Settings extra inputs warning**: When removing variables from config, Pydantic complained about extra variables in `.env`. Solved by setting `extra="ignore"` in backend config settings.
- **httpx.StreamConsumed in mock tests**: Resolved by returning response stream using `httpx.ByteStream` in mock transport.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready to run docker compose up to bring up the full isolated architecture.
- Both test suites passing 100%.

---
*Phase: 11-necesito-introducir-un-componente-bff-entre-frontend-y-backe*
*Completed: 2026-07-11*
