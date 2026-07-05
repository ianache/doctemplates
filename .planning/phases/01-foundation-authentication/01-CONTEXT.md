# Phase 1: Foundation & Authentication - Context

**Gathered:** 2026-07-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The platform has a working application foundation (backend + frontend scaffolding, database) and gates all access behind an external OAuth2/OIDC identity provider — no custom-built credentials. This phase delivers AUTH-01 only: login works, unauthenticated access is rejected, and multiple distinct users can each authenticate under their own identity. Document types, designer, content, versioning, and generation capabilities are out of scope — those are Phases 2-6.

</domain>

<decisions>
## Implementation Decisions

### Frontend Architecture
- **D-01:** Frontend framework is React.
- **D-02:** Architecture is a separate SPA + API — decoupled frontend build (e.g. Vite) talking to the FastAPI backend, not a full-stack meta-framework (no Next.js/Nuxt SSR layer). Rationale: the platform is an internal operational tool (no SEO/SSR need), and Phase 6's generation API must remain independent of any UI rendering server.
- **D-03:** Single monorepo — frontend/ and backend/ folders live in this same repository, not separate repos.
- **D-04:** Claude's Discretion — specific UI component library/design system (e.g. Mantine, shadcn/ui), chosen once the framework is in place, suited to admin/dashboard tools with drag-and-drop needs (Phase 4 lookahead).

### OIDC Provider & Login Flow
- **D-05:** OIDC identity provider is self-hosted Keycloak — run via Docker for local dev, self-hosted in prod. Rationale: free, full OIDC/OAuth2 support, lets the team create test users/realms without depending on a third-party SaaS tenant.
- **D-06:** Login flow is redirect-based: Authorization Code + PKCE. No popup-based login.
- **D-07:** Platform maintains a local user record linked to the IdP identity (IdP subject/`sub` claim, email, created-at) created on first login. This is needed starting Phase 2 to attribute document types/designs to a user, even though fine-grained roles/permissions (AUTH-02) are deferred to v2.

### Session & API Auth Strategy
- **D-08:** Browser UI authentication is a backend-issued httpOnly, secure session cookie, set after the backend validates the OIDC token from the redirect callback. The frontend SPA never handles raw IdP tokens directly.
- **D-09:** External API callers (relevant starting Phase 6's generation/preview API) authenticate via an OIDC-issued bearer token (e.g. client-credentials grant for machine-to-machine callers), validated independently of the browser session cookie mechanism. No separate/parallel API-key system — one OIDC-based auth mechanism for both UI and API callers, satisfying AUTH-01 for all access paths.

### Database & Persistence Foundation
- **D-10:** PostgreSQL is the platform's database, used across all phases (users, document types, schemas, designs, versions, etc.). Rationale: production-grade relational DB with real constraints/migrations, handles concurrent multi-user writes, and avoids the file-storage-alongside-SQLite-file complications that come up once Phase 3 introduces uploaded PDF storage.
- **D-11:** Alembic manages schema migrations as the schema evolves phase over phase (standard for SQLAlchemy-based Python backends, pairs cleanly with Postgres).

### Claude's Discretion
- Specific UI component library/design system (D-04).
- Migration tooling specifics beyond "Alembic" — e.g. exact ORM/DB access layer choice (SQLAlchemy assumed but not explicitly locked) — to be confirmed during research/planning.
- Exact local user table schema (columns beyond subject ID/email/created-at).
- Docker/local-dev setup mechanics for Keycloak (compose file, realm bootstrap approach).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Requirements
- `.planning/PROJECT.md` — Vision, constraints (OIDC-only auth, no custom credentials), Key Decisions log
- `.planning/REQUIREMENTS.md` — AUTH-01 requirement definition and traceability to Phase 1
- `.planning/ROADMAP.md` §Phase 1 — Phase 1 goal and success criteria

### Existing Codebase Analysis
- `.planning/codebase/STACK.md` — Current stack state (Python 3.12, uv, FastAPI available but unused)
- `.planning/codebase/ARCHITECTURE.md` — Confirms codebase is pre-alpha stub, no patterns yet
- `.planning/codebase/INTEGRATIONS.md` — Confirms no auth currently implemented; notes PRD's BFF-style endpoint suggestions (not authoritative for auth design)

No external specs beyond the above — this is a greenfield foundation phase with no prior ADRs or auth-specific design docs to follow.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — `main.py` is a 5-line stub; no backend, frontend, or auth code exists yet. This phase creates the foundation from scratch.

### Established Patterns
- None established in code. `headroom-ai[all]` in `pyproject.toml` is developer tooling for this project's own development (token-optimization CLI) — not a product dependency, must not be confused with platform dependencies.

### Integration Points
- FastAPI, Uvicorn, and HTTPx are already available transitively via `headroom-ai[all]` extras, but are not yet declared as direct product dependencies — planning should add them explicitly as first-class dependencies rather than relying on the transitive install.
- No `.env` file exists yet — needed for OIDC issuer URL, client ID/secret, database connection string, session secret.

</code_context>

<specifics>
## Specific Ideas

No specific visual or UX references were given for this phase (no login-page mockup, etc.) — open to a standard, clean login redirect experience. All specifics captured above are architectural/backend decisions (D-01 through D-11).

</specifics>

<deferred>
## Deferred Ideas

- Fine-grained roles/permissions per document type or design (AUTH-02) — explicitly deferred to v2 per REQUIREMENTS.md; local user record (D-07) is designed to make this addition straightforward later without a schema rework.
- Choice of a specific third-party OIDC SaaS provider (Auth0/Okta) — self-hosted Keycloak was chosen for dev/prod instead; revisit only if a future deployment constraint requires a managed IdP.

None — discussion stayed within phase scope otherwise.

</deferred>

---

*Phase: 01-foundation-authentication*
*Context gathered: 2026-07-05*
