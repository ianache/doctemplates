# Stack Research

**Domain:** Document Management Platform
**Researched:** 2026-07-09
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | Core application runtime | Standard language for backend services, with advanced syntax features (pattern matching, improved typing) and native library support. |
| FastAPI | 0.111.0+ | Web API framework | High-performance, asynchronous REST framework that automatically generates OpenAPI docs and implements Pydantic data validation. |
| Jinja2 | 3.1.4+ | Document template engine | Standard templating engine for Python, offering rich control structures (loops, conditionals), custom filter integrations, and AST parsing capability. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-box | 7.2.0 | Case-insensitive dot-notation access | Recommended as an external library alternative to support dot-notation (`data.key`) and case-insensitivity (`box_casesense=False`) natively. |
| jsonschema | 4.22.0 | Dynamic JSON Schema validation | Use if the system adopts JSON Schema instead of path-based schemas for complex type matching and structural verification. |
| WeasyPrint | 62.0+ | HTML to PDF rendering engine | Converts rendered HTML pages containing filled tokens into print-ready PDF files. |
| PyMuPDF | 1.24.0+ | PDF document assembly and extraction | Merges generated HTML PDFs with uploaded static PDFs, and extracts page ranges. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Fast package manager and installer | Used to resolve, lock, and install dependencies deterministically via `uv.lock`. |

## Installation

```bash
# Core dependencies
uv add fastapi uvicorn jinja2 weasyprint pymupdf

# Supporting dependencies
uv add python-box
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Custom Recursive Dict Wrapper** (`RecursiveCaseInsensitiveDict`) | `python-box` (`box_casesense=False`) | Use `python-box` if you prefer a battle-tested external library with comprehensive helper methods and don't mind the extra dependency weight. |
| **Custom Path-Based Validator** | `jsonschema` library | Use `jsonschema` if document types require highly complex JSON-standard schema matching (e.g., regex constraints, enum constraints) rather than simple presence and type checking. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `requests.structures.CaseInsensitiveDict` | Only supports case-insensitivity on the top level. It does not recursively wrap nested dictionary structures or dictionaries within lists. | A custom recursive subclass of `dict` (e.g. `RecursiveCaseInsensitiveDict`) or `python-box`. |
| Raw String/Regex Interpolation | Standard formatting (`f-strings` or `.format()`) or custom regex parser is prone to syntax errors, lacks support for complex logic (loops, conditionals), and prevents secure token validation. | Jinja2 with an AST (Abstract Syntax Tree) parsing visitor. |
| Flat Dictionary Schemas | Forcing users to flatten objects (e.g., `cliente_direccion_calle`) violates the PRD requirement for nested properties (`cliente.direccion.calle`) and lists (`cliente.contactos[]`). | Nested JSON schema validation using path prefix matching. |

## Stack Patterns by Variant

### Nested Objects and Lists of Objects
For dynamic schemas containing nested fields (`cliente.direccion.calle`) and arrays of items (`cliente.contactos[].nombre`), standard static compile-time validation (Pydantic models) is insufficient because fields are defined dynamically by admin users at runtime.

**Pattern: AST Path Extraction & Payload Path Validation**
1. **Template Extraction**: Compile the Jinja2 template and parse its AST to extract all nested variable paths.
2. **Path Verification**: Validate these extracted paths against the Document Type's schema.
3. **Payload Verification**: Construct the dot-notation paths of the incoming payload, mapping list items with `[]`, and verify they match the schema.

### Case-Insensitive Token Matching
**Pattern: Recursive Case-Insensitive Dictionary Context**
Wrap the incoming JSON payload in a dictionary subclass that overrides key access and attribute access (`__getitem__`, `__getattr__`, `__contains__`) using `casefold()`.
- When passed to Jinja2, the template rendering engine automatically resolves mixed-case paths (e.g. `{{ Cliente.Direccion.Calle }}`) against the wrapped context, even if the payload keys are lowercase or different casing.
- This ensures 100% compatibility with Jinja2 loop structures and dot-attribute resolution.

---

## Technical Implementations

### 1. Recursive Case-Insensitive Dot-Notation Dictionary

```python
import collections.abc

class RecursiveCaseInsensitiveDict(dict):
    """
    A dictionary subclass that allows case-insensitive key access and
    dot-notation attribute access. It recursively wraps nested dictionaries
    and lists containing dictionaries.
    """
    def __init__(self, data=None, **kwargs):
        super().__init__()
        self._key_map = {}  # maps casefolded_key -> original_key
        if data is not None:
            self.update(data)
        if kwargs:
            self.update(kwargs)

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            super().__setitem__(key, value)
            return

        key_lower = key.casefold()
        if key_lower in self._key_map:
            old_key = self._key_map[key_lower]
            if old_key != key:
                super().pop(old_key, None)
        
        self._key_map[key_lower] = key
        super().__setitem__(key, self._wrap(value))

    def __getitem__(self, key):
        if not isinstance(key, str):
            return super().__getitem__(key)
        key_lower = key.casefold()
        if key_lower in self._key_map:
            return super().__getitem__(self._key_map[key_lower])
        raise KeyError(key)

    def __delitem__(self, key):
        if not isinstance(key, str):
            super().__delitem__(key)
            return
        key_lower = key.casefold()
        if key_lower in self._key_map:
            original_key = self._key_map.pop(key_lower)
            super().__delitem__(original_key)
        else:
            raise KeyError(key)

    def __contains__(self, key):
        if not isinstance(key, str):
            return super().__contains__(key)
        return key.casefold() in self._key_map

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        if not isinstance(key, str):
            return super().pop(key, default)
        key_lower = key.casefold()
        if key_lower in self._key_map:
            original_key = self._key_map.pop(key_lower)
            return super().pop(original_key)
        return default

    def update(self, other=None, **kwargs):
        if other is not None:
            if hasattr(other, "keys"):
                for k in other.keys():
                    self[k] = other[k]
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def _wrap(self, value):
        if isinstance(value, dict):
            return RecursiveCaseInsensitiveDict(value)
        elif isinstance(value, (list, tuple)):
            return [self._wrap(item) for item in value]
        return value

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'RecursiveCaseInsensitiveDict' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name == "_key_map":
            super().__setattr__(name, value)
        else:
            self[name] = value
```

### 2. Jinja2 AST Variable Path Extractor

```python
from jinja2 import Environment, nodes

def get_ast_path(node):
    """
    Statically reconstructs dot-notation paths from Jinja2 AST nodes.
    Maps list indices (e.g. contacts[0]) to brackets (contacts[]).
    """
    if isinstance(node, nodes.Name):
        return node.name
    elif isinstance(node, nodes.Getattr):
        parent_path = get_ast_path(node.node)
        if parent_path:
            return f"{parent_path}.{node.attr}"
    elif isinstance(node, nodes.Getitem):
        parent_path = get_ast_path(node.node)
        if parent_path:
            arg = node.arg
            if isinstance(arg, nodes.Const):
                if isinstance(arg.value, int):
                    return f"{parent_path}[]"
                elif isinstance(arg.value, str):
                    return f"{parent_path}.{arg.value}"
            return f"{parent_path}[]"
    return None

def extract_template_paths(template_content: str) -> set[str]:
    """
    Parses a Jinja2 template and returns all unique leaf paths.
    E.g. "{{ cliente.direccion.calle }}" -> {"cliente.direccion.calle"}
    """
    env = Environment()
    try:
        ast = env.parse(template_content)
    except Exception as e:
        raise ValueError(f"Jinja2 parser syntax error: {e}")

    paths = set()
    for node in ast.find_all((nodes.Name, nodes.Getattr, nodes.Getitem)):
        path = get_ast_path(node)
        if path:
            paths.add(path)

    # Filter out prefixes so we only keep leaf tokens
    all_paths = list(paths)
    leaf_paths = set()
    for p in all_paths:
        is_prefix = False
        for other in all_paths:
            if other != p:
                if other.startswith(p + ".") or other.startswith(p + "[]"):
                    is_prefix = True
                    break
        if not is_prefix:
            leaf_paths.add(p)
    return leaf_paths
```

### 3. Payload Validator against Allowed Schema Paths

```python
def get_payload_paths(data, current_path="") -> set[str]:
    """
    Walks a JSON-like structure and yields all existing paths.
    List indices are mapped to '[]'.
    """
    paths = set()
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{current_path}.{k}" if current_path else k
            paths.add(path)
            paths.update(get_payload_paths(v, path))
    elif isinstance(data, (list, tuple)):
        for item in data:
            path = f"{current_path}[]"
            paths.add(path)
            paths.update(get_payload_paths(item, path))
    return paths

def get_prefixes(path: str) -> set[str]:
    """
    Splits a schema path into all possible valid prefixes.
    E.g. "cliente.contactos[].nombre" ->
    {"cliente", "cliente.contactos", "cliente.contactos[]", "cliente.contactos[].nombre"}
    """
    prefixes = set()
    parts = path.split('.')
    current = ""
    for part in parts:
        if current:
            if part.endswith('[]'):
                base_part = part[:-2]
                prefixes.add(f"{current}.{base_part}")
                current = f"{current}.{part}"
            else:
                current = f"{current}.{part}"
        else:
            if part.endswith('[]'):
                base_part = part[:-2]
                prefixes.add(base_part)
                current = part
            else:
                current = part
        prefixes.add(current)
    return prefixes

def validate_payload(payload: dict, allowed_schema_paths: list[str]):
    """
    Validates payload paths case-insensitively against the allowed schema list.
    Raises ValueError detailing any disallowed paths.
    """
    allowed_set = {path.casefold() for path in allowed_schema_paths}
    all_allowed = set()
    for path in allowed_set:
        all_allowed.update(get_prefixes(path))

    payload_paths = get_payload_paths(payload)
    disallowed = []
    for path in payload_paths:
        if path.casefold() not in all_allowed:
            disallowed.append(path)

    if disallowed:
        raise ValueError(f"Disallowed paths found in payload: {disallowed}")
```

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `python@3.12` | `jinja2@3.1.4` | Stable, fully supported |
| `python@3.12` | `fastapi@0.111.0` | Stable, fully supported |
| `python@3.12` | `python-box@7.2.0` | Stable, fully supported |

## Sources

- [Jinja2 AST Meta API](https://jinja.palletsprojects.com/en/3.1.x/api/#meta-api) — Used to understand syntax parsing limits and write the custom AST path builder.
- [Python Box Case Sensitivity Option](https://github.com/cdgriffith/Box/wiki/Configuration#box_casesense) — Details on native case-insensitive wrapper capability in python-box.
- [PEP 505 / Dict subclasses design patterns] — Informs the design of `RecursiveCaseInsensitiveDict` for transparent JSON serialization and native key casing preservation.

---
*Stack research for: Document Management Platform*
*Researched: 2026-07-09*
