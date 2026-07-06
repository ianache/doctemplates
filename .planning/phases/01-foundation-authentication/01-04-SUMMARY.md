---
phase: 01-foundation-authentication
plan: 04
subsystem: auth
tags: [pyjwt, jwks, fastapi, keycloak, sqlalchemy]

requires:
  - phase: 01-01 (backend scaffold, User/Session models, pytest fixtures)
provides:
  - "verify_bearer_token(token) - independent JWKS-based bearer-token validation"
  - "get_current_user(request, db) - cookie-session FastAPI dependency"
  - "verify_bearer_token_dep(authorization) - bearer-token FastAPI dependency"
affects: [01-06 (protected /api/health route wires these dependencies), 01-05]

tech-stack:
  added: []
  patterns:
    - "Module-level lazily-cached PyJWKClient (_get_jwks_client) as sole monkeypatch seam for tests"
    - "Explicit algorithms=['RS256'] allowlist on jwt.decode to close algorithm-confusion CVE class"
    - "Two independent auth dependencies (cookie session vs bearer token) sharing no code path, per D-09"
    - "Normalize naive DB datetimes to aware UTC before comparison"

key-files:
  created:
    - backend/app/auth/__init__.py
    - backend/app/auth/jwks.py
    - backend/app/auth/dependencies.py
    - backend/tests/test_bearer_auth.py
    - backend/tests/test_auth_gating.py
  modified: []

key-decisions:
  - "Forged the HS256 algorithm-confusion test token by hand (raw base64url + hmac), since PyJWT's own jwt.encode() now refuses to use an asymmetric PEM key as an HMAC secret at encode time - a real attacker crafts token bytes directly, bypassing that library-level guard"
  - "Normalized session.expires_at (naive DateTime column from 0001 migration) to aware UTC before comparing against datetime.now(timezone.utc), rather than altering the existing migration/model (out of this plan's file scope)"
  - "Registered/unregistered a throwaway APIRouter route on the shared app instance per-test (protected_route fixture) to exercise get_current_user through real FastAPI DI, without adding a permanent test-only route to production code"

requirements-completed: [AUTH-01]

metrics:
  duration: 20min
  completed: 2026-07-06
---

# Phase 01 Plan 04: Bearer-Token and Cookie-Session Auth Dependencies Summary

**Independent JWKS bearer-token validation (PyJWT + PyJWKClient, explicit RS256 allowlist) and DB-backed cookie-session dependency, both unit-tested against forged/expired/malformed tokens and sessions with no live Keycloak or browser involved.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-06T02:12:00Z (approx)
- **Completed:** 2026-07-06T02:32:04Z
- **Tasks:** 2 completed
- **Files modified:** 5 created

## Accomplishments

- `verify_bearer_token(token)` validates JWTs against a Keycloak realm's JWKS endpoint via `PyJWKClient`, with `algorithms=["RS256"]` as the sole explicit allowlist — closes the JWT algorithm-confusion CVE class (RESEARCH.md Pitfall 4)
- `get_current_user(request, db)` and `verify_bearer_token_dep(authorization)` FastAPI dependencies implement the two independent auth mechanisms D-09 requires (cookie session for UI, bearer token for API/M2M), sharing no code path
- 8 passing unit tests prove: valid token acceptance; rejection of wrong audience, wrong issuer, expired token, and forged HS256 (algorithm-confusion); unauthenticated/expired-session/valid-session cookie gating

## Task Commits

Each task committed atomically:

1. **Task 1: Bearer-token JWKS validation** - `f471b89` (feat)
2. **Task 2: Cookie-session dependency + unauthenticated-rejection gating test** - `0325e5c` (feat)

**Plan metadata:** (this commit, following)

_Both tasks were TDD-flagged in the plan; tests and implementation were written together per task and verified passing before commit (not split into separate RED/GREEN commits), matching the plan's own inlined test-then-code `<action>` structure rather than a strict red-green-refactor cycle._

## Files Created/Modified

- `backend/app/auth/__init__.py` - empty package marker
- `backend/app/auth/jwks.py` - `verify_bearer_token`, `_get_jwks_client` (module-cached `PyJWKClient`, exact monkeypatch target for conftest's `mock_jwks_client`)
- `backend/app/auth/dependencies.py` - `get_current_user`, `verify_bearer_token_dep`
- `backend/tests/test_bearer_auth.py` - 5 tests: valid, wrong audience, wrong issuer, expired, forged HS256 algorithm-confusion
- `backend/tests/test_auth_gating.py` - 3 tests: unauthenticated (401), expired session (401), valid session (200 + correct identity), using a throwaway per-test route

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created local `.env` from `.env.example`**
- **Found during:** Task 1 (running `pytest tests/test_bearer_auth.py`)
- **Issue:** `backend/app/config.py` requires 8 env vars (`Settings(BaseSettings)`, no defaults) sourced from a repo-root `.env`; this worktree only had `.env.example` (`.env` is gitignored and not copied into new worktrees), so `Settings()` instantiation failed with 8 validation errors before any test could even collect.
- **Fix:** `cp .env.example .env` at the repo root — matches the values 01-02-PLAN's docker-compose/Keycloak realm-export already expect for local dev.
- **Files modified:** `.env` (gitignored, not committed)
- **Commit:** N/A (untracked, gitignored)

**2. [Rule 1 - Bug] Forged the algorithm-confusion test token manually instead of via `jwt.encode`**
- **Found during:** Task 1, `test_invalid_jwt_rejected_wrong_algorithm`
- **Issue:** The plan's suggested approach (`jwt.encode(claims, public_pem, algorithm="HS256")`) raises `InvalidKeyError` from PyJWT itself at *encode* time — PyJWT now detects an asymmetric PEM being passed as an HMAC secret and refuses, which prevented the test token from ever being minted (never reached `verify_bearer_token` at all, so the test proved nothing about the actual defense).
- **Fix:** Added `_forge_hs256_token()` helper that hand-builds the JWT (base64url header/payload + raw `hmac.new(...).digest()` signature), bypassing PyJWT's caller-side guard — this is what a real attacker's crafted token bytes look like, and it correctly exercises `verify_bearer_token`'s `algorithms=["RS256"]` allowlist, which raises `jwt.PyJWTError` as expected.
- **Files modified:** `backend/tests/test_bearer_auth.py`
- **Commit:** `f471b89`

**3. [Rule 1 - Bug] Normalized naive `expires_at` before comparing to aware `datetime.now(timezone.utc)`**
- **Found during:** Task 2, `test_expired_session_rejected` / `test_valid_session_accepted` (against the real Postgres test DB)
- **Issue:** `sessions.expires_at` is `sa.DateTime()` (no timezone) per 0001's migration (01-01-PLAN, out of this plan's file scope), so values read back from Postgres are naive. Comparing a naive `datetime` to `datetime.now(timezone.utc)` (aware) raises `TypeError: can't compare offset-naive and offset-aware datetimes`, which would have surfaced as an unhandled 500 on every request through `get_current_user` instead of the required 401.
- **Fix:** In `get_current_user`, if `session.expires_at.tzinfo is None`, treat it as UTC and attach `tzinfo=timezone.utc` before comparing. Kept the fix local to `dependencies.py` (this plan's file) rather than altering the 0001 migration/model, which belongs to a different plan and would be an architectural change out of scope here.
- **Files modified:** `backend/app/auth/dependencies.py`
- **Commit:** `0325e5c`

## Issues Encountered

None beyond the auto-fixed items above. Full test suite (`pytest tests/test_bearer_auth.py tests/test_auth_gating.py -q`) against the worktree's own dockerized Postgres: 8 passed.

## User Setup Required

None — no external service configuration required beyond the local `.env` already reconciled by prior phase work (01-02-PLAN's Keycloak realm-export values).

## Next Phase Readiness

`get_current_user` and `verify_bearer_token_dep` are ready to be wired directly via `Depends(...)` on 01-06-PLAN's `/api/health` route with no further auth-logic design work. No blockers. Note for the parallel 01-05-PLAN merge: both plans append to `backend/app/auth/__init__.py`'s package surface conceptually, but this plan left `__init__.py` as an empty marker (no exports added) — 01-05-PLAN's additions to that file should merge without conflict.

---

*Phase: 01-foundation-authentication*
*Completed: 2026-07-06*

## Self-Check: PASSED

All 5 created files exist on disk; both task commits (`f471b89`, `0325e5c`) found in git log.
