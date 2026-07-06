---
phase: 1
slug: foundation-authentication
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | none — Wave 1 (01-01-PLAN) installs |
| **Quick run command** | `cd backend && uv run pytest -q` |
| **Full suite command** | `cd backend && uv run pytest` |
| **Estimated runtime** | ~10-20 seconds (unit + mocked-JWKS integration tests; excludes the manual browser walkthrough) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest -q`
- **After every plan wave:** Run `cd backend && uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green, plus the manual browser redirect-flow walkthrough (01-08-PLAN checkpoint, not automated this phase)
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-T3 | 01-01 | 1 | AUTH-01 | infra | `cd backend && uv run pytest tests/test_smoke.py -q` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-04-T2 | 01-04 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_auth_gating.py::test_unauthenticated_request_rejected -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-04-T1 | 01-04 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_bearer_auth.py::test_valid_jwt_accepted -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-04-T1 | 01-04 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_bearer_auth.py::test_invalid_jwt_rejected_wrong_algorithm -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-05-T1 | 01-05 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_auth_callback.py::test_first_login_creates_user -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-05-T1 | 01-05 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_auth_callback.py::test_repeat_login_reuses_user -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-05-T2 | 01-05 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_session_service.py::test_create_session_sets_expiry -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-05-T2 | 01-05 | 2 | AUTH-01 | unit | `cd backend && uv run pytest tests/test_session_service.py::test_delete_session_removes_row -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-06-T2 | 01-06 | 3 | AUTH-01 | integration | `cd backend && uv run pytest tests/test_auth_callback.py::test_full_callback_flow_creates_session_and_cookie -x` | ❌ (planned, not yet executed) | ⬜ pending |
| 01-06-T2 | 01-06 | 3 | AUTH-01 | integration | `cd backend && uv run pytest tests/test_auth_gating.py -k test_health_endpoint_requires_auth -x` | ❌ (planned, not yet executed) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task/Plan/Wave IDs reconciled against the 8 finalized PLAN.md files (01-01 through 01-08). "File Exists" reflects that `backend/`/`frontend`/`docker-compose.yml` do not yet exist on disk — this phase has been planned but not yet executed.*

---

## Wave 0 Requirements

Wave 1 (01-01-PLAN, 01-02-PLAN, 01-03-PLAN — the three plans with no `depends_on`) is this phase's Wave-0-equivalent foundation wave:

- [x] `backend/pyproject.toml` — adds `pytest`, `pytest-asyncio`, `httpx`, `cryptography` as dev dependencies (01-01-PLAN Task 1)
- [x] `backend/tests/conftest.py` — shared fixtures: `db_session` (Postgres via docker-compose, for parity with Alembic/Postgres-specific types), `client` (FastAPI `TestClient`), `rsa_keypair` + `mint_test_jwt` + `mock_jwks_client` (JWT-minting/mocked-JWKS for bearer-token tests) (01-01-PLAN Task 3)
- [x] `backend/tests/test_auth_gating.py` (01-04-PLAN Task 2), `backend/tests/test_bearer_auth.py` (01-04-PLAN Task 1), `backend/tests/test_auth_callback.py` (01-05-PLAN Task 1, extended by 01-06-PLAN Task 2), `backend/tests/test_session_service.py` (01-05-PLAN Task 2) — all planned as new files
- [x] Spike: Authlib's exact PKCE-enabling kwarg (`code_challenge_method: "S256"`) addressed in 01-06-PLAN Task 1's action notes, with a manual spot-check (`curl .../auth/login -I` confirming `code_challenge=` on the redirect) called out in that plan's `<verification>` section
- [x] Spike: Keycloak's default `aud` claim / audience-mapper requirement addressed via the explicit `oidc-audience-mapper` protocol mapper baked into 01-02-PLAN's realm-export JSON

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full browser redirect flow (login → Keycloak → callback → session cookie set → reaches platform) | AUTH-01 | No E2E framework exists yet; redirect-to-third-party-IdP flow is inherently awkward to automate reliably in CI without a dedicated test realm — out of scope to stand up fresh in Phase 1 | Covered by 01-08-PLAN Task 2 (checkpoint:human-verify): start `docker compose up` (Keycloak + Postgres), start backend + frontend dev servers, open the SPA in a browser, click login, authenticate against the local Keycloak test realm/user, confirm redirect back to the app and that an authenticated view is reachable. Confirm the httpOnly session cookie is set (DevTools Application tab) and that logging out invalidates it (DB row deleted, subsequent request rejected). |
| Multiple distinct users can each authenticate under their own identity | AUTH-01 | Requires two separate real login sessions (e.g. two browser profiles or one regular + one incognito window) against two different Keycloak test users — not meaningfully unit-testable | Covered by 01-08-PLAN Task 2, step 6: log in as `alice@example.com` in one browser session and `bob@example.com` in another (both provisioned in 01-02-PLAN's realm-export JSON); confirm each reaches the platform under their own local user record (distinct `sub`/email), and that each session cookie only authenticates its own user. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (the sole exception, 01-08-PLAN Task 2, explicitly documents `MISSING — manual browser walkthrough only, per 01-VALIDATION.md Manual-Only Verifications` per the Nyquist rule format)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (only 01-08-PLAN Task 2 lacks one, immediately preceded by 01-08-PLAN Task 1's automated `curl` check)
- [x] Wave 0 covers all MISSING references (Wave 1 — 01-01/01-02/01-03 — establishes pytest infra, JWT/JWKS fixtures, Docker/Keycloak/Postgres stack, and frontend scaffold before any dependent plan runs)
- [x] No watch-mode flags (all commands use `-q`/`-x`, no `--watch`)
- [x] Feedback latency < 20s (full suite estimated ~10-20s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
