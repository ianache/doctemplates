---
phase: 07-backend-core-nested-data-case-insensitive-matching
verified: 2026-07-11T03:12:51Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
---

# Phase 7: Backend Core Nested Data and Case-Insensitive Matching Verification Report

**Phase Goal:** Support nested objects, object lists, and case-insensitive payload mapping and Jinja2 rendering on the backend.
**Verified:** 2026-07-11T03:12:51Z
**Status:** passed
**Re-verification:** No - canonical initial verification. A prior non-canonical `07-VERIFICATION.md` existed, but it had no structured frontmatter or `gaps:` section.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The API parses and validates Document Type schemas containing nested structures and object lists. | VERIFIED | `DocumentTypeFieldIn.validate_name_path` enforces nested/list segment regex and max depth in `backend/app/schemas/document_type.py:10-36`; `DocumentTypeCreate.validate_schema_structure` detects leaf/object/list conflicts in `backend/app/schemas/document_type.py:50-96`. Tests cover invalid paths, conflicts, and valid `cliente.contactos[].nombre` schemas in `backend/tests/test_document_types.py`. |
| 2 | PDF generation renders nested/list template tokens with case-insensitive resolving. | VERIFIED | `CaseInsensitiveContext`, recursive dict/list proxies, and `CaseInsensitiveSandboxedEnvironment` are wired into `render_html_page_to_pdf` in `backend/app/services/pdf_generator.py:521-553`. Integration test renders mixed-case `Cliente.Contactos` loop data and direct probe rendered `{{Cliente.Contactos[0].Nombre}}` to PDF. |
| 3 | Payload validation detects case-insensitive key collisions at any level and rejects with clear `400 Bad Request`. | VERIFIED | `check_casing_collisions` recursively records `type: casing_collision` errors in `backend/app/services/pdf_generator.py:157-183`; `validate_and_coerce_payload` raises `HTTPException(status_code=400)` on collisions in `backend/app/services/pdf_generator.py:371-381`. Unit tests cover nested `Num`/`num`; direct probe also covered flat/nested mixed collision. |
| 4 | PDF generation rejects unknown or mismatched payload fields according to schema. | VERIFIED | `validate_payload_against_schema` rejects unknown object keys, object/list shape mismatches, and type coercion failures in `backend/app/services/pdf_generator.py:303-360`. Unit tests cover unknown properties and direct probe covered dict passed to list field. |
| 5 | Missing or empty list properties do not fail API validation. | VERIFIED | Missing schema list children are coerced to `[]` in `backend/app/services/pdf_generator.py:333-335`; explicit `None` lists return `[]` in `backend/app/services/pdf_generator.py:352-354`. Unit test asserts omitted `cliente.contactos` succeeds as an empty list. |
| 6 | Original caller payload casing is preserved in persisted issuances. | VERIFIED | Generation route calls `generate_composed_pdf(design, payload, ...)` for validation/rendering, then persists `input_data=payload` in `backend/app/api/document_designs.py:458-487`. Integration test asserts DB `DocumentIssuance.input_data == payload` with mixed casing. |
| 7 | Template validation accepts case variations against schema fields. | VERIFIED | `validate_template_tokens` lowercases allowed ancestor paths and extracted paths in `backend/app/services/content_validation.py:215-232` and following validation loop. Tests cover `{{Cliente.Nombre}}` against `cliente.nombre`. |
| 8 | Template validation supports loop/list variable paths. | VERIFIED | `JinjaTokenExtractor.visit_For` maps loop target variables to `iter_path[]`; `get_ancestor_paths` admits wildcard/list ancestors in `backend/app/services/content_validation.py:197-219`. Tests cover `{% for c in cliente.contactos %}{{c.nombre}}{% endfor %}` mapping to `cliente.contactos[].nombre`. |
| 9 | Proxy wrappers protect private double-underscore lookups. | VERIFIED | `RecursiveCaseInsensitiveDict` and `RecursiveCaseInsensitiveList` reject private dunder access in `backend/app/services/pdf_generator.py:398-489`. Tests assert `__class__`, `__dict__`, and `["__class__"]` are blocked. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/app/schemas/document_type.py` | Nested/list schema path validation and structural conflict detection | VERIFIED | Substantive implementation with regex validators, depth cap, case-insensitive field uniqueness, and schema tree conflict checks. Wired through `DocumentTypeCreate` in `backend/app/api/document_types.py`. |
| `backend/app/services/pdf_generator.py` | Payload expansion, collision detection, schema validation, case-insensitive rendering proxies | VERIFIED | Substantive implementation. Wired through `generate_composed_pdf`, generation/preview API routes, and rendering path. |
| `backend/app/services/content_validation.py` | Case-insensitive template token validation and list-loop path extraction | VERIFIED | Substantive AST/token implementation. Wired through template creation route in `backend/app/api/content_templates.py:49`. |
| `backend/tests/test_document_types.py` | Schema path validation tests | VERIFIED | Focused tests passed. |
| `backend/tests/test_pdf_generator.py` | Payload validation and generator tests | VERIFIED | Focused tests passed. |
| `backend/tests/test_content_templates.py` | Template token validation tests | VERIFIED | Focused tests passed. |
| `backend/tests/test_nested_case_insensitive.py` | Integration tests for nested/case-insensitive generation | VERIFIED | Focused tests passed. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `document_types.py` | `DocumentTypeCreate` validators | FastAPI request model | WIRED | Create endpoint accepts `payload: DocumentTypeCreate`, so Pydantic validators run before DB insert. |
| `document_designs.py` | `generate_composed_pdf` | `generate_document` and `preview_document` | WIRED | Generation and preview routes call the PDF generator with the caller payload. |
| `generate_composed_pdf` | `validate_and_coerce_payload` | first step in PDF composition | WIRED | Payload validation happens before rendering or persistence. |
| `render_html_page_to_pdf` | `CaseInsensitiveSandboxedEnvironment` | environment construction | WIRED | Case-insensitive context is used for every HTML template render. |
| `content_templates.py` | `validate_template_tokens` | template create endpoint | WIRED | Template save validates extracted tokens against document type fields. |
| `generate_document` | `DocumentIssuance.input_data` | `input_data=payload` | WIRED | Raw input payload is persisted after successful generation. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `backend/app/api/document_designs.py` | `payload` | Request body for `/api/document-designs/{design_id}/generate` | Yes | FLOWING - passed into `generate_composed_pdf`, then raw payload persisted to issuance. |
| `backend/app/services/pdf_generator.py` | `expanded_payload` | `expand_payload(payload)` | Yes | FLOWING - merged flat/nested payload is collision checked and schema validated. |
| `backend/app/services/pdf_generator.py` | `coerced_dict` / `coerced_list` | schema tree plus payload | Yes | FLOWING - recursive validator returns typed nested data to template rendering. |
| `backend/app/services/content_validation.py` | `extractor.extracted_tokens` | Jinja2 AST parse of template HTML | Yes | FLOWING - unknown tokens trigger HTTP 400, valid tokens are stored on template records. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Focused Phase 7 backend tests | `rtk uv run pytest tests\test_document_types.py tests\test_pdf_generator.py tests\test_content_templates.py tests\test_nested_case_insensitive.py -q` from `backend/` | `22 passed, 1 warning in 155.44s` | PASS |
| Flat/nested casing collision, list mismatch, case-insensitive render helper probe | `rtk uv run python -c "...validate_and_coerce_payload...render_html_page_to_pdf..."` from `backend/` | `ok` | PASS |

### Probe Execution

No phase-declared `scripts/*/tests/probe-*.sh` probes were present or required for this backend implementation phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| NEST-01 | `07-01-PLAN.md` | Support nested objects in Document Type schemas API validation. | SATISFIED | Nested path regex, structure tree validation, API create wiring, and passing tests. |
| NEST-02 | `07-01-PLAN.md` | Support lists of objects using bracket wildcard notation in schemas API validation. | SATISFIED | Parent path regex permits `[]`, schema tree models list nodes, tests cover `cliente.contactos[].nombre`. |
| NEST-03 | `07-01-PLAN.md` | Validate API payload nested object/list schemas and reject unknown or mismatched fields with `400 Bad Request`. | SATISFIED | Recursive schema validator rejects unknown keys, object/list shape mismatches, and type coercion failures. |
| CASE-01 | `07-01-PLAN.md` | Implement case-insensitive matching of API payload keys to schema properties. | SATISFIED | Validator matches payload keys to schema child names via lowercase comparison. |
| CASE-02 | `07-01-PLAN.md` | Detect case-insensitive key collisions and reject `400 Bad Request`. | SATISFIED | Recursive collision detector returns structured `casing_collision` details and tests pass. |
| CASE-03 | `07-01-PLAN.md` | Render Jinja2 template tokens case-insensitively. | SATISFIED | Case-insensitive Jinja2 context and recursive proxies are used by render path; integration tests and probe passed. |

No additional Phase 7 requirement IDs were found in `.planning/REQUIREMENTS.md` beyond these six.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `backend/app/services/pdf_generator.py` | 354 | `return []` | INFO | Benign implementation for missing/empty list support, not a stub. |
| `backend/app/services/content_validation.py` | 36 | `return []` | INFO | Benign extractor default for no tokens, not a stub. |

No `TODO`, `FIXME`, `XXX`, `PLACEHOLDER`, `coming soon`, or `not implemented` markers were found in the modified implementation/test files scanned.

### Human Verification Required

None. This phase is backend-only and the required behavior was verifiable through code inspection, wiring checks, direct helper probes, and tests.

### Gaps Summary

No blocking gaps found. The phase goal is achieved in the codebase: nested object/list schemas validate, payloads are mapped case-insensitively with collision and unknown-field rejection, Jinja2 rendering resolves mixed-case nested/list tokens, and raw payload casing is preserved in persisted issuances.

---

_Verified: 2026-07-11T03:12:51Z_
_Verifier: the agent (gsd-verifier)_
