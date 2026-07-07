# Phase 2: Document Types - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 02-document-types
**Areas discussed:** Schema field model, Document type lifecycle, Creation UX, List/detail view

---

## Schema Field Model

| Option | Description | Selected |
|--------|-------------|----------|
| Name + type + description | Each field has a token name, a data type (string/number/date/boolean), and optional description | ✓ |
| Name only | Fields are just a list of allowed token names, untyped | |

**User's choice:** Name + type + description
**Notes:** Chosen to enable real validation in Phase 3 (VALID-01) and clearer schema browsing (DOCTYPE-02).

| Option | Description | Selected |
|--------|-------------|----------|
| Available convention, not enforced | Dots group related fields (cliente.nombre) but are treated as opaque strings | ✓ |
| Enforced nested structure | Platform parses dot notation into real nested schema/namespaces | |

**User's choice:** Available convention, not enforced
**Notes:** Avoids unnecessary upfront modeling work for a phase that's just "define allowed tokens."

---

## Document Type Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, freely editable | Admin can add/remove/rename fields anytime; no document-type versioning | ✓ |
| Locked after first use | Schema becomes read-only (append-only) once referenced by a design/template | |

**User's choice:** Yes, freely editable
**Notes:** Simplest for MVP1; risk of breaking references accepted for now.

| Option | Description | Selected |
|--------|-------------|----------|
| Not this phase's concern | Defer field-removal impact to Phase 3 where validation is implemented | ✓ |
| Decide now | Lock in a soft-delete/deprecate policy now | |

**User's choice:** Not this phase's concern
**Notes:** Nothing consumes the schema yet in Phase 2.

---

## Creation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Form with add/remove field rows | Dynamic form, no JSON authoring required | ✓ |
| Form + JSON import/export | Same form plus JSON paste/import option | |

**User's choice:** Form with add/remove field rows
**Notes:** Matches the "no engineering involvement" core value.

| Option | Description | Selected |
|--------|-------------|----------|
| Name + description only | Minimal top-level metadata beyond the field list | ✓ |
| Name + description + category/tags | Adds organizational tagging | |

**User's choice:** Name + description only
**Notes:** No evidence yet that MVP1 needs categorization.

---

## List/Detail View

| Option | Description | Selected |
|--------|-------------|----------|
| Name, description, field count | Simple list columns | |
| Also created-by/created-at | Adds audit info per row | ✓ |

**User's choice:** Also created-by/created-at
**Notes:** Local user record from Phase 1 already supports attribution.

| Option | Description | Selected |
|--------|-------------|----------|
| Table | Dense, scannable rows | ✓ |
| Cards | Visual card grid | |

**User's choice:** Table
**Notes:** Fits admin/operational tool conventions, scales well.

---

## Claude's Discretion

- Exact DB schema for storing typed fields (JSONB column vs. separate `document_type_fields` table)
- Detail/schema view layout specifics beyond showing the full field list with types/descriptions
- Whether the type enum (string/number/date/boolean) is fixed or extensible

## Deferred Ideas

- Category/tag system for document types
- Enforced nested-namespace schema structure
- Locking/versioning of document types themselves
- Field-removal impact handling (deferred to Phase 3)
