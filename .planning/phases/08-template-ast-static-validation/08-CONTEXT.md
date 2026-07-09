# Phase 8: Template AST & Static Validation - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract referenced variable token paths from Jinja2 templates using a custom AST parser, mapping local block variables and loops (e.g. `item.nombre` inside a `for item in cliente.contactos` block) back to their parent schema field path (reconstructing `cliente.contactos[].nombre`). Implement validation logic to block saving designs (if in non-draft status) or activating designs when the extracted variable paths do not match the associated Document Type schema.

</domain>

<decisions>
## Implementation Decisions

### Save & Activation Severity
- **D-01 (Flexible Drafts, Strict Active):** Designs in `draft` status are allowed to be saved with validation warnings (warnings list returned in the JSON response). Modifying a design to `active` or `superseded` status, or saving a design that is already `active`/`superseded`, will strictly reject any undeclared variable tokens with `400 Bad Request`.

### AST Scope Resolution
- **D-02 (Scope-Aware AST Parsing):** Validation will implement a custom Jinja2 AST NodeVisitor (`jinja2.Visitor` subclass) that tracks local loop alias bindings (`For` nodes) to dynamically reconstruct the parent wildcard list path (mapping local variable lookups like `item.nombre` back to `cliente.contactos[].nombre`).

### Globals & Helper Exclusion
- **D-03 (Dynamic Globals Bypass):** The template validator will dynamically read the configured symbols and functions in the Jinja2 environment's globals (`env.globals`). Variables found in the template matching these registered globals (case-insensitively) will be automatically skipped from schema matching.

### the agent's Discretion
- The exact implementation of AST NodeVisitor traversing rules and variable scope stacks.
- The structure of warn logs returned in the draft response JSON (e.g., `warnings: ["Token 'x' not declared in schema"]`).
- Test template variants to exercise standard loop edge cases.

</decisions>

<canonical_refs>
## Canonical References

### Project Requirements & Specifications
- `PRD2.md` §Document Types — Defines nested validation and AST rules.
- `.planning/PROJECT.md` — Core value and decisions index.
- `.planning/REQUIREMENTS.md` — Scoped requirements list for Milestone v2.0 (AST-*).
- `.planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md` — Prior decisions (leaf-only field names notation).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/content_validation.py`: `validate_template_tokens` is the entry point for static template validation. It currently uses a regex-based finder which needs to be replaced/supplemented by the new Jinja2 AST NodeVisitor parser.
- `backend/app/routes/document_designs.py`: Saves and updates designs. We need to hook static validation here before updating design files or state transitions.

### Established Patterns
- Case-insensitivity helper wrappers.
- Structured response formats for FastAPI validations.

### Integration Points
- `/api/document-designs/{design_id}` update routes and `/api/document-designs` create routes will call the validator.

</code_context>

<deferred>
## Deferred Ideas

- Direct visual indicators inside the HTML designer showing missing tokens in real-time — deferred to Phase 10.

</deferred>

---

*Phase: 08-template-ast-static-validation*
*Context gathered: 2026-07-09*
