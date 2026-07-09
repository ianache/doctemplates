# Phase 7: Backend Core (Nested Data & Case-Insensitive Matching) - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the backend core support for nested object schemas (e.g. `cliente.direccion.calle`) and lists of objects (e.g. `cliente.contactos[].nombre`) in Document Type field definitions. Support case-insensitive key and token matching during API payload validation (which rejects unknown keys, array mismatches, and key collisions with `400 Bad Request`) and Jinja2 rendering (resolving variables like `{{Cliente.Nombre}}` dynamically without mutating caller data casing on disk).

</domain>

<decisions>
## Implementation Decisions

### Schema Definition
- **D-01 (Leaf-Only Storage):** DocumentType fields will only explicitly store leaf-level paths (e.g., `cliente.direccion.calle` of type `string` and `cliente.contactos[].nombre` of type `string`). Objects and lists are not declared as separate parent fields; the engine will dynamically infer the parent structure and type requirements based on these leaf dot/bracket notation paths.

### API Ingestion & Data Persistence
- **D-02 (Casing Preservation on Disk):** The API payload (`input_data` saved in `DocumentIssuance` database records) will be stored preserving the exact casing sent by the caller. Casing normalization will not happen at the database level, but dynamically in-memory using wrapper proxies during schema validation and template rendering.
- **D-03 (Collision Rejection):** If a payload contains duplicate keys that differ only in casing at any level (e.g., `{"Name": "Juan", "name": "Pedro"}`), the request is rejected with `400 Bad Request`.
- **D-04 (Casing Collision Error Format):** Casing collisions will return a structured JSON response mimicking Pydantic/FastAPI's validation error style, specifying the location (`loc`), the error type (`casing_collision`), and a list of conflicting keys.

### Validation Policy
- **D-05 (Permissive Lists):** Missing list properties or empty lists (e.g., `[]`) will be permitted by the validation middleware and will not throw errors. The template rendering engine will handle empty/missing lists gracefully by rendering empty blocks or skipping loops.
- **D-06 (Strict Unknown Properties):** Any undeclared JSON property in the API generation payload will be strictly rejected with `400 Bad Request` (`additionalProperties: false` equivalent).

### Template Variable Resolution
- **D-07 (Dynamic Case-Insensitive Namespace):** Render context values will be resolved case-insensitively using a custom dictionary/list mapping wrapper proxy class (`RecursiveCaseInsensitiveDict` or similar) passed to Jinja2, allowing variables of any case combination in templates to match corresponding schema tokens.

### the agent's Discretion
- The exact algorithms for recursive case-insensitive dictionary wrapping and wildcard index path mapping (`[]` replacement).
- The naming and code conventions for custom Jinja2 Environment context adapter classes.
- Test data payloads used in mock test suites.

</decisions>

<canonical_refs>
## Canonical References

### Project Requirements & Specifications
- `PRD2.md` §Document Types — Defines nested objects and case-insensitive template requirements.
- `.planning/PROJECT.md` — Core value and decisions index.
- `.planning/REQUIREMENTS.md` — Scoped requirements list for Milestone v2.0 (NEST-*, CASE-*).

### Technical Research
- `.planning/research/STACK.md` — Python box / custom casing dictionary recommendations.
- `.planning/research/FEATURES.md` — Scope definitions for nested keys and collisions.
- `.planning/research/ARCHITECTURE.md` — AST traversal and case-insensitive Jinja runtime details.
- `.planning/research/PITFALLS.md` — Overwrite risks, Jinja out-of-bounds, and security flags.
- `.planning/research/SUMMARY.md` — Consolidated research summary.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/pdf_generator.py`: Core Jinja rendering and page sequence merging. Uses `expand_flat_dict` which will need to be refactored to support case-insensitive nested parsing, lists, and collision checks.
- `backend/app/routes/document_designs.py`: Generation and preview endpoints checking schemas and permissions.
- `backend/app/auth/dependencies.py`: Session auth logic.

### Established Patterns
- Synced synchronous endpoint responses to avoid deadlocks.
- Standard FastAPI error structures (`detail: [...]`).

### Integration Points
- `/api/document-designs/{id}/generate` and `/preview` endpoints will route payload through the new validation class and case-insensitive environment wrapper.

</code_context>

<deferred>
## Deferred Ideas

- In-UI visual hierarchy tree for nested fields — deferred to Phase 10.
- Drag-and-drop table loop marker helpers in designer — deferred to Phase 10.
- Real platform-side operational data fetching (DATA-01) — out of scope.
- Signature or access protection for shared documents — deferred to future milestones.

</deferred>

---

*Phase: 07-backend-core-nested-data-case-insensitive-matching*
*Context gathered: 2026-07-09*
