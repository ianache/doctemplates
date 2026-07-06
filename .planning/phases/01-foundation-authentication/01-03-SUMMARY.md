---
phase: 01-foundation-authentication
plan: 03
subsystem: ui
tags: [vite, react, typescript, tailwind, react-router-dom, design-system]

requires:
  - phase: none (Wave 1, no dependencies)
provides:
  - "Standalone Vite + React + TypeScript SPA scaffold in frontend/"
  - "Tailwind theme wired to Precision Archival design tokens (.design/DESIGN.md)"
  - "Routing skeleton (/login, /) via react-router-dom"
  - "apiFetch() wrapper (credentials: include) for backend calls"
  - "Placeholder LoginPage and AuthenticatedShell components"
affects: [01-07-plan, frontend-auth-wiring]

tech-stack:
  added:
    - "vite ^8.1.1 + @vitejs/plugin-react ^6.0.3"
    - "react ^19.2.7 / react-dom ^19.2.7"
    - "react-router-dom ^7.18.1"
    - "typescript ~6.0.2"
    - "tailwindcss ^3.4.19 + postcss ^8.5.16 + autoprefixer ^10.5.2"
  patterns:
    - "Tailwind config extends theme with named design tokens (bg-primary, text-on-surface, etc.) rather than raw hex utilities"
    - "Single apiFetch() wrapper in src/lib/api.ts is the only sanctioned path to the backend, always sending credentials: 'include'"
    - "Route components are pure placeholders (no backend calls) until 01-07-PLAN wires real behavior"

key-files:
  created:
    - frontend/package.json
    - frontend/vite.config.ts
    - frontend/tailwind.config.ts
    - frontend/postcss.config.js
    - frontend/index.html
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/index.css
    - frontend/src/lib/api.ts
    - frontend/src/pages/LoginPage.tsx
    - frontend/src/pages/AuthenticatedShell.tsx
    - frontend/.env.example
  modified: []

key-decisions:
  - "Used Tailwind CSS v3.4.19 (JS config + postcss.config.js with tailwindcss/autoprefixer plugins) instead of the newly-released Tailwind v4, because the plan's literal file layout (tailwind.config.ts with theme.extend, postcss.config.js with separate autoprefixer plugin) is the v3 convention; v4 replaces this with a CSS-first @theme/@import setup and a different postcss plugin package, which would have broken the plan's explicit acceptance criteria and file structure."

requirements-completed: [AUTH-01]

metrics:
  duration: 35min
  completed: 2026-07-06
---

# Phase 1 Plan 03: Frontend Scaffold & Design Tokens Summary

**Vite + React 19 + TypeScript SPA scaffolded with Tailwind wired to the Precision Archival design system (colors, typography, spacing, radii) and a minimal /login vs / routing skeleton backed by a credentials-included apiFetch() wrapper.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-06T01:05:00Z (approx)
- **Completed:** 2026-07-06T01:40:00Z
- **Tasks:** 2/2 completed
- **Files modified:** 20 (15 in Task 1, 5 in Task 2, including scaffold-generated tsconfig/oxlint/README files)

## Accomplishments

- Scaffolded `frontend/` as a standalone Vite + React 19 + TypeScript project (no meta-framework), decoupled from the FastAPI backend per D-01/D-02.
- Encoded all Precision Archival design tokens from `.design/DESIGN.md` into `tailwind.config.ts` (colors, font families, spacing scale including the `sm: 12px` platform-wide exception and Phase-1-only `2xl`/`3xl` extensions, and border radii matching DESIGN.md exactly — not the outdated `.design/*.html` mockup config).
- Wired Google Fonts (Hanken Grotesk, Inter, JetBrains Mono, Material Symbols Outlined variable icon font) into `index.html`.
- Built a routing skeleton (`/login` -> `LoginPage`, `/` -> `AuthenticatedShell`) with no auth guard yet, ready for 01-07-PLAN.
- Implemented `apiFetch()` in `src/lib/api.ts` as the single sanctioned backend-call path, always sending `credentials: "include"` so the httpOnly session cookie is forwarded.

## Task Commits

Each task committed atomically:

1. **Task 1: Vite + React + TypeScript scaffold with Tailwind design tokens** - `a490ee8` (feat)
2. **Task 2: Routing skeleton, API client wrapper, placeholder pages** - `0cebbba` (feat)

_Note: No TDD tasks in this plan (tdd="false" on both tasks per plan frontmatter)._

## Files Created/Modified

- `frontend/package.json` - Vite React-TS scaffold + react-router-dom, tailwindcss/postcss/autoprefixer devDeps
- `frontend/vite.config.ts` - Standard Vite React plugin config (unmodified from scaffold default)
- `frontend/tailwind.config.ts` - Theme extension with Precision Archival colors, fontFamily, spacing, borderRadius tokens
- `frontend/postcss.config.js` - Standard Tailwind + Autoprefixer PostCSS pipeline
- `frontend/index.html` - Google Fonts links (Hanken Grotesk, Inter, JetBrains Mono, Material Symbols Outlined)
- `frontend/src/main.tsx` - BrowserRouter + StrictMode entrypoint
- `frontend/src/index.css` - Tailwind directives + `body` base rule (bg-background, text-on-surface, font-body)
- `frontend/.env.example` - `VITE_API_BASE_URL=http://localhost:8000`
- `frontend/src/lib/api.ts` - `apiFetch()` typed fetch wrapper, `credentials: "include"` always set
- `frontend/src/pages/LoginPage.tsx` - Placeholder centered card, no backend calls
- `frontend/src/pages/AuthenticatedShell.tsx` - Placeholder topbar, no backend calls
- `frontend/src/App.tsx` - `<Routes>`/`<Route>` switch, no auth guard yet

Removed as cleanup (dead scaffold assets superseded by the above): `frontend/src/App.css`, `frontend/src/assets/{react.svg,vite.svg,hero.png}`, `frontend/public/icons.svg`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pinned Tailwind CSS to v3.4.19 instead of latest (v4.3.2)**
- **Found during:** Task 1, dependency install
- **Issue:** `npm view tailwindcss version` resolves to Tailwind v4.3.2 by default. Tailwind v4 replaces the classic `tailwind.config.ts` + `postcss.config.js` (with separate `tailwindcss`/`autoprefixer` plugins) workflow with a CSS-first `@import "tailwindcss"` + `@theme` setup and a single `@tailwindcss/postcss` plugin. The plan's explicit file list, action steps, and acceptance criteria (`postcss.config.js` — "standard Tailwind + Autoprefixer setup"; `tailwind.config.ts` with `theme.extend`) are written against the v3 convention.
- **Fix:** Installed `tailwindcss@3.4.19`, `postcss@8.5.16`, `autoprefixer@10.5.2` explicitly instead of taking the unpinned latest.
- **Files modified:** `frontend/package.json`, `frontend/postcss.config.js`, `frontend/tailwind.config.ts`
- **Commit:** `a490ee8`

None of the other issues encountered required Rule 1/2/4 handling — the plan's task specifications matched cleanly onto the scaffolded Vite output with only the dependency-version adjustment above.

## Known Stubs

Both `LoginPage.tsx` and `AuthenticatedShell.tsx` are intentional placeholders per the plan (`must_haves.artifacts` explicitly labels them "real copy/behavior wired in 01-07-PLAN"). They render static text only, make no backend calls, and `App.tsx` has no auth-guard/redirect logic yet. This is by design — 01-07-PLAN (Wave 2, depends on 01-06's backend auth contract) is the plan that resolves these stubs with real login form, `/api/health`-based redirect guard, and Sign Out wiring.

## Self-Check: PASSED

All files below verified to exist on disk and both commits verified in git log — see Self-Check section for the raw results.
