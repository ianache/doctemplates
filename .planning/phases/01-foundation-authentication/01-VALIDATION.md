---
phase: 1
slug: foundation-authentication
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10-20 seconds (unit + mocked-JWKS integration tests; excludes the manual browser walkthrough) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green, plus the manual browser redirect-flow walkthrough (not automated this phase)
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-xx-xx | TBD | 0 | AUTH-01 | infra | `uv add pytest pytest-asyncio --dev` | ❌ W0 | ⬜ pending |
| 01-xx-xx | TBD | 0 | AUTH-01 | unit | `uv run pytest tests/test_auth_gating.py::test_unauthenticated_request_rejected -x` | ❌ W0 | ⬜ pending |
| 01-xx-xx | TBD | TBD | AUTH-01 | unit | `uv run pytest tests/test_bearer_auth.py::test_valid_jwt_accepted -x` | ❌ W0 | ⬜ pending |
| 01-xx-xx | TBD | TBD | AUTH-01 | unit | `uv run pytest tests/test_bearer_auth.py::test_invalid_jwt_rejected -x` | ❌ W0 | ⬜ pending |
| 01-xx-xx | TBD | TBD | AUTH-01 | integration | `uv run pytest tests/test_auth_callback.py::test_first_login_creates_user -x` | ❌ W0 | ⬜ pending |
| 01-xx-xx | TBD | TBD | AUTH-01 | integration | `uv run pytest tests/test_auth_callback.py::test_repeat_login_reuses_user -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Exact Task IDs/Plan/Wave columns to be filled in by the planner once PLAN.md files exist.*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — add `pytest`, `pytest-asyncio` as dev dependencies (currently absent — no test infra exists yet)
- [ ] `tests/conftest.py` — shared fixtures: test DB session (Postgres via docker-compose, for parity with Alembic/Postgres-specific types), FastAPI `TestClient`/`AsyncClient`, a helper to mint locally-signed test JWTs + a mocked JWKS endpoint for bearer-token tests
- [ ] `tests/test_auth_gating.py`, `tests/test_bearer_auth.py`, `tests/test_auth_callback.py` — new files, none exist
- [ ] Spike: confirm Authlib's exact PKCE-enabling kwarg (`code_challenge_method: "S256"` assumed) and nonce-validation behavior against the real local Keycloak container before relying on it in later waves
- [ ] Spike: confirm Keycloak's default `aud` claim value / audience-mapper requirement against the real local Keycloak container before finalizing the bearer-validation dependency's `audience=` parameter (may need to validate against `azp` instead)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full browser redirect flow (login → Keycloak → callback → session cookie set → reaches platform) | AUTH-01 | No E2E framework exists yet; redirect-to-third-party-IdP flow is inherently awkward to automate reliably in CI without a dedicated test realm — out of scope to stand up fresh in Phase 1 | Start `docker compose up` (Keycloak + Postgres), start backend + frontend dev servers, open the SPA in a browser, click login, authenticate against the local Keycloak test realm/user, confirm redirect back to the app and that an authenticated view is reachable. Confirm the httpOnly session cookie is set (DevTools Application tab) and that logging out invalidates it (DB row deleted, subsequent request rejected). |
| Multiple distinct users can each authenticate under their own identity | AUTH-01 | Requires two separate real login sessions (e.g. two browser profiles or one regular + one incognito window) against two different Keycloak test users — not meaningfully unit-testable | Log in as Test User A in one browser session and Test User B in another; confirm each reaches the platform under their own local user record (distinct `sub`/email), and that each session cookie only authenticates its own user. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
