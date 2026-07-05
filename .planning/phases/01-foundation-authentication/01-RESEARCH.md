# Phase 1: Foundation & Authentication - Research

**Researched:** 2026-07-05
**Domain:** OIDC/OAuth2 authentication (Keycloak + FastAPI + React SPA), monorepo foundation, PostgreSQL/SQLAlchemy/Alembic setup
**Confidence:** MEDIUM-HIGH (core auth flow verified against official docs; some library-internals details — e.g. exact Authlib nonce/PKCE code — could not be fetched directly and rely on cross-checked training knowledge, flagged accordingly)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Frontend Architecture**
- D-01: Frontend framework is React.
- D-02: Architecture is a separate SPA + API — decoupled frontend build (e.g. Vite) talking to the FastAPI backend, not a full-stack meta-framework (no Next.js/Nuxt SSR layer). Rationale: internal operational tool (no SEO/SSR need); Phase 6's generation API must remain independent of any UI rendering server.
- D-03: Single monorepo — frontend/ and backend/ folders live in this same repository, not separate repos.
- D-04: Claude's Discretion — specific UI component library/design system, chosen once the framework is in place, suited to admin/dashboard tools with drag-and-drop needs (Phase 4 lookahead).

**OIDC Provider & Login Flow**
- D-05: OIDC identity provider is self-hosted Keycloak — Docker for local dev, self-hosted in prod.
- D-06: Login flow is redirect-based: Authorization Code + PKCE. No popup-based login.
- D-07: Platform maintains a local user record linked to the IdP identity (sub claim, email, created-at) created on first login. Needed starting Phase 2 to attribute document types/designs to a user, even though fine-grained roles/permissions (AUTH-02) are deferred to v2.

**Session & API Auth Strategy**
- D-08: Browser UI authentication is a backend-issued httpOnly, secure session cookie, set after the backend validates the OIDC token from the redirect callback. The frontend SPA never handles raw IdP tokens directly.
- D-09: External API callers (relevant starting Phase 6) authenticate via an OIDC-issued bearer token (e.g. client-credentials grant for machine-to-machine callers), validated independently of the browser session cookie mechanism. No separate/parallel API-key system — one OIDC-based auth mechanism for both UI and API callers, satisfying AUTH-01 for all access paths.

**Database & Persistence Foundation**
- D-10: PostgreSQL is the platform's database, used across all phases.
- D-11: Alembic manages schema migrations.

### Claude's Discretion
- Specific UI component library/design system (D-04).
- Migration tooling specifics beyond "Alembic" — e.g. exact ORM/DB access layer choice (SQLAlchemy assumed but not explicitly locked).
- Exact local user table schema (columns beyond subject ID/email/created-at).
- Docker/local-dev setup mechanics for Keycloak (compose file, realm bootstrap approach).

### Deferred Ideas (OUT OF SCOPE)
- Fine-grained roles/permissions per document type or design (AUTH-02) — deferred to v2; local user record (D-07) designed to make this addition straightforward later.
- Choice of a specific third-party OIDC SaaS provider (Auth0/Okta) — self-hosted Keycloak was chosen instead; revisit only if a future deployment constraint requires a managed IdP.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Multi-user access is gated behind an OAuth2/OIDC login flow (generic identity provider integration, not custom-built credentials) | Covered by: Keycloak Docker local-dev setup, Authlib-based Authorization Code + PKCE redirect flow, backend session-cookie issuance pattern, independent bearer-token validation via PyJWT+JWKS for API callers, local user upsert-on-first-login pattern. See Standard Stack, Architecture Patterns, Code Examples, Common Pitfalls below. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No custom credential storage** — auth must integrate an external OAuth2/OIDC identity provider; platform never owns passwords (repeats PROJECT.md constraint, reinforced by CLAUDE.md "Critical Business Rules" intent for auth).
- **headroom-ai is dev tooling only** — `headroom-ai[all]>=0.30.0` in `pyproject.toml` is a token-optimization CLI for this project's own development, NOT a product dependency. FastAPI/Uvicorn/HTTPx are currently only available *transitively* through it — the plan MUST add them as explicit, direct dependencies in `pyproject.toml` rather than relying on the transitive install.
- **No formatter/linter configured** — no black/ruff/flake8 present. If the plan introduces one, it's a net-new convention, not enforcement of an existing one.
- **No type hints established** — codebase currently has none (5-line stub), but Python 3.12+ is available; using modern type hints in new code does not conflict with any existing convention.
- **Python 3.12+ required** — `.python-version` pins 3.12; `pyproject.toml` requires `>=3.12`. Local Python interpreter for the assistant's shell resolved to 3.13.14, but `uv` will respect `.python-version`/`pyproject.toml` constraints when creating the project venv — plan should keep target at 3.12 unless there's a specific reason to bump it.
- **GSD workflow enforcement** — direct file edits outside a GSD command are disallowed; this is process guidance for the orchestrator/executor, not a technical constraint on the phase's implementation itself.
- **Windows 11 dev environment** — local dev commands/scripts should be Windows-shell-compatible (or documented for Git Bash), particularly Docker Compose invocation and any Makefile-style helper scripts.

## Summary

Phase 1 needs three things working together: (1) a self-hosted Keycloak instance reachable from a FastAPI backend, (2) a FastAPI-driven Authorization Code + PKCE redirect flow that never exposes raw IdP tokens to the React SPA, and (3) an independent bearer-token validation path for future machine-to-machine API callers using the same Keycloak realm. All three are well-trodden patterns with mature, actively-maintained libraries — this is not a domain requiring custom protocol implementation.

The standard toolchain is: **Authlib** (`authlib`) for the browser-facing OIDC client (handles discovery, state/PKCE/nonce bookkeeping via Starlette's `SessionMiddleware`, and ID-token validation on the callback), **PyJWT** with `PyJWKClient` for independent bearer-token validation (JWKS-based signature verification, no per-request round trip to Keycloak), **SQLAlchemy 2.0** (declarative `Mapped`/`mapped_column` style) + **Alembic** for the Postgres schema, and a hand-rolled DB-backed session table (not a third-party session library — the one obvious candidate, `fastapi-sessions`, is archived/unmaintained since 2023) for the httpOnly cookie backing the browser session.

**Primary recommendation:** Use Authlib for the Authorization Code + PKCE redirect/callback against Keycloak's discovery document, issue a custom DB-backed session (random opaque token in an httpOnly/secure/SameSite=Lax cookie, mapped to a `sessions` table row referencing the local `users` table), and validate bearer tokens for API callers with PyJWT + `PyJWKClient` against the same realm's JWKS endpoint — one Keycloak realm, two independently-implemented validation paths, satisfying D-08/D-09 exactly as decided.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.139.0 (verified via PyPI, 2026-07) | Backend web framework | Already available transitively; project constraint requires promoting to direct dependency |
| uvicorn | 0.50.0 | ASGI server | Standard FastAPI production/dev server |
| authlib | 1.7.2 | OIDC client (Authorization Code + PKCE, discovery, ID-token validation) | Actively maintained (last push 2026-06-19, 5.3k+ GitHub stars), first-class Starlette/FastAPI integration, handles PKCE/state/nonce bookkeeping so the app doesn't hand-roll OAuth2 protocol logic |
| pyjwt | 2.13.0 | Independent bearer-token (JWT) signature + claims validation for API callers | Actively maintained (last push 2026-06-29), `PyJWKClient` gives JWKS-based key resolution + caching without a network call per request |
| sqlalchemy | 2.0.51 | ORM / DB access layer | Modern typed declarative style (`Mapped`/`mapped_column`), works with both sync and async engines, pairs directly with Alembic |
| alembic | 1.18.5 | Schema migrations | Locked by D-11; standard companion to SQLAlchemy |
| psycopg[binary] | 3.3.4 (psycopg v3) | PostgreSQL driver | Native SQLAlchemy 2.0 dialect `postgresql+psycopg`; psycopg3 supports async natively if the app later needs `create_async_engine` — sync mode is sufficient and simpler for Phase 1 |
| pydantic-settings | 2.14.2 | Typed environment/config loading (`.env` → settings object) | Standard FastAPI-ecosystem pattern for OIDC issuer URL, client ID/secret, DB URL, session secret |
| itsdangerous | 2.2.0 | Required by Starlette's `SessionMiddleware` (used only for transient OAuth handshake state, not the app's long-lived session) | Starlette hard-dependency for `SessionMiddleware`; already needed transitively once `SessionMiddleware` is added |
| python-dotenv | 1.2.2 | Local `.env` loading | Common pairing with pydantic-settings for local dev |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 | HTTP client | Already available transitively; Authlib's async OAuth client uses httpx under the hood; also useful for calling Keycloak's admin/token endpoints directly if needed |
| pytest | 9.1.1 | Test runner | Wave 0 gap — no test infra exists yet (see Validation Architecture) |
| pytest-asyncio | 1.4.0 | Async test support | Needed for testing async FastAPI routes/dependencies |

### Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.7 | UI framework | Locked by D-01 |
| react-dom | 19.2.7 | React DOM renderer | Pairs with react |
| vite | 8.1.3 | Dev server/bundler | Locked by D-02 (decoupled SPA build); requires Node >=20.19 or >=22.12 (verified: Node 22.14.0 available locally, satisfies requirement) |
| @vitejs/plugin-react | 6.0.3 | Vite React plugin (JSX, Fast Refresh) | Official Vite React template dependency |
| typescript | 6.0.3 | Type checking | Not explicitly locked, but strongly recommended given no existing frontend conventions to conflict with, and this is a multi-phase project (designer canvas in Phase 4 benefits from typed props) |
| react-router-dom | 7.18.1 | Client-side routing (login redirect landing, protected app shell) | De facto standard for React SPA routing; needed to distinguish "logged out" vs "app" views |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Authlib (OIDC client) | Hand-rolled `httpx` calls to Keycloak's token/authorize endpoints | Authlib handles PKCE code_verifier generation/storage, state/nonce anti-CSRF, and ID-token signature+claims validation automatically; hand-rolling this is exactly the kind of security-sensitive protocol code that should not be custom-built |
| PyJWT + PyJWKClient (bearer validation) | python-jose | python-jose has multiple confirmed CVEs including an algorithm-confusion vulnerability (GHSA-6c5p-j8vq-pqhj) and a timing-attack HMAC comparison issue (GHSA-w799-prg3-cx77); it is also FastAPI's historical tutorial choice but is less actively aligned with current security practice than PyJWT. PyJWT is recommended, with strict `algorithms=[...]` allowlisting regardless of choice (both libraries have had allowlist-bypass-class CVEs historically — always pin latest version) |
| Hand-rolled DB-backed session table | `fastapi-sessions` package | Archived on GitHub (last push 2023-07-11) — not a viable dependency. A `sessions` table (opaque random token cookie → row with user_id/expires_at) is simple enough that hand-rolling is the correct call here, not "reinventing a wheel" |
| psycopg (v3) | psycopg2-binary | psycopg3 is the SQLAlchemy 2.0-era recommended driver with native async support if ever needed later; psycopg2 is legacy-maintenance-mode. No reason to pick psycopg2 for greenfield code |
| shadcn/ui or Mantine (component library, D-04) | Ship Phase 1 with no component library | Phase 1 only needs a login screen + a minimal authenticated shell — recommend deferring the formal D-04 pick to Phase 4 planning (when the drag-and-drop designer's concrete needs are known) rather than locking in now. If a decision is wanted sooner: shadcn/ui (Radix + Tailwind, copy-in components, no runtime dependency lock-in) and Mantine (batteries-included, good forms/hooks) are the two leading current candidates for admin/dashboard tooling — tradeoff is Tailwind-adoption cost (shadcn) vs. bundle size/opinionation (Mantine) |

**Installation (backend):**
```bash
uv add fastapi uvicorn[standard] authlib pyjwt sqlalchemy alembic "psycopg[binary]" pydantic-settings python-dotenv
uv add --dev pytest pytest-asyncio httpx
```

**Installation (frontend, inside `frontend/`):**
```bash
npm create vite@latest frontend -- --template react-ts
npm install react-router-dom
```

**Version verification:** All versions above were verified against the PyPI/npm registries directly (2026-07-05), not from training-data memory. Given `uv.lock` doesn't yet pin these (they aren't declared dependencies), running `uv add` will resolve to current-compatible versions at plan-execution time — treat the table above as "confirmed available as of research date," re-check via `uv add` output at execution time rather than hardcoding these exact patch versions in any lockfile-adjacent documentation.

## Architecture Patterns

### Recommended Project Structure
```
.
├── backend/
│   ├── pyproject.toml            # backend-specific deps (or keep at repo root — see note)
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   └── app/
│       ├── main.py               # FastAPI app instance, middleware wiring
│       ├── config.py             # pydantic-settings Settings class
│       ├── db.py                 # engine/session factory
│       ├── models/
│       │   ├── user.py
│       │   └── session.py
│       ├── auth/
│       │   ├── oidc.py           # Authlib OAuth registry (Keycloak client)
│       │   ├── routes.py         # /auth/login, /auth/callback, /auth/logout
│       │   ├── dependencies.py   # get_current_user (cookie-based), verify_bearer_token (JWKS-based)
│       │   └── jwks.py           # PyJWKClient wrapper for independent bearer validation
│       └── api/
│           └── health.py         # simple authenticated ping/health endpoint to prove gating works
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # route switch: logged-out landing vs authenticated shell
│       └── lib/api.ts            # fetch wrapper with credentials: 'include'
├── docker-compose.yml            # Keycloak + Postgres for local dev
├── .env.example
└── .planning/                    # (existing GSD planning artifacts)
```

**Note on backend `pyproject.toml` location:** the repo root already has a `pyproject.toml` (project `29-docmanagemet`, only dependency `headroom-ai[all]`). Two viable options: (a) keep backend code and dependencies at repo root (simplest — `backend/` becomes just an `app/` package under root, no separate `pyproject.toml`), or (b) make `backend/` a proper sub-project with its own `pyproject.toml`/`uv.lock`, keeping the root `pyproject.toml` purely for dev tooling (`headroom-ai`). Given `headroom-ai[all]` is explicitly *not* a product dependency per CLAUDE.md, **option (b) is cleaner** — it fully separates "tools I use to build this" from "what the product depends on" and avoids the transitive-FastAPI confusion the CONTEXT.md already flagged. This is a planning decision, not fully locked by CONTEXT.md; flagging for the planner to confirm.

### Pattern 1: Backend-driven Authorization Code + PKCE (Authlib)
**What:** FastAPI registers Keycloak as an OAuth client via its OIDC discovery document; `/auth/login` redirects the browser to Keycloak; `/auth/callback` exchanges the code for tokens, validates the ID token, upserts the local user, and issues the app's own session cookie.
**When to use:** All browser-based login (D-06, D-08).
**Example (verified pattern from Authlib official docs, adapted from the Starlette/FastAPI integration guide fetched 2026-07-05):**
```python
# Source: https://docs.authlib.org/en/stable/oauth2/client/web/fastapi.html
# and https://github.com/authlib/demo-oauth-client (fastapi-google-login)
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)  # transient OAuth state only

oauth = OAuth()
oauth.register(
    name="keycloak",
    server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    client_kwargs={
        "scope": "openid email profile",
        "code_challenge_method": "S256",  # enables PKCE — MEDIUM confidence, cross-check at implementation time
    },
)

@app.get("/auth/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.keycloak.authorize_access_token(request)  # validates ID token signature, iss, nonce, exp
    userinfo = token["userinfo"]  # sub, email, etc.
    # upsert local user by userinfo["sub"], create app session row, set httpOnly cookie, redirect to frontend
```
**Confidence note:** The `authorize_redirect`/`authorize_access_token` call shapes and `SessionMiddleware` requirement are confirmed directly from official Authlib docs and the official demo repo (fetched 2026-07-05). The exact `code_challenge_method` kwarg name for enabling PKCE and the precise nonce-validation internals were NOT found in the fetched doc excerpts (pages returned partial/compressed content) — this is MEDIUM confidence from cross-referenced community knowledge, not confirmed line-by-line in official docs. **Validate this specific kwarg during Wave 0 spike** before relying on it in later waves.

### Pattern 2: Independent bearer-token validation for API callers (PyJWT + JWKS)
**What:** A separate FastAPI dependency validates `Authorization: Bearer <token>` headers by fetching Keycloak's JWKS, matching the token's `kid`, verifying signature/issuer/audience/expiry — no shared code path with the cookie-session dependency, no network round-trip to Keycloak per request (JWKS cached).
**When to use:** External API callers (D-09) — relevant from Phase 6 onward, but the validation dependency should be built in Phase 1 alongside the cookie-session path so both auth mechanisms exist and are provably independent per AUTH-01's "unauthenticated requests to the platform (UI and API) are rejected."
**Example (verified against official PyJWT docs, fetched 2026-07-05):**
```python
# Source: https://pyjwt.readthedocs.io/en/stable/usage.html
import jwt
from jwt import PyJWKClient

jwks_client = PyJWKClient(f"{settings.oidc_issuer}/protocol/openid-connect/certs")

def verify_bearer_token(token: str) -> dict:
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],          # explicit allowlist — never omit
        audience=settings.oidc_client_id,   # see Pitfall: Keycloak audience mapping below
        issuer=settings.oidc_issuer,
    )
```

### Pattern 3: DB-backed session (not a signed-cookie-only session)
**What:** `sessions` table (`id` opaque random token, `user_id` FK, `created_at`, `expires_at`), cookie holds only the opaque `id`. Enables real logout (delete row) and server-side expiry control, unlike a stateless signed cookie.
**When to use:** The long-lived app session cookie (D-08). NOT the same as Starlette's `SessionMiddleware` (that one is only for the few seconds of OAuth-handshake temp state — a separate, unrelated cookie).
**Rationale:** `fastapi-sessions` (the one existing library for this) is archived since 2023 — this is a "don't hand-roll... except when the only library option is dead" case. A sessions table is simple enough (few columns, two queries: create-on-callback, lookup-on-request) that hand-rolling is the right call, not a violation of "don't hand-roll" philosophy.

### Anti-Patterns to Avoid
- **Storing the raw Keycloak access/ID/refresh token in a cookie sent to the browser:** violates D-08 ("frontend SPA never handles raw IdP tokens directly") and needlessly widens the token's exposure surface. Only the opaque app-session ID should reach the browser.
- **Using Starlette's `SessionMiddleware` cookie as the actual app session:** it's signed-but-not-encrypted client-side storage with no server-side revocation — fine for transient OAuth state (a few seconds), wrong for a long-lived authenticated session where logout must actually work.
- **Validating bearer tokens via Keycloak's introspection endpoint on every request:** Keycloak's own docs flag this as unnecessarily slow/load-bearing on the IdP at scale; local JWKS-based validation is the documented recommended approach.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth2/OIDC Authorization Code + PKCE protocol logic (state, nonce, code_verifier/code_challenge, ID-token validation) | Custom `httpx` calls to Keycloak endpoints with manual PKCE math | Authlib | Security-critical protocol code; a subtle bug (e.g. skipped nonce check) reopens CSRF/replay attack surface. Authlib is the maintained, widely-used option for exactly this |
| JWKS fetching/caching/key-matching for bearer-token validation | Manual `httpx` GET to `/certs` + manual `kid` matching + manual cache invalidation | PyJWT's `PyJWKClient` | Handles key-id matching, caching, and refresh-on-miss automatically; hand-rolled caching is an easy source of stale-key or unbounded-refetch bugs |
| Password/credential storage | Any local password field/hash | N/A — explicitly out of scope; Keycloak owns credentials entirely | Locked project constraint: "no custom-built credentials" |

**Key insight:** Everything protocol-level (PKCE, nonce, JWKS) has mature libraries; the only thing genuinely worth hand-rolling here is the trivial app-session table, precisely because the "standard" library for that (`fastapi-sessions`) is dead.

## Common Pitfalls

### Pitfall 1: Keycloak's default access-token audience isn't the calling client's client_id
**What goes wrong:** Validating a bearer token with `audience=<your_client_id>` fails even for a correctly-issued Keycloak token.
**Why it happens:** Keycloak's default `aud` claim behavior does not automatically include the requesting client's client_id unless a dedicated "audience" protocol mapper is added to that client (this is a widely-reported Keycloak configuration gotcha in the community, and Keycloak's own admin guide has a dedicated "Audience support" section for it — full mapper-configuration text could not be fetched in this research pass, so this is MEDIUM confidence, verify hands-on during Wave 0).
**How to avoid:** When configuring the Keycloak client used for machine-to-machine calls, add an explicit Audience protocol mapper (or validate against the `azp` — authorized party — claim instead of `aud`, if that fits the token shape better). Write a Wave 0 spike test that actually decodes a real token from a local Keycloak instance before writing the "real" validation dependency.
**Warning signs:** `InvalidAudienceError` on tokens that otherwise look correctly signed and issued.

### Pitfall 2: Wildcard CORS + credentials silently breaks cross-origin cookies
**What goes wrong:** `allow_origins=["*"]` with `allow_credentials=True` looks like it should work in local dev but the browser refuses to attach cookies/Authorization headers.
**Why it happens:** Per the CORS spec (confirmed via official FastAPI docs, fetched 2026-07-05): none of `allow_origins`, `allow_methods`, `allow_headers` may be `"*"` when `allow_credentials=True` — browsers ignore/reject wildcard origin when credentials are involved.
**How to avoid:** Explicitly list `http://localhost:5173` (Vite dev server) — and the real frontend origin(s) in prod — in `allow_origins`; keep `allow_credentials=True`.
**Warning signs:** Login flow appears to succeed (redirect happens, callback returns 200) but subsequent authenticated API calls from the SPA silently come back as 401 because the session cookie never actually reached the backend.

### Pitfall 3: `SessionMiddleware`'s cookie is not the app session
**What goes wrong:** Reusing Starlette's `SessionMiddleware` session (added only to support Authlib's OAuth handshake bookkeeping) as the actual long-lived login session.
**Why it happens:** It's the cookie mechanism that's already "there" once Authlib is wired up, so it's tempting to just keep storing `user` data in it.
**How to avoid:** Treat `SessionMiddleware`'s cookie as scoped strictly to the OAuth handshake (a few seconds, cleared after `authorize_access_token` completes). Issue a second, separate httpOnly/secure/SameSite cookie backed by the `sessions` DB table for the actual authenticated session, per Pattern 3 above.
**Warning signs:** Logout doesn't actually invalidate anything server-side; a captured cookie remains valid until its client-side signed expiry, with no way to revoke early.

### Pitfall 4: JWT library algorithm-confusion / allowlist-bypass CVEs
**What goes wrong:** An attacker crafts a token using an unexpected algorithm (e.g. presenting an RSA public key as an HMAC secret) that a lax `jwt.decode()` call accepts.
**Why it happens:** Both python-jose (GHSA-6c5p-j8vq-pqhj, algorithm confusion with ECDSA keys) and PyJWT itself (GHSA-jq35-7prp-9v3f, algorithm allow-list bypass with PyJWK/PyJWKClient; GHSA-xgmm-8j9v-c9wx, public JWK accepted as HMAC secret) have had CVEs in this exact family — confirmed via OSV.dev query 2026-07-05.
**How to avoid:** Always pass an explicit `algorithms=["RS256"]` (never omit, never allow `["RS256", "HS256"]` mixed families unless truly needed), and pin PyJWT to the latest patched version (2.13.0 as of this research) rather than an old pinned version.
**Warning signs:** N/A pre-emptively — this is a "always do it right the first time" class of pitfall; verify by writing a test that a token signed with an unexpected algorithm/key type is rejected.

### Pitfall 5: `localhost` cross-port cookie + SameSite confusion in dev
**What goes wrong:** Assuming a cookie set by the backend (`localhost:8000`) won't reach the frontend (`localhost:5173`) because they're "different origins," and over-engineering a workaround (e.g. `SameSite=None` + always-Secure, which then requires HTTPS even in dev).
**Why it happens:** Same-Site is determined by the registrable domain (eTLD+1), not full origin — `localhost:5173` and `localhost:8000` are same-site (though cross-origin for CORS purposes). `SameSite=Lax` cookies ARE sent on same-site cross-origin `fetch()`/XHR requests (the Lax restriction targets cross-site top-level navigation quirks, not same-site subresource requests).
**How to avoid:** Use `SameSite=Lax` (not `None`) for local dev; ensure the frontend's `fetch` calls include `credentials: 'include'`; modern browsers also treat `http://localhost` as a secure context, so `Secure` cookies generally still work in local dev without HTTPS — but confirm this in the actual browser used for testing, and don't assume it holds for `127.0.0.1` the same way as `localhost`.
**Warning signs:** Cookie appears set (visible in DevTools Application tab) but never arrives on subsequent API requests from the SPA.

## Code Examples

Verified patterns from official sources (also see Architecture Patterns above for the primary login/callback and bearer-validation examples):

### CORS configuration for Vite SPA + credentials
```python
# Source: https://fastapi.tiangolo.com/tutorial/cors/ (fetched 2026-07-05)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # exact origin, no wildcard — required for credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### SQLAlchemy 2.0 declarative model style
```python
# Source: https://docs.sqlalchemy.org/en/20/orm/quickstart.html (fetched 2026-07-05)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sub: Mapped[str] = mapped_column(unique=True, index=True)  # IdP subject claim
    email: Mapped[str]
    created_at: Mapped[datetime]
```

### Keycloak local dev container (verified against official Keycloak container docs, fetched 2026-07-05)
```yaml
# docker-compose.yml (excerpt)
services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    command: start-dev --import-realm
    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: admin
      KC_BOOTSTRAP_ADMIN_PASSWORD: change_me
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./keycloak/import:/opt/keycloak/data/import
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: docmanagement
      POSTGRES_PASSWORD: change_me
      POSTGRES_DB: docmanagement
    ports:
      - "127.0.0.1:5432:5432"
```
**Note:** `--import-realm` + a mounted realm export JSON in `keycloak/import/` is the documented way to bootstrap a realm/client/test-users automatically on container start — addresses the "Docker/local-dev setup mechanics for Keycloak (realm bootstrap approach)" discretion item from CONTEXT.md. Recommend committing a realm-export JSON (with test users, a confidential client for the backend, and a client-credentials client for future M2M testing) to the repo so `docker compose up` produces a ready-to-use realm with no manual admin-console clicking.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT/JWKS handling in FastAPI tutorials | PyJWT + PyJWKClient | python-jose has had unpatched-feeling CVE history (multiple OSV entries, last meaningful activity slower); PyJWT is more actively maintained (pushed 2026-06-29) | Plans/tutorials referencing FastAPI's official security tutorial (which historically used python-jose) should not be followed verbatim for the JWT library choice |
| `fastapi-sessions` for cookie session management | Hand-rolled DB-backed session table | Library archived 2023-07-11 | Any tutorial/blog post recommending `fastapi-sessions` is now recommending a dead dependency |
| psycopg2 as the default SQLAlchemy Postgres driver | psycopg (v3) | SQLAlchemy 2.0 (2023) added first-class psycopg3 dialect support | New projects should default to psycopg3 unless there's a specific compatibility reason not to |

**Deprecated/outdated:**
- `python-jose`: not deprecated outright, but no longer the recommended default for new FastAPI+OIDC projects given its CVE history vs. PyJWT's more current posture.
- `fastapi-sessions`: effectively abandoned (archived), do not add as a dependency.

## Open Questions

1. **Exact Authlib PKCE-enabling kwarg and nonce-validation internals**
   - What we know: Authlib's Starlette/FastAPI integration handles `authorize_redirect`/`authorize_access_token` and requires `SessionMiddleware` for temp state storage (confirmed via official docs).
   - What's unclear: The precise `client_kwargs` key to force PKCE (`code_challenge_method: "S256"` is the community-standard approach, but the fetched doc excerpts didn't show it verbatim) and how strictly the nonce is validated automatically on `authorize_access_token` vs. requiring a separate `parse_id_token` call.
   - Recommendation: Spike this in Wave 0 — write a throwaway script that performs the full redirect flow against the local Keycloak container and inspect exactly what `token` and `token["userinfo"]` contain, confirm PKCE is actually being used (inspect the actual authorize request URL for `code_challenge`).

2. **Keycloak audience mapper configuration specifics**
   - What we know: Keycloak has a dedicated "Audience support" admin-guide section and protocol-mapper mechanism; local JWKS validation is the documented recommended approach over introspection.
   - What's unclear: Exact default `aud` claim value for a fresh Keycloak client (commonly reported as `"account"` in community sources, not confirmed in official docs fetched this session) and the exact steps to add a client-specific audience mapper via the admin console/realm-export JSON.
   - Recommendation: Confirm hands-on against the actual local Keycloak container in Wave 0 before finalizing the bearer-validation dependency's `audience=` parameter — may need to validate against `azp` instead, or add an explicit mapper in the realm-export JSON.

3. **Repo layout: single root `pyproject.toml` vs. separate `backend/pyproject.toml`**
   - What we know: Root `pyproject.toml` currently only declares `headroom-ai[all]` (dev tooling, not product).
   - What's unclear: Whether the team prefers a single Python project (simpler `uv` workflow, root-level venv) or the cleaner separation of `backend/` as its own sub-project.
   - Recommendation: Planner should decide explicitly in Wave 0 rather than leaving implicit — this affects every subsequent phase's file paths.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Keycloak + Postgres local dev | ✓ | 29.4.1 (Docker Desktop, daemon running) | — |
| Node.js | Vite frontend | ✓ | 22.14.0 | — (satisfies Vite's >=20.19/>=22.12 requirement) |
| npm | Frontend package management | ✓ | 11.9.0 | — |
| Python | Backend | ✓ | 3.13.14 (interpreter on PATH); project pins 3.12 via `.python-version`/`pyproject.toml` | `uv` will provision the correct 3.12 venv per project config — no action needed, but don't assume the ad-hoc shell `python3` is the project interpreter |
| uv | Python package/venv management | ✓ | 0.9.8 | — |
| PostgreSQL (local CLI/server) | DB | ✗ (no local `psql`/`pg_isready`) | — | Run via Docker Compose alongside Keycloak (see Code Examples) — no bare-metal Postgres install needed |
| Keycloak (running instance) | OIDC provider | ✗ (not yet started) | — | Bring up via `docker compose up` as part of Wave 0 — this IS part of the phase's deliverable, not a missing external dependency |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** PostgreSQL and Keycloak are not yet running locally, but both have a clear, already-verified fallback (Docker Compose, confirmed Docker daemon is live) — standing these up is itself part of this phase's Wave 0 work, not a blocker.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (not yet installed — Wave 0 gap) |
| Config file | none — see Wave 0 Gaps |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Unauthenticated request to a protected API route is rejected (401/redirect) | unit/integration | `uv run pytest tests/test_auth_gating.py::test_unauthenticated_request_rejected -x` | ❌ Wave 0 |
| AUTH-01 | Bearer token with valid Keycloak-issued JWT is accepted by the independent validation dependency | unit | `uv run pytest tests/test_bearer_auth.py::test_valid_jwt_accepted -x` (use a locally-generated RSA keypair + mocked JWKS response, not a live Keycloak call, for speed) | ❌ Wave 0 |
| AUTH-01 | Bearer token with wrong algorithm/signature/audience/issuer is rejected | unit | `uv run pytest tests/test_bearer_auth.py::test_invalid_jwt_rejected -x` | ❌ Wave 0 |
| AUTH-01 | First-time login via OIDC callback creates a local user record linked to IdP `sub` | integration | `uv run pytest tests/test_auth_callback.py::test_first_login_creates_user -x` (mock Authlib's token exchange, or run against the real local Keycloak container as a slower integration test) | ❌ Wave 0 |
| AUTH-01 | Second login by the same IdP subject reuses the existing local user (no duplicate) | integration | `uv run pytest tests/test_auth_callback.py::test_repeat_login_reuses_user -x` | ❌ Wave 0 |
| AUTH-01 | Full browser redirect flow (login → Keycloak → callback → session cookie set) reaches the platform | manual / E2E | Manual browser walkthrough against local Keycloak container (Playwright E2E is a reasonable future addition but out of scope to stand up fresh in Phase 1 — justification: no E2E framework exists yet, and the redirect-to-third-party-IdP flow is inherently awkward to automate reliably in CI without a dedicated test realm) | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest -q`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`, plus the manual browser walkthrough for the redirect flow (see table above) since that path isn't automated in Phase 1.

### Wave 0 Gaps
- [ ] `pyproject.toml` — add `pytest`, `pytest-asyncio` as dev dependencies (currently absent)
- [ ] `tests/conftest.py` — shared fixtures: test DB session (SQLite or a test Postgres schema), FastAPI `TestClient`/`AsyncClient`, a helper to mint locally-signed test JWTs + a mocked JWKS endpoint for bearer-token tests
- [ ] `tests/test_auth_gating.py`, `tests/test_bearer_auth.py`, `tests/test_auth_callback.py` — new files, none exist
- [ ] Decide test-DB strategy: a real local Postgres (via the same docker-compose) vs. SQLite-for-tests — recommend Postgres via docker-compose for parity, given Alembic migrations and Postgres-specific types may appear later phases

## Sources

### Primary (HIGH confidence)
- FastAPI official docs — CORS (`https://fastapi.tiangolo.com/tutorial/cors/`) — fetched 2026-07-05, quoted verbatim on wildcard+credentials restriction
- PyJWT official docs — usage/JWKS (`https://pyjwt.readthedocs.io/en/stable/usage.html`) — fetched 2026-07-05
- SQLAlchemy 2.0 ORM Quickstart (`https://docs.sqlalchemy.org/en/20/orm/quickstart.html`) — fetched 2026-07-05
- Alembic Tutorial (`https://alembic.sqlalchemy.org/en/latest/tutorial.html`) — fetched 2026-07-05
- Keycloak container docs (`https://www.keycloak.org/server/containers`) — fetched 2026-07-05
- Keycloak OIDC layers/endpoints docs (`https://www.keycloak.org/securing-apps/oidc-layers`) — fetched 2026-07-05
- PyPI registry (direct API queries, 2026-07-05) — fastapi, uvicorn, sqlalchemy, alembic, psycopg, python-jose, authlib, pyjwt, python-multipart, pydantic-settings, httpx, pytest, pytest-asyncio, itsdangerous, python-dotenv version numbers
- npm registry (direct API queries, 2026-07-05) — react, react-dom, vite, @vitejs/plugin-react, react-router-dom, typescript version numbers
- GitHub API (direct queries, 2026-07-05) — repo activity/archived status for python-jose, pyjwt, authlib, fastapi-sessions
- OSV.dev API (direct queries, 2026-07-05) — CVE/advisory lists for python-jose and pyjwt
- GitHub Releases API — Keycloak latest release (26.6.4, published 2026-06-26)

### Secondary (MEDIUM confidence)
- Authlib official docs, FastAPI/Starlette integration pages (`docs.authlib.org/en/stable/oauth2/client/web/fastapi.html` and `.../starlette.html`) — fetched 2026-07-05 but returned partial/compressed content; core `authorize_redirect`/`authorize_access_token`/`SessionMiddleware` pattern confirmed, but exact PKCE kwarg name and nonce-validation internals not confirmed verbatim
- Authlib official demo repo (`github.com/authlib/demo-oauth-client`, fastapi-google-login) — fetched 2026-07-05, confirms the general register→redirect→callback shape
- Keycloak audience-claim/mapper behavior — Keycloak's admin guide confirms the topic exists (table of contents) but detailed explanatory text was not retrievable in this session; cross-referenced against known community-reported Keycloak default-audience behavior

### Tertiary (LOW confidence)
- Keycloak default `aud` claim value (commonly `"account"` for a fresh client) — this is training-data/community knowledge, NOT confirmed against official docs this session. Flagged as an Open Question — verify hands-on in Wave 0.
- WebSearch tool was unavailable this session (repeated 502 errors from the search backend) — all findings above were obtained via direct WebFetch to specific known URLs and direct registry/API queries instead. This means broader "what does the community currently recommend" discovery (beyond the specific libraries already known to be relevant) was not performed. If a broader ecosystem scan is needed later, retry WebSearch or use Brave/Exa if enabled.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified directly against PyPI/npm registries; library choice rationale (PyJWT over python-jose, hand-rolled sessions over `fastapi-sessions`) backed by direct GitHub/OSV.dev queries, not just training data
- Architecture: MEDIUM-HIGH — core patterns (CORS, SQLAlchemy, Alembic, Keycloak container, JWKS validation) confirmed via official docs; Authlib-specific PKCE/nonce internals are MEDIUM (partial doc retrieval), flagged as Open Questions for a Wave 0 spike
- Pitfalls: MEDIUM-HIGH — CORS and JWT-CVE pitfalls are HIGH (directly sourced); Keycloak audience-mapping and SameSite-cookie pitfalls are MEDIUM (well-known community patterns, not fully confirmed against official docs this session)

**Research date:** 2026-07-05
**Valid until:** 30 days (stable, mature ecosystem — Keycloak/Authlib/PyJWT/SQLAlchemy patterns don't shift quickly), but re-verify the two flagged Open Questions (Authlib PKCE kwarg, Keycloak audience mapper) hands-on regardless of elapsed time, since they were not independently confirmed this session.
