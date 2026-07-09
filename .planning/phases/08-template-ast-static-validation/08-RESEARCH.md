# Phase 8: Template AST & Static Validation - Research

## User Constraints (from CONTEXT.md)

- **D-01 (Flexible Drafts, Strict Active):** Designs in `draft` status are allowed to be saved with validation warnings (warnings list returned in the JSON response). Modifying a design to `active` or `superseded` status, or saving a design that is already `active`/`superseded`, will strictly reject any undeclared variable tokens with `400 Bad Request`. [CITED: .planning/phases/08-template-ast-static-validation/08-CONTEXT.md]
- **D-02 (Scope-Aware AST Parsing):** Validation will implement a custom Jinja2 AST NodeVisitor (`jinja2.Visitor` subclass) that tracks local loop alias bindings (`For` nodes) to dynamically reconstruct the parent wildcard list path (mapping local variable lookups like `item.nombre` back to `cliente.contactos[].nombre`). [CITED: .planning/phases/08-template-ast-static-validation/08-CONTEXT.md]
- **D-03 (Dynamic Globals Bypass):** The template validator will dynamically read the configured symbols and functions in the Jinja2 environment's globals (`env.globals`). Variables found in the template matching these registered globals (case-insensitively) will be automatically skipped from schema matching. [CITED: .planning/phases/08-template-ast-static-validation/08-CONTEXT.md]
- **the agent's Discretion:** [CITED: .planning/phases/08-template-ast-static-validation/08-CONTEXT.md]
  - The exact implementation of AST NodeVisitor traversing rules and variable scope stacks.
  - The structure of warn logs returned in the draft response JSON (e.g., `warnings: ["Token 'x' not declared in schema"]`).
  - Test template variants to exercise standard loop edge cases.

---

## Technical Domain Investigation

### 1. Scope-Aware Jinja2 AST NodeVisitor
Jinja2 templates are compiled into an Abstract Syntax Tree (AST) which can be inspected using a custom subclass of `jinja2.visitor.NodeVisitor`. [VERIFIED: jinja2 runtime behavior]
To reconstruct nested path references under local loop alias bindings, we implement a scope stack (`self.scope_stack` list of dicts) during AST traversal:
- **`For` Nodes:** When entering a `For` node, we resolve the path of its iterable (`node.iter`). If it maps to a schema path (e.g., `cliente.contactos`), we bind the target variables (e.g. `c` or unpack keys) in `new_scope` mapping to the parent path with list wildcards appended (e.g., `cliente.contactos[]`). If the iterable is not a schema path (e.g., `range(10)`), we bind targets to `None` to prevent them from leaking out. We push this `new_scope` onto the scope stack before visiting body nodes, and pop it on exit. [VERIFIED: jinja2 runtime behavior]
- **`Assign` Nodes (`{% set ... %}`):** When encountering assignments, we resolve the path of the value (`node.node`). If it represents a valid schema path, we bind the target variable name to this path in the current block scope. If not, we bind the target to `None` so it is marked as a local-only variable. [VERIFIED: jinja2 runtime behavior]
- **`Call` Nodes:** To avoid registering helper function names or object methods (e.g., `.upper()`, `.strftime()`) as schema variables, we intercept `visit_Call` and visit only its arguments (`args` and keyword arguments `kwargs`), while resolving the base of the callable if it is an attribute reference (e.g., extracting `cliente.nombre` from `cliente.nombre.upper()`). [VERIFIED: jinja2 runtime behavior]
- **`Getattr` and `Getitem` Nodes:** We recursively resolve nested attribute access (dots) and item index lookups. Integer indices (e.g. `contactos[0]`) or dynamic variables (e.g. `contactos[idx]`) are normalized into the wildcard representation (`contactos[]`). [VERIFIED: jinja2 runtime behavior]

### 2. Ancestor Path Validation Strategy
Since templates can reference parent objects and loop variables (e.g. `{% for c in cliente.contactos %}` references `cliente.contactos` directly, whereas the schema declares `cliente.contactos[].nombre`), any extracted path `P` is valid if it represents either an exact match or a parent ancestor of a declared schema path `S` (case-insensitively). [VERIFIED: jinja2 runtime behavior]
We can generate all valid paths and ancestor prefix variants for a schema field path `S` by splitting the path at `.` boundaries and registering each progressive parent component (with and without `[]` list suffixes). For example, `cliente.contactos[].nombre` yields:
`{"cliente", "cliente.contactos", "cliente.contactos[]", "cliente.contactos[].nombre"}`
If an extracted path from the template exists in this generated ancestor set, validation passes. [VERIFIED: jinja2 runtime behavior]

### 3. Dynamic Globals/Context Bypass
To prevent false positives on built-in symbols and block variables:
- We dynamically read `env.globals` keys (case-insensitively).
- We append standard Jinja block-scoped context keywords: `{"loop", "self", "g", "request", "session"}`.
- Any variable node whose base segment matches one of these globals is automatically skipped from validation. [VERIFIED: jinja2 runtime behavior]

---

## Standard Stack, Patterns, and Pitfalls

### Pitfalls & Mitigations
- **Pitfall: Shadowing by Local Variable Constants**
  If a template contains `{% set temp = "draft" %}` and later uses `{{ temp }}`, a naive AST extractor might treat `temp` as a template variable and try to validate it against the schema.
  *Mitigation:* The `Assign` visitor explicitly binds `temp` to `None` in the scope stack. When resolving the variable, any reference resolving to `None` is treated as a local variable and bypassed. [VERIFIED: jinja2 runtime behavior]
- **Pitfall: Dynamic Method Call Exclusions**
  If a template utilizes `{{ cliente.nombre.upper() }}`, the AST treats `.upper` as a `Getattr`. If we do not intercept the `Call` parent node, the extractor will try to validate `cliente.nombre.upper` against the schema.
  *Mitigation:* By overriding `visit_Call` and bypassing the generic visit traversal on the target expression, we stop descending down the callable node's attribute tree and cleanly extract only the base variable (e.g., `cliente.nombre`). [VERIFIED: jinja2 runtime behavior]

---

## Confidence Assessment

| Requirement | Description | Confidence | Notes |
|:---|:---|:---|:---|
| **AST-01** | Parse Jinja2 templates using AST to extract referenced token paths (including nested objects and list fields). | **HIGH** | Extractor logic successfully verified against complex nested and loop templates in a Python prototype. |
| **AST-02** | Statically validate extracted template token paths against the Document Type schema before template/design activation. | **HIGH** | Simple ancestor-set prefix matching handles lists, wildcards, and partial references cleanly and case-insensitively. |

---

## Open Questions

1. **How should warning messages be structured?**
   **RESOLVED:** They will be formatted as `Token '{path}' is not declared in schema` and returned under `warnings: list[str]` in the API save/update JSON response for draft designs. This meets frontend display needs. [CITED: .planning/phases/08-template-ast-static-validation/08-CONTEXT.md]
2. **Should custom helper functions registered as globals in the Future be dynamically ignored?**
   **RESOLVED:** Yes, by dynamically introspecting `env.globals` at validation time, future-proofing is guaranteed. No other custom filters or tags need special bypasses beyond standard Jinja2 block globals (loop, self, etc.). [CITED: .planning/phases/08-template-ast-static-validation/08-CONTEXT.md]
