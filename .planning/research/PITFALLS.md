# Pitfalls Research

**Domain:** Document Management Platform Template Rendering & Schema Validation
**Researched:** 2026-07-09
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Key Overwrite Collision in Case-Insensitive Nested Normalization

**What goes wrong:**
During recursive key normalization (converting dictionary keys to lowercase/casefold for case-insensitive matching), if a payload contains duplicate keys that differ only in case (e.g., `{"Name": "Alice", "name": "Bob"}`), one key will silently overwrite the other, resulting in data loss.

**Why it happens:**
Recursive key normalization utilities typically convert dict keys using `dct[k.lower()] = dct.pop(k)` or create a new dictionary by iterating and lowercasing keys. Python standard dictionaries do not support duplicate keys. Without explicit collision checking, values are discarded silently.

**How to avoid:**
1. **Collision Check:** Maintain a set of already normalized keys at the current dictionary level. If a duplicate is found, raise a `400 Bad Request` validation error.
2. **Immutable Transformations:** Never mutate input payloads in-place. Always return a new copy.
3. **Use Casefold:** Use `str.casefold()` instead of `str.lower()` to handle Unicode characters (e.g., Spanish accents or special characters) correctly.

**Warning signs:**
- Dynamic payload properties disappearing randomly in generated documents.
- API validation passes but template rendering contains incorrect data due to overwritten keys.

**Phase to address:**
Phase 3 / Active (Case-insensitive matching milestone)

---

### Pitfall 2: Silent Failures and Undefined Attributes in Jinja2 List Navigation

**What goes wrong:**
Accessing list indices in Jinja2 templates (e.g., `{{ cliente.contactos[0].nombre }}`) fails silently if the list is empty or the index is out of bounds. The template renders a blank space or `None`, generating invalid PDF documents without throwing any errors at API level.

**Why it happens:**
By default, Jinja2 evaluates unresolved indices or missing attributes to a `jinja2.Undefined` object. In default web environments, this prevents page crashes, but for official PDF generation, silent omission is extremely dangerous.

**How to avoid:**
1. **Use StrictUndefined:** Set the environment configuration `undefined=jinja2.StrictUndefined`. This forces the rendering engine to raise an `UndefinedError` if any token or index is missing or out of bounds.
2. **Pre-render Checks:** Validate the structure of arrays and minimum item counts at the API schema validation layer.
3. **Template Conditionals:** Guard accesses with `{% if cliente.contactos %}` or check length using `{% if cliente.contactos | length > 0 %}`.

**Warning signs:**
- PDFs are generated successfully but contain blank fields or placeholders.
- API requests succeed with 200 OK despite payload containing empty arrays.

**Phase to address:**
Phase 3 / Active (List of objects rendering)

---

### Pitfall 3: Case-Sensitivity Breakdown in Jinja2 Expression Engine

**What goes wrong:**
If payloads are normalized to lowercase on the backend, template variables defined in camelCase or PascalCase (e.g., `{{ cliente.Direccion }}`) will fail to resolve, raising an `UndefinedError` (if `StrictUndefined` is active) or rendering blank spaces.

**Why it happens:**
Jinja2 maps standard attribute/item access directly to Python's dictionary lookups, which are case-sensitive. Even if we normalized the incoming API payload to lowercase, the template files written by users might use mixed casing, causing mismatch errors.

**How to avoid:**
1. **Case-Insensitive Context Wrapper:** Implement a custom dictionary wrapper for the template context that overrides `__getitem__` and `__getattr__` to perform case-insensitive key lookups dynamically.
2. **Compile-time Normalization:** Parse the template AST (Abstract Syntax Tree) and normalize all variable tokens to lowercase before rendering.
3. **Strict Schema Constraints:** Reject template uploads containing keys that do not strictly match the lowercase/case-insensitive standard of the document type schema.

**Warning signs:**
- Template rendering fails with "UndefinedError" even though the payload contains the requested data in a different casing.
- Validation passes but rendering fails.

**Phase to address:**
Phase 3 / Active (Case-insensitive token and payload key matching)

---

### Pitfall 4: Vague Array Validation Paths and Structural Mismatches

**What goes wrong:**
Validation errors inside arrays of objects return generic messages or complex raw paths (e.g., `body.cliente.contactos.2.nombre`). The caller is left with cryptic messages and cannot determine which object in the array was missing keys or had invalid types.

**Why it happens:**
Most schema validation engines focus on nested JSON pointers or tuple-based error coordinates (e.g. `('cliente', 'contactos', 2, 'nombre')`). Converting these pointers to readable client messages requires custom traversal logic. Additionally, if the client sends a single dictionary instead of an array, validation libraries can fail to clarify the structural mismatch.

**How to avoid:**
1. **Error Mapper:** Implement an error handler that maps validator paths to standard JSON path notations (e.g., `cliente.contactos[2].nombre`).
2. **Strict Structural Validation:** Ensure schemas enforce `type: array` and prevent conversion of dicts into single-element arrays without explicit permission.
3. **Clear API Response Contract:** Always return a structured list of validation errors mapping the parameter path to the human-readable failure reason.

**Warning signs:**
- Clients complaining about "Validation failed" without any details on which index or object failed.
- API validation errors pointing to the wrong index due to index shifting.

**Phase to address:**
Phase 2 / Active (Schema validation milestone)

---

### Pitfall 5: Permissive Schema Coercion and Dynamic Type Failures

**What goes wrong:**
Validation libraries often perform silent type coercions (e.g., converting `"123"` to `123` or `"true"` to `True`). When these values reach the rendering context, templates that expect a string (e.g., to run string filters like `.upper()`) will raise a `TypeError` and crash rendering.

**Why it happens:**
To ease web-form handling, validation libraries (such as Pydantic or draft schema validators) try to coerce values. In document generation, this coercion can break templates that expect precise data types.

**How to avoid:**
1. **Strict Mode:** Force validation to run in strict mode (e.g., `strict=True` in Pydantic or strict type checking in JSON Schema).
2. **Type Assertion in Schema:** Ensure schemas declare exact types (e.g., strict string, integer, float) and forbid boolean-to-integer conversion.

**Warning signs:**
- `TypeError: 'int' object is not iterable` or similar errors during template rendering.
- API allows invalid payload types and fails downstream at the PDF layout step.

**Phase to address:**
Phase 2 / Active (Document Type Schemas)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Recursive lowercasing dictionary keys without check | Easy 5-line implementation. | Silent data loss if keys overlap (e.g., `Name` vs `name`). | Never. |
| Relying on Jinja2's default Undefined behavior | Templates never crash; quick prototype setup. | Incomplete/blank contracts generated and signed. | Only in local design mockup preview tool. |
| Coercing numeric payload strings to integers | Tolerant API parsing for frontend clients. | TypeErrors in Jinja2 when formatting functions run. | Only when schema explicitly permits multiple types (e.g., union). |
| Parsing template variables using RegExp | Avoids setting up a template engine compiler. | Fragile, breaks on loops, nested fields, or comments. | Never. |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| HTML-to-PDF Engine (e.g. WeasyPrint) | Referencing dynamic asset URLs (CDNs) or absolute local paths that are not accessible to the container. | Bundle and embed assets using base64 data URIs or share a volume with static assets. |
| OIDC Identity Providers | Hardcoding Issuer URL or relying on dynamic request URLs in multi-tenant environments behind reverse proxies. | Use a fixed environment config for Issuer URL and check standard proxy headers (`X-Forwarded-Proto`). |
| Jinja2 Templates (Visual Editor) | Direct injection of unescaped HTML strings from database. | Use Jinja2 autoescaping, and utilize a sanitizer like `bleach` to prune unsafe tags. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Deep recursion key-normalization | Slow API response; maximum recursion depth exceeded error. | Avoid recursive logic on massive payloads; validate maximum nesting depth (e.g., max 10 levels) at middleware. | Payload > 5MB or depth > 50 levels. |
| Unbounded template array iteration | High CPU / Memory spikes; gateway timeouts on generation endpoint. | Impose `maxItems` limits on array schemas in document definitions. | Array items > 1,000. |
| Synchronous PDF generation | Event loop block; high latency for concurrent requests. | Run generation asynchronously using worker thread pools or background tasks (Celery/rq). | Concurrent generation requests > 5. |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Server-Side Template Injection (SSTI) | Attacker accesses system globals (`__builtins__`, `config`, etc.) to run shell code. | Use Jinja2 `SandboxedEnvironment` and restrict class attributes access. |
| Local File Inclusion in PDF renderers | Attackers include `<iframe src="file:///etc/passwd">` to read local configuration files inside the generated PDF. | Disable local file access flags in the PDF engine (e.g., `--disable-local-file-access` or configuration). |
| Cross-Site Scripting (XSS) in payload | HTML tags in client payloads render markup, breaking PDF layouts or running malicious scripts. | Escape dynamic content with auto-escape filters and sanitize user inputs. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Vague 400 Bad Request error responses | Operational users cannot figure out why payload doesn't match design. | Return structured errors mapping the exact path (`cliente.contactos[1].nombre`) to the validation issue. |
| Undetected token typo in visual designer | User creates template but it generates blanks because token name has typos. | Build a template verification tool in the editor that validates parsed tokens against the schema. |
| PDF page overflow on dynamic loops | Generated pages contain orphaned header blocks or split signatures. | Apply CSS print stylesheets like `page-break-inside: avoid;` and preview with varying list lengths. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Case-Insensitive Normalization:** Often missing duplicate checking — verify that sending duplicate keys with different casings (e.g. `{"Name": "A", "name": "B"}`) returns a clear `400` error rather than silently overwriting.
- [ ] **Jinja2 Array Access:** Often missing index bounds verification — verify that retrieving `contactos[0]` when `contactos` is empty raises an `UndefinedError` rather than rendering as a blank space.
- [ ] **Array Schema Validation:** Often missing type assertion of elements — verify that passing a list of numbers to a list of dicts throws an error.
- [ ] **PDF Generator Temp Cleanup:** Often missing cleanup of intermediate files — verify that temporary HTML files or raw outputs are deleted from storage upon failure or success.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent data omission in signed contracts | HIGH | Enable `StrictUndefined` in template environment; parse original payload templates to identify missing fields; regenerate PDFs and contact affected clients if necessary. |
| Payload key collision data loss | MEDIUM | Deploy strict key normalization middleware rejecting duplicate casefolded keys; restore or audit logs to find corrupted payloads. |
| Headless PDF engine crash under load | MEDIUM | Scale memory allocations; implement a rate-limiter or a queue for generation tasks; clean up orphan system processes. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Key Overwrite on Case Normalization | Phase 3 (Active) | Unit test sending duplicate payload keys of different casings. |
| Silent Omissions in Jinja2 lists | Phase 3 (Active) | Unit test with `StrictUndefined` expecting `UndefinedError` when list elements are empty. |
| Case-Sensitivity Breakdown in Jinja2 | Phase 3 (Active) | Create dynamic lookup context wrapper and verify camelCase matches lowercased keys. |
| Cryptic/Vague Array Validation Errors | Phase 2 (Active) | Write error path formatter and verify structured error coordinates returned on payload error. |
| Permissive Schema Coercion | Phase 2 (Active) | Verify strict mode config rejects coerced type inputs (e.g. string to int). |

## Sources

- [Jinja2 Sandboxed Environment Reference Documentation](https://jinja.palletsprojects.com/en/3.1.x/sandbox/)
- [Pydantic Strict Mode Configuration](https://docs.pydantic.dev/latest/concepts/strict_mode/)
- [Weasyprint Command Line and PDF Security Docs](https://doc.courtbouillon.org/weasyprint/stable/)
- [OWASP Server-Side Template Injection Mitigation Guide](https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Server-Side_Template_Injection)

---
*Pitfalls research for: Document Management Platform*
*Researched: 2026-07-09*
