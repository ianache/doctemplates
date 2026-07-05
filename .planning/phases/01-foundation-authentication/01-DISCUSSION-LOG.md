# Phase 1: Foundation & Authentication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-05
**Phase:** 1-foundation-authentication
**Areas discussed:** Frontend architecture, OIDC provider & login flow, Session & API auth strategy, Database & persistence foundation

---

## Frontend Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| React | Largest ecosystem for drag-and-drop canvas libraries (Phase 4) and component libraries; common for admin/designer tools | ✓ |
| Vue | Good DX, solid drag-and-drop ecosystem (vuedraggable), smaller bundle in many setups | |
| Svelte/SvelteKit | Leaner runtime, less boilerplate, smaller ecosystem of drag-and-drop canvas components | |
| You decide | Claude picks based on Phase 4 drag-and-drop fit | |

**User's choice:** React

| Option | Description | Selected |
|--------|-------------|----------|
| Separate SPA + API | Frontend build (Vite) decoupled from FastAPI backend; matches Phase 6's external-caller API requirement | ✓ |
| Full-stack meta-framework (Next.js/Nuxt) | SSR/routing conveniences but a second server runtime; no SEO/SSR need for an internal tool | |
| You decide | Claude chooses based on simplicity/fit | |

**User's choice:** Separate SPA + API

| Option | Description | Selected |
|--------|-------------|----------|
| Monorepo, single repo | frontend/ and backend/ folders in one repo; simpler for small team | ✓ |
| Separate repositories | Independent versioning/deploy lifecycle, more overhead | |

**User's choice:** Monorepo, single repo

| Option | Description | Selected |
|--------|-------------|----------|
| You decide | Claude picks a component library fit for admin/dashboard + drag-and-drop once framework is locked | ✓ |
| Specific library in mind | User names one | |

**User's choice:** You decide

**Notes:** No further questions — area settled in one round.

---

## OIDC Provider & Login Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Self-hosted Keycloak | Free, full OIDC/OAuth2 support, Docker for local dev, no third-party SaaS tenant dependency | ✓ |
| SaaS provider (Auth0, Okta, etc.) | Managed, less ops overhead, requires account/tenant setup, possible usage pricing | |
| Fully generic — configurable issuer URL, no provider chosen | Build to spec only, defer concrete provider to deployment; riskier to build/test without one in hand | |

**User's choice:** Self-hosted Keycloak

| Option | Description | Selected |
|--------|-------------|----------|
| Redirect (Authorization Code + PKCE) | Standard OIDC flow, browser redirect to IdP and back; simplest, no popup-blocker issues | ✓ |
| Popup-based login | Opens IdP login in a popup; better SPA UX but adds popup-blocker/postMessage complexity | |

**User's choice:** Redirect (Authorization Code + PKCE)

| Option | Description | Selected |
|--------|-------------|----------|
| Local user record linked to IdP identity | Minimal local row (subject ID, email, created-at) on first login; needed for ownership/audit in Phase 2+ | ✓ |
| No local user record — rely on IdP token claims | Simpler now, but Phase 2+ needs to attribute designs/document types to a user | |

**User's choice:** Local user record linked to IdP identity

**Notes:** No further questions — area settled in one round.

---

## Session & API Auth Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Backend-issued httpOnly session cookie | Backend validates OIDC token post-redirect and sets its own httpOnly/secure cookie; frontend never handles raw tokens | ✓ |
| Frontend holds IdP access token directly (Bearer header) | No backend session state, but SPA manages refresh and exposes token to browser JS memory (larger XSS surface) | |

**User's choice:** Backend-issued httpOnly session cookie

| Option | Description | Selected |
|--------|-------------|----------|
| Same OIDC-issued bearer token, validated independently of UI session | External callers use client-credentials (or similar) grant from the same IdP; backend validates JWT directly, no dependency on cookie session | ✓ |
| Separate API-key mechanism, independent of OIDC | Simpler for callers but a second auth mechanism to build/secure; less aligned with AUTH-01's OIDC-gated intent | |

**User's choice:** Same OIDC-issued bearer token, validated independently of UI session

**Notes:** No further questions — area settled in one round.

---

## Database & Persistence Foundation

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL | Production-grade relational DB, handles concurrent multi-user writes, fits relational document-type/schema/design data from day one | ✓ |
| SQLite | Zero-ops, file-based; weaker under concurrent writes, complicates deployment once Phase 3 adds file uploads alongside a SQLite file | |
| You decide | Claude picks based on multi-user + file-upload fit | |

**User's choice:** PostgreSQL

| Option | Description | Selected |
|--------|-------------|----------|
| Alembic | Standard migration tool for SQLAlchemy/Python backends, versioned scripts, works cleanly with Postgres | ✓ |
| You decide | Claude picks a migration approach once ORM/DB access layer is chosen | |

**User's choice:** Alembic

**Notes:** No further questions — area settled in one round.

---

## Claude's Discretion

- Specific UI component library/design system (chosen once React is scaffolded)
- Exact ORM/DB access layer beyond "Alembic for migrations" (SQLAlchemy assumed, to confirm in research/planning)
- Exact local user table schema beyond subject ID/email/created-at
- Docker/local-dev setup mechanics for Keycloak (compose file, realm bootstrap)

## Deferred Ideas

- Fine-grained roles/permissions per document type or design (AUTH-02) — already tracked as a v2 requirement in REQUIREMENTS.md; not re-litigated here beyond confirming the local user record (D-07) supports adding it later.
- Third-party OIDC SaaS provider (Auth0/Okta) as an alternative to self-hosted Keycloak — noted as a future option if a deployment constraint requires a managed IdP, not pursued now.
