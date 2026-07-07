---
status: resolved
trigger: "Investigate issue: oidc-login-redirect-loop"
created: 2026-07-06T00:00:00Z
updated: 2026-07-06T00:00:00Z
---

## Current Focus

hypothesis: /auth/callback completes token exchange but fails to establish a session recognizable by /auth/login's "already authenticated" check, or the session cookie is not being set/read correctly (e.g. cookie not sent back due to attributes, or check-if-authenticated logic redirects to /auth/login instead of app shell).
test: Read backend/app auth route implementations (/auth/login, /auth/callback), session cookie service, and diff of f3b428c.
expecting: Find a code path where /auth/callback issues a 307 redirect to a URL that itself triggers /auth/login again (e.g. redirecting to a protected frontend route that isn't recognized as authenticated, or missing cookie set before redirect).
next_action: Read backend app auth module completely.

## Symptoms

expected: After authenticating with Keycloak (realm "docmanagement" at http://localhost:8080), the user should land in the authenticated app shell with an active session.
actual: /auth/callback returns 307 without establishing a working session; client then re-hits /auth/login, restarting the OIDC flow (new state/code) in a loop. Frontend shows generic "We couldn't sign you in" error.
errors: Frontend generic error banner: "We couldn't sign you in. Something went wrong completing sign-in..." No stack trace from user yet. backend/server.log and backend/server2.log present in repo root (untracked) - check for earlier exception info.
reproduction: 100% reproducible. Open app -> /auth/login -> Keycloak login -> /auth/callback with code -> loops back to /auth/login instead of reaching app shell.
started: Suspect introduced or incompletely fixed by f3b428c "fix(01-08): stabilize local auth verification flow" - must verify against actual code, not assume.

## Eliminated

## Evidence

## Resolution

root_cause: Not conclusively isolated. Investigation was interrupted (agent stopped) while confirming Postgres/Keycloak were up and locating a test user credential, before code-level root cause was found.
fix: None applied in this session — user retested the full manual login flow (01-08-PLAN.md, all 7 checks) against a freshly confirmed-running stack and the loop did not reproduce.
verification: User manually confirmed all 7 checks in 01-08-PLAN.md pass, including login, cookie inspection, sign-out invalidation, and independent multi-user sessions.
files_changed: []

**Note:** Resolved by retest, not by a confirmed code fix. If the redirect loop recurs, restart investigation from this file's "Current Focus" hypothesis (session-recognition/cookie issue between `/auth/callback` and `/auth/login`) rather than starting cold.
