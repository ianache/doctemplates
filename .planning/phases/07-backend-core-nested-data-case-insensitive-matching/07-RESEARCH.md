# Phase 7 Research: Backend Core (Nested Data & Case-Insensitive Matching)

## User Constraints (from CONTEXT.md)

### Implementation Decisions
*   **D-01 (Leaf-Only Storage):** DocumentType fields will only explicitly store leaf-level paths (e.g., `cliente.direccion.calle` of type `string` and `cliente.contactos[].nombre` of type `string`). Objects and lists are not declared as separate parent fields; the engine will dynamically infer the parent structure and type requirements based on these leaf dot/bracket notation paths. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   **D-02 (Casing Preservation on Disk):** The API payload (`input_data` saved in `DocumentIssuance` database records) will be stored preserving the exact casing sent by the caller. Casing normalization will not happen at the database level, but dynamically in-memory using wrapper proxies during schema validation and template rendering. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   **D-03 (Collision Rejection):** If a payload contains duplicate keys that differ only in casing at any level (e.g., `{"Name": "Juan", "name": "Pedro"}`), the request is rejected with `400 Bad Request`. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   **D-04 (Casing Collision Error Format):** Casing collisions will return a structured JSON response mimicking Pydantic/FastAPI's validation error style, specifying the location (`loc`), the error type (`casing_collision`), and a list of conflicting keys. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   **D-05 (Permissive Lists):** Missing list properties or empty lists (e.g., `[]`) will be permitted by the validation middleware and will not throw errors. The template rendering engine will handle empty/missing lists gracefully by rendering empty blocks or skipping loops. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   **D-06 (Strict Unknown Properties):** Any undeclared JSON property in the API generation payload will be strictly rejected with `400 Bad Request` (`additionalProperties: false` equivalent). [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   **D-07 (Dynamic Case-Insensitive Namespace):** Render context values will be resolved case-insensitively using a custom dictionary/list mapping wrapper proxy class (`RecursiveCaseInsensitiveDict` or similar) passed to Jinja2, allowing variables of any case combination in templates to match corresponding schema tokens. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]

### Agent's Discretion
*   The exact algorithms for recursive case-insensitive dictionary wrapping and wildcard index path mapping (`[]` replacement). [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   The naming and code conventions for custom Jinja2 Environment context adapter classes. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   Test data payloads used in mock test suites. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]

### Deferred Ideas
*   In-UI visual hierarchy tree for nested fields — deferred to Phase 10. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   Drag-and-drop table loop marker helpers in designer — deferred to Phase 10. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   Real platform-side operational data fetching (DATA-01) — out of scope. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
*   Signature or access protection for shared documents — deferred to future milestones. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]

## Project Constraints (from GEMINI.md)

None (no `GEMINI.md` or `.agents/GEMINI.md` files exist in the workspace).

## Phase Requirements Mapping

| Req ID | Requirement Description | Implementation Strategy |
|---|---|---|
| **NEST-01** | Support nested objects in Document Type schemas and API validation. | Define regex to validate nested path names during schema creation. Validate nested dict structures against Schema Trees. |
| **NEST-02** | Support lists of objects using bracket wildcard notation in schemas and API validation. | Use `contactos[].nombre` naming notation in `DocumentTypeField`. The Schema Tree identifies `[]` to instantiate list nodes. |
| **NEST-03** | Validate API payload against nested schemas, rejecting unknown/mismatched fields. | Walk payload recursively alongside the Schema Tree. Reject unknown fields (`D-06`) or structure mismatches with `400 Bad Request`. |
| **CASE-01** | Implement case-insensitive matching for API payload keys and schema properties. | Standardize key matching by comparing lowercase versions of payload keys and schema property names in the validation walk. |
| **CASE-02** | Detect case-insensitive key collisions and reject with `400 Bad Request`. | Pre-process the parsed payload to check for duplicate lowercase keys at any hierarchy level. Return detailed structured errors. |
| **CASE-03** | Render Jinja2 template tokens case-insensitively. | Subclass `jinja2.runtime.Context` to resolve variables case-insensitively, wrapping rendering inputs in case-insensitive dict proxies. |

## Technical Domain Analysis

### 1. Schema Parsing & Representation (Leaf-Only Storage)
Since the database only stores leaf fields (e.g. `cliente.direccion.calle`), we must infer the hierarchy dynamically at runtime. We will construct a `SchemaNode` tree:
*   **Object Nodes:** Represent parent dicts containing named children (properties).
*   **List Nodes:** Represent arrays containing an `item_schema` (typically an Object Node representing list elements).
*   **Leaf Nodes:** Represent primitive type inputs (`string`, `number`, `boolean`, `date`).

#### Path Parser Rule:
*   Any segment ending in `[]` (e.g. `items[]`) denotes a List Node.
*   Other segments denote Object Nodes, except the last segment which is a Leaf Node.
*   *Validation Heuristics:* Schema field creation will validate that paths do not have conflicting shapes (e.g. declaring `cliente` as both a primitive and a parent).

### 2. Payload Expansion
To ensure full backward-compatibility and clean schema validation, we will normalize flat dot-notation payloads (e.g., `{"cliente.nombre": "Juan"}`) into nested structures before validation.
*   **Expansion algorithm:** Recursively parses dot-notation keys and merges them into appropriate dictionaries and lists (e.g. `cliente.contactos[0].nombre` creates list indices dynamically and sets the value).

### 3. Casing Collisions Detection
A recursive function will scan the expanded payload. At each level:
*   If two keys map to the same lowercased string (e.g., `"Name"` and `"name"`), it records a collision.
*   The error lists all conflicting keys and the exact path location, e.g.:
    ```json
    {
      "loc": ["cliente", "contactos", 0, "Name"],
      "msg": "Casing collision detected for key 'name': Name, name",
      "type": "casing_collision",
      "ctx": {
        "conflicting_keys": ["Name", "name"]
      }
    }
    ```

### 4. Custom Jinja Context Resolvers
Jinja2 evaluates variables using standard dictionary lookups on its context namespace [CITED: jinja.palletsprojects.com/en/3.1.x/api/]. Unpacking the context with `**context` forces top-level keys into a standard dictionary. To maintain case-insensitivity:
*   **Top-level resolution:** Subclass `jinja2.runtime.Context` and override `resolve_or_missing` to search keys case-insensitively within `self.parent`. [CITED: jinja.palletsprojects.com/en/3.1.x/api/#jinja2.runtime.Context]
*   **Nested resolution:** Wrap dictionaries and lists in custom proxies (`RecursiveCaseInsensitiveDict` / `RecursiveCaseInsensitiveList`).
    *   `RecursiveCaseInsensitiveDict` maps `__getattr__` and `__getitem__` to case-insensitive searches in its internal data.
    *   `RecursiveCaseInsensitiveList` intercepts indices and wraps sub-dictionaries in `RecursiveCaseInsensitiveDict` upon access.

## Proposed Code Locations & Changes

### 1. `backend/app/schemas/document_type.py`
*   Add path validation regex `^[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?$` for parent segments and `^[a-zA-Z_][a-zA-Z0-9_]*$` for leaves to enforce alphanumeric structures.
*   Add a case-insensitive check and schema tree builder test in `@model_validator(mode="after")` to reject structural schema conflicts during API schema definition.

### 2. `backend/app/services/pdf_generator.py`
*   Implement `SchemaNode` class and `build_schema_tree` helper.
*   Implement `expand_payload` and `set_nested_value` helper to merge flat keys.
*   Implement `check_casing_collisions` and recursive `validate_payload_against_schema`.
*   Implement custom `CaseInsensitiveContext` and `RecursiveCaseInsensitiveDict` proxy.
*   Override `render_html_page_to_pdf` to instantiate a custom `CaseInsensitiveSandboxedEnvironment` using `CaseInsensitiveContext`.

### 3. `backend/app/services/content_validation.py`
*   Implement case-insensitive template token checks.
*   Support nested wildcard patterns (e.g. allowing loop variables `c.nombre` to map against `cliente.contactos[].nombre`) using a leaf-level lookup fallback during Phase 7.

## Risk Assessment & Pitfalls

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| **Shadowing of dict properties by `__getattr__`** | MEDIUM | Ensure custom dict wrapper only intercepts `__getattr__` for keys not already defined on the parent class (e.g., `keys`, `items`). Python does this natively by matching class attributes before invoking `__getattr__`. [ASSUMED] |
| **Non-contiguous list indices in flat payloads** | LOW | If the user inputs `contactos[2]` without `[0]` or `[1]`, the expansion yields `None` placeholders, which correctly trigger structural validation errors during the schema walk. [ASSUMED] |
| **Mutating data casing on disk** | HIGH | Rejecting collision mutations ensures the database preserves the caller's casing exactly. The case-insensitive dictionary wrapper is strictly a read-only runtime proxy. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md] |

## Open Questions

1.  **Should list schemas support lists of primitive types?** E.g. `cliente.tags[]` (type string).
    *   **RESOLVED:** No. Limit wildcard notation `[]` to lists of objects as specified by `NEST-02` (e.g. `cliente.contactos[].nombre`). Lists of primitives are not needed for this MVP. [CITED: .planning/phases/07-backend-core-nested-data-case-insensitive-matching/07-CONTEXT.md]
2.  **How should date inputs behave under coercion?**
    *   **RESOLVED:** Keep current ISO YYYY-MM-DD string coercion. If a date is parsed successfully, preserve it as a string to avoid timezone manipulation issues. [VERIFIED: backend/app/services/pdf_generator.py]
