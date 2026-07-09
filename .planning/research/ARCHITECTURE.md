# Architecture Research

**Domain:** Document Generation Engine (Schema Validation & Jinja2 Case-Insensitive Templating)
**Researched:** 2026-07-09
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     API & Validation Layer                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   Payload    │  │   Template AST   │  │    Schema     │  │
│  │  Validator   │  │    Extractor     │  │   Validator   │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬───────┘  │
│         │                   │                    │          │
├─────────┼───────────────────┼────────────────────┼──────────┤
│         ▼                   ▼                    ▼          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               In-Memory Expansion Layer               │  │
│  │   - CaseInsensitiveDict                               │  │
│  │   - CaseInsensitiveList                               │  │
│  └──────────────────────────┬────────────────────────────┘  │
├─────────────────────────────┼───────────────────────────────┤
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Jinja2 Engine                      │  │
│  │   - CaseInsensitiveEnvironment                        │  │
│  │   - CaseInsensitiveContext                            │  │
│  └──────────────────────────┬────────────────────────────┘  │
├─────────────────────────────┼───────────────────────────────┤
│                             ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               PDF Compilation Pipeline                │  │
│  │   - HTML Generation  ->  PDF Compilation              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Template AST Extractor** | Parses Jinja2 template files, traverses the AST, tracks nested `for` loop iteration variable scopes, and yields normalized schema paths (e.g. `cliente.contactos[].nombre`). | Subclassing `jinja2.nodes` traversal patterns, mapping loop targets dynamically. |
| **Payload Validator** | Flattens input JSON payloads into dotted path notation (e.g. `cliente.contactos[].nombre`) and asserts all fields exist within the allowed document type schema. | Recursive traversal of Python dicts/lists, case-insensitive key comparison. |
| **Case-Insensitive Wrapper** | Wraps dicts and lists into in-memory structures supporting case-insensitive key lookups and attribute lookups while preserving original casing. | Subclassing `collections.abc.Mapping` and `collections.abc.Sequence` with key `.lower()` storage. |
| **Case-Insensitive Context** | Intercepts Jinja2's variable resolution engine at the root level, replacing the plain dictionary with a case-insensitive lookup map. | Subclassing `jinja2.runtime.Context` and overriding standard environment initialization. |

---

## Recommended Project Structure

```
backend/
├── app/
│   ├── core/
│   │   └── document/
│   │       ├── __init__.py
│   │       ├── context.py       # CaseInsensitiveDict/List wrappers & Jinja2 Context
│   │       ├── parser.py        # AST traversal & token path extraction
│   │       ├── validator.py     # Schema matching & payload flattening
│   │       └── engine.py        # Main document rendering pipeline coordinator
│   ├── models/
│   │   └── doc_type.py          # DocumentType schemas and allowed tokens
│   └── api/
│       └── v1/
│           └── generate.py      # PDF generation & validation endpoint
```

### Structure Rationale

- **`app/core/document/`**: Isolates all logic related to template syntax analysis, in-memory wrapping, and schema validation. This ensures the document templating engine has zero dependencies on web frameworks or databases.
- **`app/core/document/context.py`**: Separates wrapper logic from the parsing/AST logic to allow independent unit testing of the data resolution layers.
- **`app/core/document/parser.py`**: Houses the Jinja2 syntax tree analysis, ensuring template structure validations can be run statically during template upload.

---

## Architectural Patterns

### Pattern 1: AST-Based Template Scope & Path Extraction

**What:** Extracting used variables and nested paths directly from Jinja2's Abstract Syntax Tree (AST), tracking local variables declared by `{% for %}` loops, and resolving them to their canonical absolute schema paths.
**When to use:** Statically validating uploaded templates to guarantee they only reference allowed fields in the Document Type schema.
**Trade-offs:** 
- *Pros*: Extremely precise. Does not require rendering with mock data to discover schema paths. Catch issues immediately at design upload time.
- *Cons*: Must handle all Jinja2 control flow statements (like loops, scoping, local variables).

**Example:**
```python
import jinja2
from jinja2 import nodes

def extract_paths_with_scoping(template_source: str) -> set[str]:
    env = jinja2.Environment()
    ast = env.parse(template_source)
    paths = set()

    def resolve_path_nodes(node, scope):
        if isinstance(node, nodes.Name):
            # Resolve scoped variable name to its absolute schema prefix
            if node.name in scope:
                return list(scope[node.name])
            return [node.name]
            
        elif isinstance(node, nodes.Getattr):
            base = resolve_path_nodes(node.node, scope)
            return base + [node.attr] if base is not None else None
                
        elif isinstance(node, nodes.Getitem):
            base = resolve_path_nodes(node.node, scope)
            if base is not None:
                arg = node.arg
                if isinstance(arg, nodes.Const):
                    if isinstance(arg.value, int):
                        # Convert specific index access (e.g. contactos[0]) to wildcard pattern
                        if base:
                            base[-1] = f"{base[-1]}[]"
                            return base
                        return ["[]"]
                    elif isinstance(arg.value, str):
                        return base + [arg.value]
        return None

    def visit(node, scope):
        if isinstance(node, nodes.For):
            iter_path = resolve_path_nodes(node.iter, scope)
            if iter_path and isinstance(node.target, nodes.Name):
                prefix = list(iter_path)
                if prefix:
                    prefix[-1] = f"{prefix[-1]}[]"
                else:
                    prefix = ["[]"]
                
                # Push loop variable mapping onto current scope
                new_scope = dict(scope)
                new_scope[node.target.name] = prefix
                
                for child in node.iter_child_nodes():
                    if child is node.target or child is node.iter:
                        visit(child, scope)
                    else:
                        visit(child, new_scope)
                return
        
        path = resolve_path_nodes(node, scope)
        if path is not None:
            paths.add(".".join(path))
        else:
            for child in node.iter_child_nodes():
                visit(child, scope)

    visit(ast, {})
    # Filter out direct loop iteration variables from output
    return paths
```

### Pattern 2: Case-Insensitive Wrapper (Data Expansion)

**What:** Implementing custom dict and list wrappers (`CaseInsensitiveDict` and `CaseInsensitiveList`) that lowercase keys internally for lookups, but maintain original casing for representation and validation.
**When to use:** Parsing and handling client payloads where keys could be supplied in PascalCase (`Cliente.Nombre`), camelCase (`cliente.nombre`), or lowercase, but are checked against a single schema definition and rendered in Jinja2 templates.
**Trade-offs:**
- *Pros*: Completely transparent. Payload structure remains a map, and no pre-processing modification of the template's textual casing is required.
- *Cons*: Small lookup overhead. Need to handle collisions if the payload contains fields differing only by case.

**Example:**
```python
import collections.abc

class CaseInsensitiveDict(collections.abc.Mapping):
    def __init__(self, data):
        self._store = {}
        self._original_keys = {}
        for k, v in data.items():
            k_lower = k.lower()
            if k_lower in self._store:
                raise ValueError(
                    f"Case collision: '{k_lower}' defined multiple times "
                    f"('{self._original_keys[k_lower]}' vs '{k}')"
                )
            self._store[k_lower] = self._wrap(v)
            self._original_keys[k_lower] = k

    def _wrap(self, val):
        if isinstance(val, dict):
            return CaseInsensitiveDict(val)
        elif isinstance(val, list):
            return CaseInsensitiveList(val)
        return val

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._store[key.lower()]
        return self._store[key]

    def __iter__(self):
        return iter(self._original_keys.values())

    def __len__(self):
        return len(self._store)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'CaseInsensitiveDict' has no attribute '{name}'")

    def __contains__(self, key):
        if isinstance(key, str):
            return key.lower() in self._store
        return key in self._store


class CaseInsensitiveList(collections.abc.Sequence):
    def __init__(self, data):
        self._list = [self._wrap(item) for item in data]

    def _wrap(self, val):
        if isinstance(val, dict):
            return CaseInsensitiveDict(val)
        elif isinstance(val, list):
            return CaseInsensitiveList(val)
        return val

    def __getitem__(self, index):
        return self._list[index]

    def __len__(self):
        return len(self._list)
```

### Pattern 3: Case-Insensitive Jinja2 Variable Resolver

**What:** Subclassing Jinja2's `Context` class to intercept variable lookups and wrap the environment parameters in a `CaseInsensitiveDict`.
**When to use:** Resolving template expressions like `{{Cliente.Codigo}}` and `{{cliente.codigo}}` to the same data block under the hood.
**Trade-offs:**
- *Pros*: Works out of the box with standard Jinja2 syntax. Local variables defined inside templates via `{% set %}` work normally.
- *Cons*: Extends Jinja2 internals.

**Example:**
```python
from jinja2 import Environment
from jinja2.runtime import Context

class CaseInsensitiveContext(Context):
    def __init__(self, environment, parent, name, blocks, globals=None):
        # parent contains merged user variables and environment globals.
        # Wrapping parent makes all top-level variable lookups case-insensitive.
        super().__init__(environment, CaseInsensitiveDict(parent), name, blocks, globals)

class CaseInsensitiveEnvironment(Environment):
    context_class = CaseInsensitiveContext
```

---

## Data Flow

### Request Flow

When an API client triggers document generation, the system validates the payload schema, parses the templates, and compiles the document:

```
[API Generate Request]
          │
          ▼
   [Flatten Payload] ──► (Generates normalized keys: "cliente.contactos[].nombre")
          │
          ▼
 [Validate Schema] ──► (Compares payload keys against the Document Type flat schema)
          │
          ▼
[Wrap Data Structure] ──► (Instantiates CaseInsensitiveDict for safe variable lookups)
          │
          ▼
 [Jinja2 Context] ──► (CaseInsensitiveEnvironment maps all variables case-insensitively)
          │
          ▼
  [HTML Generated] ──► [PDF Compiler] ──► [Merge Static PDFs] ──► [Merged PDF Response]
```

### State Management

This engine is stateless; context is constructed in-memory on each request execution and is not persisted. 

### Key Data Flows

1. **Payload Schema Validation**:
   - The user passes a nested JSON request payload.
   - The system recursively traverses the JSON, producing flat path strings where list elements are represented by `[]` (wildcard format, e.g. `cliente.contactos[].nombre`).
   - Each path string is converted to lowercase and matched against the allowed document type schema (which consists of lowercased flat strings).
   - If any generated path is missing from the allowed list, a `400 Bad Request` schema error is returned immediately before rendering begins.

2. **Template Variable Validation (Offline / Admin Design View)**:
   - When a design version is uploaded/created, templates are statically compiled to their Jinja2 AST.
   - The AST is walked to extract all referenced variable paths, accounting for loops.
   - These template paths are validated against the Document Type's schema fields. If a template references a token that doesn't exist in the schema, the upload is rejected.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-1k users** | Single FastAPI/Flask app running the rendering pipeline. The case-insensitive wrappers operate entirely in memory. |
| **1k-100k users** | Cache compiled Jinja2 ASTs in memory (e.g. `lru_cache`) to avoid repeated parsing overhead during document generation requests. |
| **100k+ users** | Offload compilation of HTML to PDF (often CPU/memory heavy, e.g. Weasyprint or Chromium subprocesses) to separate worker nodes using message queues (e.g., Celery/Redis). Keep parsing and in-memory variable wrappers on the API gateway layer. |

### Scaling Priorities

1. **First bottleneck:** Parsing Jinja2 template strings on every request.
   - *Fix:* Cache parsed template objects or pre-compile templates during design activation.
2. **Second bottleneck:** Heavy CPU/memory consumption of PDF rendering engines.
   - *Fix:* Horizontal scaling of rendering workers. Ensure validation and data wrapping happen early at the API edge to avoid routing invalid requests to workers.

---

## Anti-Patterns

### Anti-Pattern 1: Deep Lowercasing Payload Keys (Mutative Normalization)
- **What people do:** Recursively lowercase all keys in the input dictionary before rendering.
- **Why it's wrong:** It destroys the original key casing. If the template contains elements that print data keys dynamically or requires preserving specific names for integration, deep mutation causes issues. It also makes error messages hard to relate back to the client's original payload casing.
- **Do this instead:** Use read-only `CaseInsensitiveDict` wrappers which preserve the original keys and values, mapping lookups dynamically.

### Anti-Pattern 2: Regex-based Template Variable Matching
- **What people do:** Match variables in template source code using regexes like `r"\{\{\s*([\w\.]+)\s*\}\}"`.
- **Why it's wrong:** Fails on expressions with spaces, method calls, filters, index brackets (e.g. `{{ cliente.contactos[0].nombre }}`), and local loop contexts (e.g. `{% for c in contactos %}{{ c.nombre }}{% endfor %}`).
- **Do this instead:** Leverage Jinja2's parser AST to perform semantic validation of template tokens, tracking local scoping rules properly.

### Anti-Pattern 3: Pre-processing Templates to Lowercase Variable Names
- **What people do:** Rewrite the user's Jinja2 template string before rendering to force all expressions to lowercase.
- **Why it's wrong:** Modifying the raw template text shifts characters and lines, meaning any syntax errors or rendering failures reported by Jinja2 will point to line numbers and expressions that do not match the user's original file.
- **Do this instead:** Intercept variable resolution using a custom `Context` and environment class so the original template runs unchanged.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **OAuth2 / OIDC** | JWT Validation middleware | API verifies caller tokens to fetch caller context. Data schemas are partitioned by client tenant. |
| **PDF Rendering Worker** | HTTP Post / Queue Task | HTML payload generated by Jinja2 is passed to a rendering agent (e.g., Weasyprint/Playwright). |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Designer (UI) ↔ Engine** | JSON Schemas / API | The designer uses schema lists to constrain drag-and-drop actions, while the engine uses it to reject generation. |
| **Data Wrapper ↔ Jinja2** | Duck-typing / Protocol | The custom dictionary inherits from `collections.abc.Mapping`, making it drop-in compatible with Jinja2's dict helper functions. |

---

## Sources

- [Jinja2 AST Parser API](https://jinja.palletsprojects.com/en/3.1.x/api/#parser)
- [Python Mapping Collections Protocol](https://docs.python.org/3/library/collections.abc.html)
- [Case Insensitive Dictionaries in Python PEP-455 (Historical)](https://peps.python.org/pep-0455/)
- [Jinja2 Runtime Context Lookup Resolution](https://github.com/pallets/jinja/blob/main/src/jinja2/runtime.py)

---
*Architecture research for: Document Template Engine Case-Insensitive and Nested Validation*
*Researched: 2026-07-09*
