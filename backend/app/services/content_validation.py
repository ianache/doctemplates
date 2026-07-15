import re
import jinja2
from jinja2 import nodes
from jinja2.visitor import NodeVisitor
from fastapi import HTTPException

TOKEN_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")
JINJA_MARKER_PATTERN = re.compile(r"(\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\})")


def normalize_jinja_marker(marker: str) -> str:
    marker = " ".join(marker.strip().split())
    if marker.startswith("{{") and marker.endswith("}}"):
        inner = marker[2:-2].strip()
        return f"{{{{ {inner} }}}}"
    if marker.startswith("{%") and marker.endswith("%}"):
        inner = marker[2:-2].strip()
        return f"{{% {inner} %}}"
    return marker


def extract_jinja_markers(html: str) -> set[str]:
    return {normalize_jinja_marker(match.group(0)) for match in JINJA_MARKER_PATTERN.finditer(html or "")}


def validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]:
    original_markers = extract_jinja_markers(original_html)
    proposed_markers = extract_jinja_markers(proposed_html)
    missing = sorted(original_markers - proposed_markers)
    return [f"Missing preserved Jinja marker: {marker}" for marker in missing]


def extract_template_tokens(html: str) -> list[str]:
    tokens = [token.strip() for token in TOKEN_PATTERN.findall(html)]
    return list(dict.fromkeys(token for token in tokens if token))


def clean_token(token: str) -> str:
    # Remove filters
    base = token.split("|")[0].strip()
    # Normalize list indices e.g. [0] -> []
    base = re.sub(r"\[\d+\]", "[]", base)
    return base.strip()


class JinjaTokenExtractor(NodeVisitor):
    def __init__(self):
        self.scope_stack = [{}]
        self.extracted_tokens = set()

    def _get_target_names(self, target_node) -> list[str]:
        if isinstance(target_node, nodes.Name):
            return [target_node.name]
        elif isinstance(target_node, nodes.Tuple):
            names = []
            for item in target_node.items:
                names.extend(self._get_target_names(item))
            return names
        return []

    def _get_full_path(self, node) -> str | None:
        if isinstance(node, nodes.Name):
            for scope in reversed(self.scope_stack):
                if node.name in scope:
                    return scope[node.name]
            return node.name

        elif isinstance(node, nodes.Getattr):
            parent_path = self._get_full_path(node.node)
            if parent_path is None:
                return None
            return f"{parent_path}.{node.attr}"

        elif isinstance(node, nodes.Getitem):
            parent_path = self._get_full_path(node.node)
            if parent_path is None:
                return None

            if isinstance(node.arg, nodes.Const):
                val = node.arg.value
                if isinstance(val, int):
                    return f"{parent_path}[]"
                elif isinstance(val, str):
                    return f"{parent_path}.{val}"
                else:
                    return f"{parent_path}[]"
            else:
                return f"{parent_path}[]"

        elif isinstance(node, nodes.Call):
            if isinstance(node.node, nodes.Getattr):
                return self._get_full_path(node.node.node)
            return self._get_full_path(node.node)

        return None

    def visit_Name(self, node):
        if getattr(node, 'ctx', None) == 'store':
            return
        path = self._get_full_path(node)
        if path:
            self.extracted_tokens.add(path)

    def visit_Getattr(self, node):
        path = self._get_full_path(node)
        if path:
            self.extracted_tokens.add(path)

    def visit_Getitem(self, node):
        path = self._get_full_path(node)
        if path:
            self.extracted_tokens.add(path)
        self.visit(node.arg)

    def visit_Call(self, node):
        if isinstance(node.node, nodes.Getattr):
            path = self._get_full_path(node.node.node)
            if path:
                self.extracted_tokens.add(path)
        else:
            path = self._get_full_path(node.node)
            if path:
                self.extracted_tokens.add(path)

        for arg in node.args:
            self.visit(arg)
        for kwarg in node.kwargs:
            self.visit(kwarg)
        if node.dyn_args:
            self.visit(node.dyn_args)
        if node.dyn_kwargs:
            self.visit(node.dyn_kwargs)

    def visit_For(self, node):
        iter_path = self._get_full_path(node.iter)
        self.visit(node.iter)

        new_scope = {}
        targets = self._get_target_names(node.target)
        for name in targets:
            if len(targets) == 1 and iter_path:
                new_scope[name] = f"{iter_path}[]"
            else:
                new_scope[name] = None

        self.scope_stack.append(new_scope)
        for n in node.body:
            self.visit(n)
        for n in node.else_:
            self.visit(n)
        self.scope_stack.pop()

    def visit_Assign(self, node):
        val_path = self._get_full_path(node.node)
        self.visit(node.node)

        targets = self._get_target_names(node.target)
        current_scope = self.scope_stack[-1]
        for name in targets:
            if len(targets) == 1:
                current_scope[name] = val_path
            else:
                current_scope[name] = None

    def visit_AssignBlock(self, node):
        targets = self._get_target_names(node.target)
        current_scope = self.scope_stack[-1]
        for name in targets:
            current_scope[name] = None

        for n in node.body:
            self.visit(n)

    def visit_With(self, node):
        new_scope = {}
        for target, value in zip(node.targets, node.values):
            val_path = self._get_full_path(value)
            self.visit(value)
            targets = self._get_target_names(target)
            for name in targets:
                new_scope[name] = val_path

        self.scope_stack.append(new_scope)
        for n in node.body:
            self.visit(n)
        self.scope_stack.pop()

    def visit_Macro(self, node):
        current_scope = self.scope_stack[-1]
        current_scope[node.name] = None

        new_scope = {}
        for arg in node.args:
            for name in self._get_target_names(arg):
                new_scope[name] = None

        self.scope_stack.append(new_scope)
        for default in node.defaults:
            self.visit(default)
        for n in node.body:
            self.visit(n)
        self.scope_stack.pop()

    def visit_CallBlock(self, node):
        self.visit(node.call)

        new_scope = {}
        for arg in node.args:
            for name in self._get_target_names(arg):
                new_scope[name] = None

        self.scope_stack.append(new_scope)
        for default in node.defaults:
            self.visit(default)
        for n in node.body:
            self.visit(n)
        self.scope_stack.pop()


def get_ancestor_paths(schema_path: str) -> set[str]:
    parts = schema_path.split(".")
    ancestors = set()
    current = ""
    for part in parts:
        if current:
            current = f"{current}.{part}"
        else:
            current = part
        if current.endswith("[]"):
            ancestors.add(current)
            ancestors.add(current[:-2])
        else:
            ancestors.add(current)
            ancestors.add(f"{current}[]")
    return ancestors


def validate_template_tokens(html: str, allowed_tokens: list[str]) -> list[str]:
    allowed_ancestors = set()
    for token in allowed_tokens:
        allowed_ancestors.update(get_ancestor_paths(token))
    allowed_ancestors_lower = {p.lower() for p in allowed_ancestors}

    from app.services.pdf_generator import CaseInsensitiveSandboxedEnvironment, date_format_filter
    env = CaseInsensitiveSandboxedEnvironment(autoescape=True)
    env.filters["date_format"] = date_format_filter

    bypass_vars = {k.lower() for k in env.globals.keys()}
    bypass_vars.update({"loop", "self", "g", "request", "session"})

    try:
        parsed = env.parse(html)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Template syntax error: {str(e)}"
        )

    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)

    unknown = []
    validated = set()

    for raw in extractor.extracted_tokens:
        if not raw:
            continue
        base = raw.split(".")[0].split("[")[0].strip().lower()
        if base in bypass_vars:
            continue
        if raw.lower() in allowed_ancestors_lower:
            validated.add(raw)
        else:
            unknown.append(raw)

    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template tokens: {', '.join(sorted(list(set(unknown))))}",
        )

    return sorted(list(validated))


def extract_template_tokens_ast_warnings(html: str, valid_ancestors: set[str]) -> list[str]:
    valid_ancestors_lower = {p.lower() for p in valid_ancestors}

    from app.services.pdf_generator import CaseInsensitiveSandboxedEnvironment, date_format_filter
    env = CaseInsensitiveSandboxedEnvironment(autoescape=True)
    env.filters["date_format"] = date_format_filter

    bypass_vars = {k.lower() for k in env.globals.keys()}
    bypass_vars.update({"loop", "self", "g", "request", "session"})

    try:
        parsed = env.parse(html)
    except Exception as e:
        return [f"Template syntax error: {str(e)}"]

    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)

    warnings = []
    for raw in extractor.extracted_tokens:
        if not raw:
            continue
        base = raw.split(".")[0].split("[")[0].strip().lower()
        if base in bypass_vars:
            continue
        if raw.lower() not in valid_ancestors_lower:
            warnings.append(f"Token '{raw}' is not declared in schema")

    return sorted(list(set(warnings)))
