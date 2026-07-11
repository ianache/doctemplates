# Phase 10: Complex Schema UI & Nested Data Previsualization - Research

**Researched:** 2026-07-10
**Domain:** React/Vite frontend UI over FastAPI nested schema and preview contracts
**Confidence:** HIGH

## User Constraints

`10-CONTEXT.md` exists and contains active design decisions D-01 to D-05. [VERIFIED: codebase]

### Locked Scope From ROADMAP.md

- Phase 10 goal: "Enhance the frontend to support visual configuration of complex schemas and interactive previsualization of designs with nested/array mock data." [VERIFIED: .planning/ROADMAP.md]
- Phase 10 depends on Phase 9, but Phase 09 implementation-complete state still has human UI/UAT verification pending. [VERIFIED: .planning/phases/09-search-documents-library-audit-trace/09-03-SUMMARY.md; .planning/phases/09-search-documents-library-audit-trace/09-VERIFICATION.md]
- Phase 10 requirements are `COMPUI-01` and `COMPUI-02`. [VERIFIED: .planning/REQUIREMENTS.md]

### Project Constraints From AGENTS.md

- Prefix shell commands with `rtk` when running commands. [CITED: user-provided AGENTS.md]
- Prefer RTK-filtered commands such as `rtk read`, `rtk git status`, and `rtk npm run` to reduce context usage. [CITED: user-provided AGENTS.md]

### Out of Scope From REQUIREMENTS.md

- Platform-side resolution of real operational data is deferred; API callers still supply data directly. [VERIFIED: .planning/REQUIREMENTS.md]
- Non-PDF output formats remain out of scope. [VERIFIED: .planning/REQUIREMENTS.md]
- Custom-built authentication remains out of scope. [VERIFIED: .planning/REQUIREMENTS.md]
- Shared link access control remains deferred. [VERIFIED: .planning/REQUIREMENTS.md]

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMPUI-01 | Support viewing, adding, and managing complex schema fields in the Document Types UI. [VERIFIED: .planning/REQUIREMENTS.md] | Use existing `react-hook-form` + `useFieldArray`, submit the backend's flat field path contract, and add UI helpers that generate valid `cliente.direccion.calle` and `cliente.contactos[].nombre` names. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx; backend/app/schemas/document_type.py] |
| COMPUI-02 | Support previsualizing designs with complex nested/array data in the visual editor. [VERIFIED: .planning/REQUIREMENTS.md] | Add a typed preview API client for `POST /api/document-designs/{id}/preview`, generate/edit nested mock JSON from document type fields, and render returned PDF blobs in the existing designer preview panel without creating issuances. [VERIFIED: backend/app/api/document_designs.py; backend/tests/test_generation_preview.py; frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx] |

</phase_requirements>

## Summary

Phase 10 should be implemented entirely as a frontend enhancement over the backend contracts completed in Phases 7 and 8. The backend already validates nested dot paths, `[]` list notation, case-insensitive payloads, AST-extracted template tokens, draft design warnings, and PDF preview generation without persistence. [VERIFIED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-01-SUMMARY.md; .planning/phases/08-template-ast-static-validation/08-VERIFICATION.md; backend/app/api/document_designs.py]

The Document Types UI currently creates only flat primitive fields and performs only a simple duplicate-name check before submit. The backend accepts the same flat `fields[]` payload shape, so the UI should not invent a nested schema storage format; it should offer a visual tree/editor that compiles to the existing flat field names. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx; frontend/src/lib/documentTypes.ts; backend/app/schemas/document_type.py]

The Document Design detail page currently previews selected page snapshots with `srcDoc` for HTML templates, not a generated whole-document PDF. Phase 10 should add a mock-data panel plus a generated PDF preview mode using the existing preview endpoint, keeping issuance persistence untouched. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx; backend/app/api/document_designs.py]

**Primary recommendation:** Use the existing React/Vite/TypeScript stack and build two local frontend modules: a schema-field tree adapter for `fields[]` and a mock-data adapter for preview payload JSON. [VERIFIED: frontend/package.json; backend/app/schemas/document_type.py; backend/app/services/pdf_generator.py]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Visual nested schema editing | Browser / Client | API / Backend | The browser owns authoring ergonomics; backend remains the source of truth for path validation, depth limit, uniqueness, and structural conflict rejection. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx; backend/app/schemas/document_type.py] |
| Schema path validation feedback | API / Backend | Browser / Client | Client can prevalidate for faster feedback, but backend validators are authoritative. [VERIFIED: backend/app/schemas/document_type.py] |
| Mock payload generation and editing | Browser / Client | API / Backend | Mock data is design-time UI state; backend validates/coerces it when preview is requested. [VERIFIED: backend/app/services/pdf_generator.py; backend/app/api/document_designs.py] |
| Generated PDF preview | API / Backend | Browser / Client | Backend composes PDFs; browser posts mock data and renders a returned PDF blob in an iframe. [VERIFIED: backend/app/api/document_designs.py; frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx] |
| Issuance persistence | API / Backend | Database / Storage | Preview endpoint returns a PDF response and does not create `DocumentIssuance` rows or files. [VERIFIED: backend/tests/test_generation_preview.py] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.7 | Component model and stateful UI. [VERIFIED: frontend/package.json; VERIFIED: npm registry for `react` latest] | Already installed and used by every frontend page. [VERIFIED: frontend/src/App.tsx] |
| TypeScript | ~6.0.2 | Static typing for API payloads and UI adapters. [VERIFIED: frontend/package.json] | Existing config has `noUnusedLocals`, `noUnusedParameters`, and `verbatimModuleSyntax`, so planner must include type-only imports where needed. [VERIFIED: frontend/tsconfig.app.json; .planning/phases/09-search-documents-library-audit-trace/09-03-SUMMARY.md] |
| Vite | ^8.1.1 | Frontend build/dev tool. [VERIFIED: frontend/package.json] | Existing `npm run build` runs `tsc -b && vite build`. [VERIFIED: frontend/package.json] |
| react-hook-form | 7.81.0 | Document Type form state and dynamic field rows. [VERIFIED: frontend/package-lock.json; CITED: https://github.com/react-hook-form/react-hook-form] | Already used in the create form; official examples use `useForm` registration and validation rules. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx; CITED: https://github.com/react-hook-form/react-hook-form] |
| @dnd-kit/core + @dnd-kit/sortable | 6.3.1 / 10.0.0 | Existing designer fragment ordering. [VERIFIED: frontend/package-lock.json] | Keep existing sortable design stack patterns; dnd-kit sortable docs require `DndContext` plus `SortableContext` and sorted `items`. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx; CITED: https://dndkit.com/legacy/presets/sortable/overview/] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tailwind CSS | ^3.4.19 | Existing Precision Archival design tokens. [VERIFIED: frontend/package.json; frontend/tailwind.config.ts] | Use existing color, spacing, font, and panel classes rather than introducing a new component library. [VERIFIED: frontend/tailwind.config.ts] |
| Backend FastAPI preview endpoint | Existing | PDF preview generation. [VERIFIED: backend/app/api/document_designs.py] | Use for whole-design preview with mock nested data; do not render final PDFs in the browser. [VERIFIED: backend/app/services/pdf_generator.py] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Local schema tree adapter | External JSON schema form/editor package | Not recommended: backend schema is path-list based, not JSON Schema, so a generic JSON Schema editor would add mapping complexity and package risk. [VERIFIED: backend/app/schemas/document_type.py; ASSUMED] |
| Existing preview endpoint | Client-side HTML template substitution | Not recommended: backend already owns case-insensitive Jinja2 resolution, xhtml2pdf rendering, static PDF merging, and no-persistence preview behavior. [VERIFIED: backend/app/services/pdf_generator.py; backend/app/api/document_designs.py] |
| Existing designer layout | New route/page for preview | Not recommended: requirement says previsualization in visual editor, and current detail page already owns the canvas/inspector shell. [VERIFIED: .planning/REQUIREMENTS.md; frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx] |

**Installation:** No new package installation is recommended for Phase 10. [VERIFIED: frontend/package.json; ASSUMED]

**Version verification:** Local `npm view` timed out even with approval, so package currency is based on `frontend/package.json`, `frontend/package-lock.json`, and one successful npm registry web fetch for `react@19.2.7`. [VERIFIED: command result; VERIFIED: npm registry]

## Package Legitimacy Audit

No new external packages should be installed in this phase. [VERIFIED: frontend/package.json; ASSUMED]

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| none | — | — | — | — | not run | Approved: no install task required. [VERIFIED: codebase] |

**Packages removed due to slopcheck [SLOP] verdict:** none. [VERIFIED: codebase]
**Packages flagged as suspicious [SUS]:** none. [VERIFIED: codebase]

## Architecture Patterns

### System Architecture Diagram

```mermaid
flowchart LR
  A[Document Type create/detail UI] --> B[Schema tree adapter]
  B --> C[Flat fields array: name/type/description]
  C --> D[POST /api/document-types]
  D --> E[Backend path and structural validators]
  E --> F[(DocumentType fields)]

  F --> G[Document Design detail UI]
  G --> H[Mock data adapter]
  H --> I[Editable nested JSON payload]
  I --> J[POST /api/document-designs/:id/preview]
  J --> K[Backend validate/coerce with mock_fallback]
  K --> L[PDF bytes]
  L --> M[Browser Blob URL iframe preview]
```

### Recommended Project Structure

```text
frontend/src/
├── lib/
│   ├── documentTypes.ts          # Extend field types only if backend contract changes.
│   ├── documentDesigns.ts        # Add previewDocumentDesign(designId, payload): Blob.
│   └── schemaFields.ts           # New pure adapter: flat fields <-> tree, validation, mock data.
├── pages/document-types/
│   ├── DocumentTypeCreatePage.tsx
│   ├── DocumentTypeDetailPage.tsx
│   └── components/
│       └── SchemaFieldEditor.tsx # New visual editor over flat fields[].
└── pages/document-designs/
    ├── DocumentDesignDetailPage.tsx
    └── components/
        ├── MockDataPanel.tsx     # New nested JSON editor/generator.
        └── PreviewFrame.tsx      # New Blob URL lifecycle/rendering helper.
```

### Pattern 1: Keep Backend Flat Field Contract

**What:** Represent nested schemas in UI as a tree, but submit `DocumentTypeFieldIn[]` with names like `cliente.direccion.calle` and `cliente.contactos[].nombre`. [VERIFIED: backend/app/schemas/document_type.py; frontend/src/lib/documentTypes.ts]

**When to use:** All Document Type create/detail UI for `COMPUI-01`. [VERIFIED: .planning/REQUIREMENTS.md]

**Example:**

```ts
// Source: backend/app/schemas/document_type.py and frontend/src/lib/documentTypes.ts
type FieldType = "string" | "number" | "date" | "boolean";

type DocumentTypeFieldIn = {
  name: string;
  type: FieldType;
  description: string | null;
};

const fields: DocumentTypeFieldIn[] = [
  { name: "cliente.direccion.calle", type: "string", description: null },
  { name: "cliente.contactos[].nombre", type: "string", description: null },
];
```

### Pattern 2: Mock Data From Schema Paths

**What:** Generate editable nested JSON from document type fields and preserve backend-compatible array shape. Missing list fields can be previewed as `[]`; populated list examples should include at least one object to exercise template loops. [VERIFIED: backend/app/services/pdf_generator.py; backend/tests/test_nested_case_insensitive.py]

**When to use:** Designer preview panel for `COMPUI-02`. [VERIFIED: .planning/REQUIREMENTS.md]

**Example:**

```ts
// Source: backend/app/services/pdf_generator.py parse/expand behavior
const mockPayload = {
  cliente: {
    direccion: {
      calle: "calle_val",
    },
    contactos: [
      {
        nombre: "nombre_val",
        edad: 123.45,
      },
    ],
  },
};
```

### Pattern 3: PDF Blob Preview Lifecycle

**What:** Fetch PDF bytes through `apiFetch`, convert to `Blob`, create an object URL, and revoke it in effect cleanup. [VERIFIED: frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx]

**When to use:** Whole-design preview in `DocumentDesignDetailPage`. [VERIFIED: backend/app/api/document_designs.py]

**Example:**

```tsx
// Source: frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx
useEffect(() => {
  let cancelled = false;
  let objectUrl: string | null = null;

  apiFetch(`/api/document-designs/${designId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mockPayload),
  })
    .then((res) => {
      if (!res.ok) throw new Error(`Preview failed (${res.status})`);
      return res.blob();
    })
    .then((blob) => {
      if (cancelled) return;
      objectUrl = URL.createObjectURL(blob);
      setPreviewUrl(objectUrl);
    });

  return () => {
    cancelled = true;
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  };
}, [designId, mockPayload]);
```

### Anti-Patterns to Avoid

- **Persisting preview issuances:** `POST /preview` must remain no-persistence; do not call `/generate` from the UI preview button. [VERIFIED: backend/tests/test_generation_preview.py]
- **Changing backend schema shape:** Do not replace `fields[]` with nested JSON unless a backend migration is explicitly planned. [VERIFIED: frontend/src/lib/documentTypes.ts; backend/app/schemas/document_type.py]
- **Client-only validation as authority:** Client validation is useful for UX, but backend must still reject invalid paths, conflicts, and casing duplicates. [VERIFIED: backend/app/schemas/document_type.py]
- **Rendering templates in the browser:** Browser rendering would miss backend Jinja2 case-insensitive resolution, AST behavior, static PDF merge, and xhtml2pdf output. [VERIFIED: backend/app/services/pdf_generator.py; backend/app/services/content_validation.py]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Browser PDF composer | Backend `POST /api/document-designs/{id}/preview` | Backend already validates payload, renders Jinja2, and merges static PDFs. [VERIFIED: backend/app/api/document_designs.py; backend/app/services/pdf_generator.py] |
| Drag/reorder mechanics | New drag system | Existing dnd-kit pattern | Existing designer uses `DndContext`, `SortableContext`, sensors, and `arrayMove`. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx; CITED: https://dndkit.com/legacy/presets/sortable/overview/] |
| Form field array state | Custom uncontrolled DOM array | `react-hook-form` + `useFieldArray` | Existing Document Type create form already uses this pattern. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx; CITED: https://github.com/react-hook-form/react-hook-form] |
| Backend path parser | New backend parser in frontend as authority | Lightweight client mirror plus backend submit validation | Backend owns regex, depth cap, structural conflict validation, and case-insensitive uniqueness. [VERIFIED: backend/app/schemas/document_type.py] |

**Key insight:** The complex part is adapter logic, not new infrastructure. Keep storage/API flat, make UI visual. [VERIFIED: codebase; ASSUMED]

## Common Pitfalls

### Pitfall 1: Treating `[]` as a Leaf Segment

**What goes wrong:** UI creates `cliente.contactos[].nombre` as if `contactos[]` were a primitive field instead of a list-of-objects parent. [VERIFIED: backend/app/schemas/document_type.py]
**Why it happens:** The backend stores only leaf field rows, so parent object/list nodes are inferred. [VERIFIED: backend/app/schemas/document_type.py]
**How to avoid:** Build a tree adapter that marks segments ending in `[]` as list nodes and only allows primitive `type` selection on leaf rows. [VERIFIED: backend/app/schemas/document_type.py]
**Warning signs:** Generated payload contains `{ "contactos[]": ... }` instead of `{ "contactos": [ ... ] }`. [VERIFIED: backend/app/services/pdf_generator.py]

### Pitfall 2: Previewing Page Snapshot HTML Instead of Generated Document

**What goes wrong:** Users see raw token placeholders in `srcDoc` and assume nested data preview is broken. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx]
**Why it happens:** Current designer preview renders selected template snapshot HTML, not backend-composed PDF. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx]
**How to avoid:** Add an explicit generated preview mode/panel that posts mock data to `/preview` and displays returned PDF bytes. [VERIFIED: backend/app/api/document_designs.py]
**Warning signs:** Preview iframe source is `srcDoc` for an HTML page after clicking "preview data". [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx]

### Pitfall 3: Requiring Full Mock Payload for Preview

**What goes wrong:** Preview UI blocks on every primitive field even though backend preview supports mock fallback. [VERIFIED: backend/app/services/pdf_generator.py]
**Why it happens:** Generation and preview have different strictness; `/generate` uses `mock_fallback=False`, `/preview` uses `mock_fallback=True`. [VERIFIED: backend/app/api/document_designs.py]
**How to avoid:** Let users partially edit mock data, but surface backend validation errors for malformed object/list types. [VERIFIED: backend/app/services/pdf_generator.py]
**Warning signs:** Empty mock data cannot preview a draft design. [VERIFIED: backend/tests/test_generation_preview.py]

### Pitfall 4: Case-Insensitive Collisions Hidden by UI

**What goes wrong:** UI allows both `Cliente.Nombre` and `cliente.nombre`; backend rejects on save. [VERIFIED: backend/app/schemas/document_type.py]
**Why it happens:** Current frontend duplicate check is case-sensitive. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx]
**How to avoid:** Make UI duplicate checks case-insensitive and mirror backend conflict messages. [VERIFIED: backend/app/schemas/document_type.py]
**Warning signs:** `new Set(names).size` is the only duplicate check. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx]

### Pitfall 5: Phase 9 UI State Assumption

**What goes wrong:** Planner assumes Phase 9 live browser UAT passed and builds Phase 10 around verified navigation behavior. [VERIFIED: .planning/phases/09-search-documents-library-audit-trace/09-03-SUMMARY.md]
**Why it happens:** Phase 9 frontend compiled, but live browser verification remained outstanding. [VERIFIED: .planning/phases/09-search-documents-library-audit-trace/09-VERIFICATION.md]
**How to avoid:** Use Phase 9 code patterns, but include a manual/browser checkpoint for Phase 10 preview and navigation. [VERIFIED: .planning/phases/09-search-documents-library-audit-trace/09-VERIFICATION.md]
**Warning signs:** Plan says "Phase 9 UAT passed" without evidence. [VERIFIED: .planning/phases/09-search-documents-library-audit-trace/09-VERIFICATION.md]

## Code Examples

### Add Preview API Client

```ts
// Source: backend/app/api/document_designs.py and frontend/src/lib/api.ts
export async function previewDocumentDesign(
  designId: string,
  payload: Record<string, unknown>,
): Promise<Blob> {
  const res = await apiFetch(`/api/document-designs/${designId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
  return res.blob();
}
```

### Generate Mock Leaf Values

```ts
// Source: backend/app/services/pdf_generator.py mock_fallback behavior
function sampleValue(type: FieldType): string | number | boolean {
  if (type === "number") return 123.45;
  if (type === "boolean") return true;
  if (type === "date") return new Date().toISOString().slice(0, 10);
  return "sample";
}
```

### Case-Insensitive Duplicate Check

```ts
// Source: backend/app/schemas/document_type.py
function hasCaseInsensitiveDuplicates(fields: { name: string }[]) {
  const lowered = fields.map((field) => field.name.trim().toLowerCase());
  return new Set(lowered).size !== lowered.length;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat primitive-only field UI | Visual editor over nested/list path strings | Phase 10 target | UI should compile to existing backend paths. [VERIFIED: .planning/ROADMAP.md; frontend/src/pages/document-types/DocumentTypeCreatePage.tsx] |
| Selected-page `srcDoc` preview | Whole-design backend PDF preview with mock payload | Phase 6 backend, Phase 10 frontend | UI can previsualize real composition without issuance persistence. [VERIFIED: backend/app/api/document_designs.py; backend/tests/test_generation_preview.py] |
| Regex or manual token scanning | Jinja2 AST token validation | Phase 8 | Draft warnings and activation errors should be visible to users where available. [VERIFIED: .planning/phases/08-template-ast-static-validation/08-VERIFICATION.md] |

**Deprecated/outdated:**
- Current Document Type create form's primitive-only `FIELD_TYPES` row UI is insufficient for `COMPUI-01`. [VERIFIED: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx; .planning/REQUIREMENTS.md]
- Current designer selected-page iframe is insufficient for `COMPUI-02` because it does not run backend data binding. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx; .planning/REQUIREMENTS.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | No new package installation is required for Phase 10. | Standard Stack / Package Legitimacy Audit | If a planner chooses a complex third-party JSON/schema editor, package legitimacy must be rerun and UI integration risk increases. |
| A2 | A local path-list-to-tree adapter is simpler than adopting a JSON Schema editor. | Alternatives Considered / Don't Hand-Roll | If product direction changes to JSON Schema storage, this UI adapter recommendation becomes too narrow. |
| A3 | Mock arrays should default to at least one object in UI examples to exercise loops. | Architecture Patterns / Common Pitfalls | If product wants empty-list preview by default, templates with loops may not visually demonstrate array layouts. |

## Open Questions

1. **Should existing document types be editable in Phase 10 or only view/create?**
   - What we know: Requirement says "viewing, adding, and managing complex schema fields" in Document Types UI. [VERIFIED: .planning/REQUIREMENTS.md]
   - What's unclear: Current frontend has create/detail pages but no update/delete document type API found in inspected files. [VERIFIED: frontend/src/lib/documentTypes.ts; backend/app/api/document_types.py]
   - Recommendation: Plan `COMPUI-01` as create + detail visualization first; add edit only if backend update API exists or a backend task is explicitly added. [ASSUMED]

2. **Should mock data persist per design/page?**
   - What we know: Preview endpoint takes request payload and does not persist issuance. [VERIFIED: backend/app/api/document_designs.py; backend/tests/test_generation_preview.py]
   - What's unclear: No existing frontend storage location for preview mock data was found. [VERIFIED: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx]
   - Recommendation: Keep mock data local component state for Phase 10 MVP; defer persistence unless the user requests saved preview fixtures. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | Frontend build/dev | yes | v22.23.1 | none needed. [VERIFIED: command result] |
| npm | Frontend scripts/package metadata | uncertain | command timed out | Use existing `package-lock.json`; do not install packages. [VERIFIED: command result] |
| Vite dev server | Browser UAT | project-configured | ^8.1.1 in `package.json` | `npm run build` compile verification. [VERIFIED: frontend/package.json] |
| Backend API | Preview endpoint | project-configured | FastAPI project | Backend tests can verify endpoint; browser preview needs local app auth. [VERIFIED: backend/pyproject.toml; backend/app/api/document_designs.py] |

**Missing dependencies with no fallback:**
- None identified for planning. [VERIFIED: codebase]

**Missing dependencies with fallback:**
- npm registry metadata lookup timed out; no new packages are recommended, so registry lookup is not blocking. [VERIFIED: command result]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Frontend framework | TypeScript compiler + Vite build; no app-level frontend test files found outside `node_modules`. [VERIFIED: frontend/package.json; command result] |
| Backend framework | pytest configured in `backend/pyproject.toml`. [VERIFIED: backend/pyproject.toml] |
| Config file | `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/vite.config.ts`, `backend/pyproject.toml`. [VERIFIED: codebase] |
| Quick run command | `rtk powershell -Command "Set-Location frontend; npm run build"` [VERIFIED: frontend/package.json] |
| Backend preview command | `rtk powershell -Command "Set-Location backend; uv run pytest tests/test_generation_preview.py tests/test_nested_case_insensitive.py -q"` [VERIFIED: backend/tests/test_generation_preview.py; backend/tests/test_nested_case_insensitive.py] |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| COMPUI-01 | Create/view nested object and list schema fields in Document Types UI. [VERIFIED: .planning/REQUIREMENTS.md] | compile + focused utility tests if frontend test framework added | `rtk powershell -Command "Set-Location frontend; npm run build"` | existing compile only; no frontend unit test framework found. [VERIFIED: command result] |
| COMPUI-02 | Preview a design with nested/list mock data through backend PDF preview. [VERIFIED: .planning/REQUIREMENTS.md] | backend integration + frontend compile + manual browser | `rtk powershell -Command "Set-Location backend; uv run pytest tests/test_generation_preview.py tests/test_nested_case_insensitive.py -q"` | backend tests exist. [VERIFIED: backend/tests/test_generation_preview.py; backend/tests/test_nested_case_insensitive.py] |

### Sampling Rate

- **Per task commit:** Run frontend build for UI tasks; run focused backend preview tests if backend preview contract changes. [VERIFIED: frontend/package.json; backend/pyproject.toml]
- **Per wave merge:** Run `frontend; npm run build` and focused backend tests above. [VERIFIED: codebase]
- **Phase gate:** Manual browser walkthrough must cover nested schema creation, detail visualization, mock data edit, preview PDF rendering, validation error display, and no issuance persistence. [VERIFIED: .planning/REQUIREMENTS.md; backend/tests/test_generation_preview.py]

### Wave 0 Gaps

- [ ] `frontend/src/lib/schemaFields.ts` pure helper module for tree parsing, path generation, duplicate/conflict checks, and mock JSON creation. [ASSUMED]
- [ ] Optional frontend unit test harness is absent; if planner wants automated utility coverage, add a test runner as a separately verified package decision. [VERIFIED: command result; ASSUMED]
- [ ] `frontend/src/lib/documentDesigns.ts` lacks `previewDocumentDesign`; add it before UI wiring. [VERIFIED: frontend/src/lib/documentDesigns.ts]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | Existing `apiFetch` sends credentials and backend depends on `get_current_user`. [VERIFIED: frontend/src/lib/api.ts; backend/app/api/document_designs.py] |
| V3 Session Management | yes | Keep using httpOnly session cookie via shared `apiFetch`; do not store tokens in preview state. [VERIFIED: frontend/src/lib/api.ts] |
| V4 Access Control | yes | Use existing authenticated document design/document type endpoints; no public preview endpoint. [VERIFIED: backend/app/api/document_designs.py; backend/app/api/document_types.py] |
| V5 Input Validation | yes | Backend Pydantic schema validators and PDF payload validation remain authoritative. [VERIFIED: backend/app/schemas/document_type.py; backend/app/services/pdf_generator.py] |
| V6 Cryptography | no new crypto | Phase 10 should not add signing/crypto behavior. [VERIFIED: .planning/REQUIREMENTS.md] |

### Known Threat Patterns for React/FastAPI Preview UI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed nested mock payload causes unexpected render path | Tampering | Submit to backend preview endpoint and display backend validation errors; do not bypass `validate_and_coerce_payload`. [VERIFIED: backend/app/services/pdf_generator.py] |
| XSS through preview HTML | Elevation of Privilege | Preview rendered output stays in PDF/blob iframe; backend Jinja environment uses sandboxed environment and autoescape. [VERIFIED: backend/app/services/pdf_generator.py] |
| Case-insensitive key collision hides one value | Tampering | Backend collision detection rejects collisions; UI should pre-check lowercased paths. [VERIFIED: backend/app/services/pdf_generator.py; backend/app/schemas/document_type.py] |
| Object URL leak | Information Disclosure | Revoke Blob URLs on effect cleanup as existing issuance preview page does. [VERIFIED: frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx] |

## Sources

### Primary (HIGH confidence)

- `.planning/ROADMAP.md` - Phase 10 scope and Phase dependencies.
- `.planning/REQUIREMENTS.md` - `COMPUI-01`, `COMPUI-02`, and out-of-scope constraints.
- `.planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-01-SUMMARY.md` and `07-VERIFICATION.md` - nested schema and case-insensitive backend behavior.
- `.planning/phases/08-template-ast-static-validation/08-01-SUMMARY.md` and `08-VERIFICATION.md` - AST validation and draft warnings.
- `.planning/phases/09-search-documents-library-audit-trace/09-03-SUMMARY.md` and `09-VERIFICATION.md` - frontend patterns and human UI verification gap.
- `frontend/src/pages/document-types/DocumentTypeCreatePage.tsx`, `DocumentTypeDetailPage.tsx`, `frontend/src/lib/documentTypes.ts` - current Document Types UI and client contract.
- `frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx`, `frontend/src/lib/documentDesigns.ts` - current designer shell and missing preview client.
- `frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx` - existing PDF Blob URL iframe pattern.
- `backend/app/schemas/document_type.py`, `backend/app/api/document_designs.py`, `backend/app/services/pdf_generator.py` - backend path, preview, and payload contracts.
- `backend/tests/test_generation_preview.py`, `backend/tests/test_nested_case_insensitive.py` - preview no-persistence and nested/list behavior.

### Secondary (MEDIUM confidence)

- `https://github.com/react-hook-form/react-hook-form` - official project README and release page evidence for `react-hook-form` usage and 7.81.0 release.
- `https://dndkit.com/legacy/presets/sortable/overview/` - official sortable docs for `DndContext`, `SortableContext`, sensors, and sorted items.
- `https://vite.dev/guide/` - official Vite guide availability.
- `https://registry.npmjs.org/react/latest` - npm registry latest metadata for `react@19.2.7`.

### Tertiary (LOW confidence)

- None used as authority.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing packages and code paths are already installed and used; registry lookup only partially succeeded. [VERIFIED: frontend/package.json; frontend/package-lock.json]
- Architecture: HIGH - backend contracts and frontend integration points are directly verified in source. [VERIFIED: backend/app/api/document_designs.py; frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx]
- Pitfalls: HIGH - pitfalls come from concrete current UI limitations and verified backend behavior. [VERIFIED: codebase]

**Research date:** 2026-07-10
**Valid until:** 2026-08-09 for codebase patterns; re-check package versions before any new package install.
