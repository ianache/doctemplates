# Feature Research

**Domain:** Document Template Generation Platform (Nested Data & Case-Insensitive Mapping)
**Researched:** 2026-07-09
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Nested Property Access (Dot Notation)** | Modern payloads are rarely flat; nesting attributes under parent namespaces (e.g., `cliente.direccion.calle`) is a standard requirement for structured data. | LOW | Handled natively by templating engines like Jinja2 using attribute lookup proxies or nested dictionaries. |
| **List Iteration in Templates** | Documents like invoices, quotes, or contracts frequently require repeating rows (e.g., repeating a row for each item in `cita.articulos[]`). | MEDIUM | Standard templating loops (`{% for item in list %}`) must be supported in the HTML renderer. |
| **Payload Schema Validation** | Ensure incoming generation payloads provide all required tokens/fields in the correct data types before rendering, preventing empty or corrupted outputs. | MEDIUM | Translated from user-defined schemas to JSON Schema for standard validation (e.g., using Python's `jsonschema` library). |
| **Token-to-PDF Pipeline** | Resolving tokens, rendering dynamic HTML via a browser/render engine, extracting static pages, and merging them in the exact design sequence. | MEDIUM | Standard pipeline: JSON + HTML → Jinja2 → Weasyprint/Playwright PDF → PyPDF page merger. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Bracket Notation Schema Builder** | Allows non-technical operational users to define complex schemas as flat token paths (e.g., `cita.articulos[].codigo`) instead of writing raw JSON Schema files. | MEDIUM | Simplifies schema configuration in the UI. A parser automatically maps paths like `parent.child[].subfield` into valid nested JSON Schemas. |
| **Native Case-Insensitive Rendering** | Removes the developer chore of mapping mismatched integration payloads. If the template uses `{{cliente.nombre}}`, it will resolve correctly even if the payload is `{"Cliente": {"nOmBrE": "Juan"}}`. | MEDIUM | Implemented via a recursive, case-insensitive context wrapper (Proxy/Dict class) in Python, passing it directly to the Jinja environment. |
| **Case-Insensitive Validation with Collision Check** | Ingested payloads are validated case-insensitively, but duplicate keys that differ only in casing (e.g. `{"name": "A", "NAME": "B"}`) are explicitly rejected with 400 errors. | LOW | Prevents ambiguous values from corrupting document generation or causing security/compliance issues. |
| **AST-Based Template-Schema Validation** | Inspects dynamic templates (including loops where variables are renamed, e.g., `{% for item in articulos %} {{ item.codigo }} {% endfor %}`) and validates their attributes against the schema. | HIGH | Uses Python's `jinja2.Environment.parse()` to extract the Abstract Syntax Tree, tracks variable aliases, and matches them to bracket-notation paths. |
| **List Boundary Visualization in UI** | The drag-and-drop designer visually highlights loop boundaries and guides the user to place array-based tokens (e.g., `articulos[].desc`) inside repeating tables. | HIGH | Prevents common formatting issues where loop tokens are placed outside repeat blocks, resulting in misaligned documents. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Dynamic Index Schema Definitions** (e.g. `contactos[0].nombre`) | Users want to bind layout tokens to specific list indices in their schema definition. | Hardcodes array sizes in the schema, breaking generic list iterations, and bloating schema management with redundant fields (`contactos[0]`, `contactos[1]`, etc.). | Enforce wildcard schema definitions (`contactos[].nombre`). Allow templates to use index lookup syntax (e.g., `{{contactos[0].nombre}}`), but validate them against the wildcard schema path. |
| **Implicit Payload Permissiveness** | Developers want the platform to accept arbitrary payloads with extra, undeclared fields without validation. | Leads to silent failures, template drift, and security issues where sensitive data is passed undetected or unused fields leak. | Enforce strict schema validation using `additionalProperties: false` in JSON Schema. Reject payloads containing undeclared keys with descriptive API errors. |
| **Case-Preserving Multi-Casing** | Users want the platform to preserve original casing variations on output/logs. | Increases engine complexity, as the platform must track multiple lookup maps and matching tables, leading to high maintenance overhead. | Normalize all incoming payload and schema keys to lowercase internally during validation and lookup. Maintain a case-folding representation for consistent error reporting. |
| **In-Template Calculations & Logic** (e.g. `{{ (precio * cant) * 1.19 }}`) | Users want to write math, string manipulation, or business rules in template tokens. | Blurs the separation of concerns. Increases template rendering failure rates and makes AST-based template validation nearly impossible. | Keep templates strictly presentational. Enforce that computed fields (e.g., `total_con_iva`) are calculated in the payload by the integration layer and defined in the schema. |

---

## Feature Dependencies

```
[Case-Insensitive Context Proxy]
    └──requires──> [Recursive Dict Wrapper]
                       └──powers──> [Case-Insensitive Jinja Rendering]

[Bracket Notation Schema Parser]
    └──requires──> [JSON Schema Generator]
                       └──powers──> [Case-Insensitive Payload Validation]

[Jinja AST Parser] 
    └──requires──> [Bracket Notation Schema Parser]
                       └──powers──> [Context-Aware Template Validator]
```

### Dependency Notes

- **[Case-Insensitive Jinja Rendering] requires [Case-Insensitive Context Proxy]:** For Jinja to render templates with arbitrary casing (e.g., accessing `cliente.nombre` matching `Cliente.Nombre`), the context dictionary supplied to Jinja must intercept lookups and recursively search for case-folded keys.
- **[Case-Insensitive Payload Validation] requires [JSON Schema Generator]:** Translating user-friendly bracket notation (`cliente.contactos[].nombre`) into a formal JSON Schema format is required before the validation engine can enforce strict payload structure and type checks.
- **[Context-Aware Template Validator] requires [Jinja AST Parser]:** Parsing the Jinja template syntax into an AST is the only way to track block scoped variables (such as local variables in loops like `item` in `{% for item in articulos %}`) and verify that nested property calls map back to bracket-notation schemas (`articulos[].codigo`).

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the core concepts of nested data and case-insensitive mapping.

- [ ] **Dot Notation Nesting (`cliente.direccion.calle`)** — Allows hierarchical objects in schemas and payloads.
- [ ] **Bracket Notation Lists (`articulos[].codigo`)** — Enables repeating structures and lists of objects in schema definition.
- [ ] **Recursive Case-Insensitive Context Proxy** — Custom dictionary adapter for python/Jinja2 to support case-insensitive token resolution during rendering.
- [ ] **Ingest Normalization & Strict Validation** — Validates payloads case-insensitively using auto-generated JSON Schema, rejecting unknown keys (`additionalProperties: false`) and case-colliding keys.
- [ ] **AST-Based Template Validator** — Validates uploaded templates prior to activation to ensure every dynamic token maps to a schema field.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **Schema Inference from Uploaded Template** — Parses an HTML/Jinja template's AST to automatically generate the document type schema.
- [ ] **Drag-and-Drop Variable Hierarchy UI** — Represents nested schemas as tree structures for easy token placement.
- [ ] **Table Component with Loop Markers** — Visual visualizer element in the drag-and-drop designer for defining list loop regions.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Multi-Level Nested Lists** — Support for deeper array nesting like `orders[].items[].serial_numbers[]`.
- [ ] **Dynamic Calculation Filters** — Safe sandbox for basic formatting/math filters in templates.
- [ ] **Third-Party Data Schemas** — Importing external schemas (e.g. OpenAPI/JSON Schema) directly as Document Type definitions.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| **Dot Notation Nesting** | HIGH | LOW | P1 |
| **Bracket Notation Lists** | HIGH | MEDIUM | P1 |
| **Case-Insensitive Rendering Proxy** | HIGH | MEDIUM | P1 |
| **Strict Payload Validation (API 400)** | HIGH | LOW | P1 |
| **AST Template Token Extraction & Validation** | HIGH | HIGH | P1 |
| **Nested Fields Tree UI** | MEDIUM | MEDIUM | P2 |
| **Drag-and-Drop Loop/Table Component** | HIGH | HIGH | P2 |
| **Schema Inference from Template** | MEDIUM | MEDIUM | P2 |
| **Multi-Level Nested Lists** | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Competitor A (DocuSign Gen API) | Competitor B (Carbone.io) | Our Approach |
|---------|---------------------------------|---------------------------|--------------|
| **Nested Objects** | Yes. Fully supported via complex JSON schemas. | Yes. Uses dot notation throughout. | Yes. Defined via flat dotted paths in a simple schema editor. |
| **Lists of Objects** | Yes. Supported inside structured JSON payloads. | Yes. Handled via iterator syntax like `d.items[i].name`. | Yes. Defined as `items[].name` in schema, rendered via standard template loops. |
| **Case-Insensitivity** | Strictly case-sensitive. Payload keys must match JSON template schema exactly. | Strictly case-sensitive. | Fully case-insensitive key lookup and schema validation, offering resilience to varying legacy integration payloads. |
| **Schema Setup** | Requires writing raw JSON Schema structure or complex model files. | Schema is inferred from the template layout file directly. | Dual approach: Schema defined in UI via simple paths or inferred from template AST, compiled to JSON Schema behind the scenes. |

## Sources

- *Carbone.io Developer Documentation* — Nested arrays and iterator syntax.
- *DocuSign Document Generation API Reference* — Schema definitions, JSON payloads, and strict casing rules.
- *Jinja2 Python AST API Docs* — Abstract Syntax Tree parsing and context resolution.
- *JSON Schema Draft-07 Specification* — Standard schema validation rules and case-sensitive property match conventions.

---
*Feature research for: Document Template Generation Platform*
*Researched: 2026-07-09*
