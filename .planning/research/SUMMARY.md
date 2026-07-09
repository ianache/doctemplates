# Project Research Summary

**Project:** DocManagement Platform
**Domain:** Document Management & Template Generation Platform (Nested Data & Case-Insensitive Mapping)
**Researched:** 2026-07-09
**Confidence:** HIGH

## Executive Summary

The DocManagement Platform is a general-purpose document template generation engine. Experts build such engines by strictly separating concerns: schema validation, dynamic payload parsing, template syntax analysis, in-memory data normalization (wrapping context), and compilation (HTML rendering to PDF). This requires a robust backend framework (FastAPI) and template rendering engine (Jinja2) capable of analyzing templates statically, along with reliable HTML-to-PDF compilers (WeasyPrint) and PDF editing toolkits (PyMuPDF) to assemble and merge dynamic HTML pages and static PDF components in sequence.

The recommended approach based on research is to implement a Python-based rendering service. Instead of mutative JSON payload transformations that cause key collisions or using simple regex patterns that fail on complex Jinja2 loops, the system will use abstract syntax tree (AST) traversal via Jinja2's parser to statically validate template variables. For case-insensitivity, we will wrap dynamic JSON payloads in a custom `RecursiveCaseInsensitiveDict` (or leverage `python-box` with `box_casesense=False`) and subclass Jinja2's `Context` to intercept lookups transparently. Payload schemas will be validated strictly against a flat dot-notation schema list (with wildcard support `[]` for arrays).

Critical risks include case-insensitive payload key collisions (e.g. `{"Name": "Alice", "name": "Bob"}`), which can cause silent overwrites. We mitigate this by checking for duplicates in the case-folding key map and returning a 400 Bad Request error. Another major risk is silent template rendering failures where missing attributes or out-of-bound list lookups render as blank spaces; we address this by enforcing `StrictUndefined` inside the Jinja2 environment. Server-Side Template Injection (SSTI) and Local File Inclusion (LFI) in HTML-to-PDF renderers are security risks mitigated by utilizing Jinja2's `SandboxedEnvironment` and disabling local file access in the PDF engine.

## Key Findings

### Recommended Stack

Core technologies include Python 3.12 (app runtime), FastAPI (for asynchronous high-performance REST APIs), and Jinja2 (for AST-backed HTML template parsing). Dynamic data lookups are supported via a custom `RecursiveCaseInsensitiveDict` (or `python-box`), and schemas are validated using the standard `jsonschema` library. The PDF generation relies on WeasyPrint (HTML to PDF compilation) and PyMuPDF (PDF document merging and page-range extraction). Dependency management and builds are handled using `uv` for speed and determinism.

**Core technologies:**
- [Python 3.12](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md#L13): Core application runtime — Standard language for backend services with rich typing and native library support.
- [FastAPI](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md#L14): Web API framework — High-performance, asynchronous REST framework with automatic OpenAPI docs and Pydantic validation.
- [Jinja2](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md#L15): Document template engine — Standard Python templating engine offering rich loops, conditionals, and AST parsing capability.
- [python-box / custom recursive dict](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md#L21): Case-insensitive dot-notation access — Supports case-insensitive lookups on nested levels without destroying original keys.
- [WeasyPrint](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md#L23): HTML to PDF engine — Converts rendered dynamic HTML files containing filled tokens into print-ready PDF files.
- [PyMuPDF](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md#L24): PDF document assembly — Merges generated PDFs with static PDF pages and extracts pages dynamically.

### Expected Features

The feature landscape revolves around supporting nested objects (dot notation) and list iteration (brackets) inside templates to handle complex, repetitive dynamic data like invoices or agreements. The key differentiators are a bracket-notation schema builder (simplifying path configuration for non-technical users), native case-insensitive rendering proxy, strict collision checks that return explicit 400 API errors, and AST-based template-schema matching to prevent invalid template uploads.

**Must have (table stakes):**
- [Nested Property Access (Dot Notation)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L15) — Hierarchical structure lookup (`cliente.direccion.calle`) in templates.
- [List Iteration in Templates](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L16) — Repeating loop rendering (`{% for item in list %}`) for line items, invoices, and dynamic table rows.
- [Payload Schema Validation](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L17) — Asserting payload correctness against configured schema paths prior to document generation.
- [Token-to-PDF Pipeline](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L18) — Full rendering, extraction, and assembly chain (JSON/HTML -> Jinja2 -> HTML PDF -> Merge with static PDFs).

**Should have (competitive):**
- [Bracket Notation Schema Builder](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L26) — Simplified flat schema path creation for non-technical users (`contactos[].nombre`).
- [Native Case-Insensitive Rendering](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L27) — Transparent mapping of mixed-cased integration payloads to templates.
- [Collision Detection on Casing](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L28) — Rejects payloads with duplicate keys that differ only in casing with 400 Bad Request.
- [AST-Based Template-Schema Validation](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L29) — Pre-upload validation mapping Jinja2 AST node variables (including loop aliases) back to schemas.
- [List Boundary Visualization in UI](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L30) — Drag-and-drop designer helpers to guide loop bounds placement.

**Defer (v2+):**
- [Multi-Level Nested Lists](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L93) — Array inside array handling (e.g., `orders[].items[].serial_numbers[]`).
- [Dynamic Calculation Filters](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L94) — In-template safe arithmetic or format evaluations.
- [Third-Party Data Schemas](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md#L95) — Direct schema imports from external systems (OpenAPI / JSON Schema).

### Architecture Approach

The engine implements a modular, decoupled architecture consisting of an API & Validation Layer, an In-Memory Expansion Layer, the Jinja2 Template Engine, and the PDF Compilation Pipeline. The system is designed to be completely stateless, caching compiled template ASTs in memory via `lru_cache` to handle concurrent traffic. All core templating, validation, and conversion code is isolated in `app/core/document/` to remain independent of web/database frameworks.

**Major components:**
1. [Template AST Extractor (parser.py)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/ARCHITECTURE.md#L47) — Parses templates, walks nodes to resolve scopes, and maps dynamic variables back to schema definitions.
2. [Payload Validator (validator.py)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/ARCHITECTURE.md#L48) — Traverses incoming client payloads to build normalized dot-notation path sets and asserts compatibility against the schema.
3. [Case-Insensitive Wrapper (context.py)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/ARCHITECTURE.md#L49) — Provides recursive lookup proxies (`CaseInsensitiveDict` and `CaseInsensitiveList`) for in-memory payloads.
4. [Case-Insensitive Jinja Environment (engine.py / context.py)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/ARCHITECTURE.md#L50) — Intercepts Jinja2 variable lookups at the root context level to allow case-insensitive resolution transparently.
5. [PDF Compiler Pipeline (engine.py)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/ARCHITECTURE.md#L37) — Feeds interpolated HTML to Weasyprint and merges outputs with uploaded static PDFs using PyMuPDF.

### Critical Pitfalls

Based on analysis, the top critical pitfalls when building nested, case-insensitive rendering engines include:

1. [Key Overwrite Collision in Case-Insensitive Nested Normalization](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md#L9) — When normalizing keys to casefolded lowercase, duplicate keys (e.g. `{"Name": "A", "name": "B"}`) will overwrite each other. We avoid this by explicitly auditing keys at each level and returning a 400 Bad Request if a collision is found.
2. [Silent Failures and Undefined Attributes in Jinja2 List Navigation](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md#L31) — If an array is empty or an out-of-bounds index is accessed (e.g. `contactos[0].nombre` when `contactos` is empty), Jinja2 defaults to rendering blank text. Avoid this by configuring `undefined=jinja2.StrictUndefined` to raise an `UndefinedError` and fail early.
3. [Case-Sensitivity Breakdown in Jinja2 Expression Engine](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md#L53) — While payloads might be normalized, templates written by users in mixed casings (`{{ cliente.Nombre }}`) will fail to resolve. Avoid this by subclassing Jinja2's `Context` with a custom case-insensitive wrapper mapping lookups dynamically.
4. [Permissive Schema Coercion and Dynamic Type Failures](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md#L97) — Coercion of types (e.g., string `"123"` to integer `123`) can cause templates to crash on string operations. Avoid this by running schema validation in strict mode and asserting exact type compatibility.
5. [Server-Side Template Injection (SSTI) & Local File Inclusion (LFI)](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md#L150) — Attackers using template expressions or HTML tags to access system files or execute malicious code. Avoid this by utilizing a SandboxedEnvironment in Jinja2 and disabling local file access flags in the PDF engine.

## Implications for Roadmap

Based on research, suggested phase structure for Milestone 2.0 (Nested Objects and Case-Insensitive Templates):

### Phase 7: Nested Object Schemas and Payload Validation
**Rationale:** Implementing nested property parsing and bracket-notation schema validation first provides the data foundation. It enables the backend to validate nested structures before templates use them.
**Delivers:** Dot-notation parsing, JSON Schema generator support for nested schemas, validation of nested fields in payload endpoints.
**Addresses:** Dot Notation Nesting and Strict Payload Validation from [FEATURES.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md).
**Avoids:** Permissive Schema Coercion and Cryptic/Vague Array Validation Errors from [PITFALLS.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md).

### Phase 8: Case-Insensitive Context and Collision Control
**Rationale:** Case-insensitivity must be transparent to both payload validations and template rendering, so a unified lookup map is needed. Adding this ensures the templates can access fields in any casing.
**Delivers:** `RecursiveCaseInsensitiveDict` implementation, custom Jinja2 `Context` mapping, case-insensitive endpoint middleware, and casing collision checking.
**Uses:** python-box / custom recursive dict from [STACK.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/STACK.md).
**Implements:** Case-Insensitive Jinja Environment component from [ARCHITECTURE.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/ARCHITECTURE.md).

### Phase 9: Array/List Scoping and AST Validation
**Rationale:** List iteration is the most complex component because it requires scope-aware AST parsing to validate dynamic templates statically before activation. Building this last builds on the nested schema & casing layers.
**Delivers:** AST variable path extraction, loop index bounds checking, template-to-schema compiler, and visual loop helper structures in the UI.
**Addresses:** Bracket Notation Lists and AST-Based Template-Schema Validation from [FEATURES.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/FEATURES.md).
**Avoids:** Silent Failures and Undefined Attributes in Jinja2 List Navigation from [PITFALLS.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.planning/research/PITFALLS.md).

### Phase Ordering Rationale

- **Data Before Rendering:** We define and validate the data structures (Phase 7) before adjusting rendering behavior (Phases 8 & 9) so we can run integration tests with static payloads first.
- **Lookup Foundation First:** Enforcing case-insensitive dictionaries (Phase 8) provides the underlying engine logic that AST validation and loop interpolation (Phase 9) rely upon.
- **Complexity Escalation:** Loop variable scoping is the most error-prone piece of AST traversal; postponing it to Phase 9 allows the core syntax parsing logic to stabilize first.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 9:** AST scope-tracking for nested loops (e.g. resolving aliases like `item` inside nested loops to correct schema paths).
- **Phase 8:** Unicode casefolding rules (`casefold()`) to ensure consistent behavior across languages and character sets without performance penalties.

Phases with standard patterns (skip research-phase):
- **Phase 7:** Flat schema matching using standard `jsonschema` libraries.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python 3.12, FastAPI, and Jinja2 are mature, and `python-box` provides production-grade case-insensitivity. |
| Features | HIGH | Table-stakes requirements align perfectly with standard document platforms like Carbone.io and DocuSign Gen. |
| Architecture | HIGH | Decoupled modular design separates parsing, context lookup, and rendering, making testing straightforward. |
| Pitfalls | HIGH | Specific security risks (SSTI, LFI) and logic errors (overwrite collisions, silent blanks) are well-documented. |

**Overall confidence:** HIGH

### Gaps to Address

- **UI Visual Design for Loops:** How to represent visual repeating lists inside the drag-and-drop HTML layout designer needs validation.
- **Handling Multi-level Nested Lists:** Although deferred to v2+, resolving paths like `orders[].items[].serial_numbers[]` statically via AST needs future proofing.

## Sources

### Primary (HIGH confidence)
- [Jinja2 AST Meta API](https://jinja.palletsprojects.com/en/3.1.x/api/#meta-api) — Template syntax analysis and variable path extraction.
- [Python Mapping Collections Protocol](https://docs.python.org/3/library/collections.abc.html) — Dict subclass structures for casefolded lookups.
- [Pydantic Strict Mode Configuration](https://docs.pydantic.dev/latest/concepts/strict_mode/) — Input payload type verification constraints.

### Secondary (MEDIUM confidence)
- [Python Box Case Sensitivity Option](https://github.com/cdgriffith/Box/wiki/Configuration#box_casesense) — Evaluation of external libraries vs custom implementation.
- [Carbone.io Developer Documentation](https://carbone.io/) — Reference for loop iterator syntax and schema structures.

---
*Research completed: 2026-07-09*
*Ready for roadmap: yes*
