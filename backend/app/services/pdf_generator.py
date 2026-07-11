import io
import os
import uuid
from datetime import datetime, timezone
from jinja2.sandbox import SandboxedEnvironment
from xhtml2pdf import pisa
from pypdf import PdfReader, PdfWriter
from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.document_design import DocumentDesign
from app.models.content_template import HtmlTemplate
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.document_type import DocumentTypeField


def date_format_filter(value: str, format_str: str = "%d/%m/%Y") -> str:
    """Formats an ISO 8601 YYYY-MM-DD date string into a custom format string."""
    if not value:
        return ""
    try:
        # Check standard date formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime(format_str)
            except ValueError:
                continue
        return value
    except Exception:
        return value


def get_payload_value(payload: dict, path: str) -> tuple[bool, any]:
    """Helper to check and retrieve a value from flat dot-notation keys or nested dicts."""
    if path in payload:
        return True, payload[path]
    parts = path.split(".")
    d = payload
    for part in parts:
        if not isinstance(d, dict) or part not in d:
            return False, None
        d = d[part]
    return True, d


def coerce_value(val: any, field_type: str, field_name: str) -> any:
    """Coerces a value to the specified schema field type, raising ValueError on failure."""
    if val is None:
        raise ValueError(f"Value for field '{field_name}' cannot be null.")

    if field_type == "string":
        if isinstance(val, (dict, list)):
            raise ValueError(f"Cannot coerce object/list to string for field '{field_name}'.")
        return str(val)

    elif field_type == "number":
        try:
            if isinstance(val, (int, float)):
                return val
            f_val = float(val)
            if f_val.is_integer():
                return int(f_val)
            return f_val
        except (ValueError, TypeError):
            raise ValueError(f"Value '{val}' is not a valid number for field '{field_name}'.")

    elif field_type == "boolean":
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            if val == 1:
                return True
            if val == 0:
                return False
            raise ValueError(f"Value '{val}' is not a valid boolean for field '{field_name}'.")
        if isinstance(val, str):
            s = val.strip().lower()
            if s in ("true", "yes", "1", "t", "y"):
                return True
            if s in ("false", "no", "0", "f", "n"):
                return False
        raise ValueError(f"Value '{val}' is not a valid boolean for field '{field_name}'.")

    elif field_type == "date":
        if not isinstance(val, str):
            raise ValueError(f"Date value must be a string in YYYY-MM-DD format for field '{field_name}'.")
        try:
            datetime.strptime(val, "%Y-%m-%d")
            return val
        except ValueError:
            raise ValueError(f"Value '{val}' is not a valid ISO 8601 date (expected YYYY-MM-DD) for field '{field_name}'.")

    else:
        return val


import re

class SchemaNode:
    def __init__(self, node_type: str, field_type: str = None, name: str = None, description: str = None):
        self.node_type = node_type  # "leaf", "object", "list"
        self.field_type = field_type  # "string", "number", "date", "boolean" (only if leaf)
        self.name = name  # original name/casing of the field segment
        self.description = description
        self.children = {}  # key: lowercase name -> SchemaNode (if object)
        self.element_node = None  # SchemaNode (if list)


def build_schema_tree(schema_fields: list[DocumentTypeField]) -> SchemaNode:
    root = SchemaNode("object")
    
    for field in schema_fields:
        segments = field.name.split(".")
        current = root
        
        for idx, segment in enumerate(segments):
            is_last = (idx == len(segments) - 1)
            
            if segment.endswith("[]"):
                name = segment[:-2]
                lk_name = name.lower()
                is_list = True
            else:
                name = segment
                lk_name = name.lower()
                is_list = False
                
            if is_last:
                current.children[lk_name] = SchemaNode(
                    "leaf",
                    field_type=field.type,
                    name=name,
                    description=field.description
                )
            else:
                if lk_name in current.children:
                    existing = current.children[lk_name]
                    if is_list:
                        current = existing.element_node
                    else:
                        current = existing
                else:
                    if is_list:
                        element_node = SchemaNode("object", name=name)
                        list_node = SchemaNode("list", name=name)
                        list_node.element_node = element_node
                        current.children[lk_name] = list_node
                        current = element_node
                    else:
                        obj_node = SchemaNode("object", name=name)
                        current.children[lk_name] = obj_node
                        current = obj_node
    return root


def check_casing_collisions(payload: any, path: list = None) -> list[dict]:
    if path is None:
        path = []
    errors = []
    if isinstance(payload, dict):
        seen = {}
        for key in payload.keys():
            lk = key.lower()
            seen.setdefault(lk, []).append(key)
        
        for lk, keys in seen.items():
            if len(keys) > 1:
                errors.append({
                    "loc": path + [keys[0]],
                    "msg": f"Casing collision detected for key '{lk}': {', '.join(keys)}",
                    "type": "casing_collision",
                    "ctx": {"conflicting_keys": keys}
                })
        
        for key, val in payload.items():
            errors.extend(check_casing_collisions(val, path + [key]))
            
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            errors.extend(check_casing_collisions(item, path + [idx]))
            
    return errors


PATH_PART_RE = re.compile(r"([^.\[]+)(?:\[(\d+)\])?")

def parse_path(path_str: str) -> list[tuple]:
    parts = path_str.split(".")
    steps = []
    for part in parts:
        match = PATH_PART_RE.match(part)
        if not match:
            raise ValueError(f"Invalid path segment: '{part}'")
        name = match.group(1)
        idx_str = match.group(2)
        if idx_str is not None:
            steps.append(("dict", name))
            steps.append(("list_idx", int(idx_str)))
        else:
            steps.append(("dict", name))
    return steps


def set_nested_value(root: any, steps: list[tuple], value: any) -> any:
    current = root
    for i, step in enumerate(steps):
        is_last = (i == len(steps) - 1)
        step_type = step[0]
        
        if step_type == "dict":
            key = step[1]
            if is_last:
                if isinstance(current, dict):
                    if key in current and isinstance(current[key], dict) and isinstance(value, dict):
                        def merge_dicts(dest, src):
                            for k, v in src.items():
                                if k in dest and isinstance(dest[k], dict) and isinstance(v, dict):
                                    merge_dicts(dest[k], v)
                                else:
                                    dest[k] = v
                        merge_dicts(current[key], value)
                    else:
                        current[key] = value
                else:
                    raise ValueError("Expected dictionary structure but found primitive/list")
            else:
                next_step_type = steps[i+1][0]
                if next_step_type == "dict":
                    if key not in current:
                        current[key] = {}
                    elif not isinstance(current[key], dict):
                        current[key] = {}
                    current = current[key]
                elif next_step_type == "list_idx":
                    if key not in current:
                        current[key] = []
                    elif not isinstance(current[key], list):
                        current[key] = []
                    current = current[key]
        
        elif step_type == "list_idx":
            idx = step[1]
            if is_last:
                while len(current) <= idx:
                    current.append(None)
                current[idx] = value
            else:
                while len(current) <= idx:
                    current.append(None)
                
                next_step_type = steps[i+1][0]
                if current[idx] is None:
                    if next_step_type == "dict":
                        current[idx] = {}
                    elif next_step_type == "list_idx":
                        current[idx] = []
                current = current[idx]


def expand_payload(payload: dict) -> dict:
    expanded = {}
    for k, v in payload.items():
        steps = parse_path(k)
        set_nested_value(expanded, steps, v)
    return expanded


def validate_payload_against_schema(
    payload: any,
    schema_node: SchemaNode,
    mock_fallback: bool = False,
    depth: int = 0,
    parent_path: list = None
) -> any:
    if parent_path is None:
        parent_path = []
        
    if depth > 5:
        raise HTTPException(
            status_code=400,
            detail="Recursion depth limit of 5 levels exceeded in payload validation."
        )
        
    if schema_node.node_type == "leaf":
        if payload is None:
            if mock_fallback:
                if schema_node.field_type == "string":
                    return f"{schema_node.name}_val"
                elif schema_node.field_type == "number":
                    return 123.45
                elif schema_node.field_type == "boolean":
                    return True
                elif schema_node.field_type == "date":
                    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
                return None
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field '{'.'.join(str(p) for p in parent_path)}' in payload."
                )
        
        try:
            return coerce_value(payload, schema_node.field_type, ".".join(str(p) for p in parent_path))
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
            
    elif schema_node.node_type == "object":
        if payload is None:
            payload = {}
                
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Expected dictionary structure at '{'.'.join(str(p) for p in parent_path)}' but found primitive/list."
            )
            
        for k in payload.keys():
            if k.lower() not in schema_node.children:
                prop_path = ".".join(str(p) for p in parent_path + [k])
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown property '{k}' at location '{prop_path}'"
                )
                
        coerced_dict = {}
        for child_lk, child_node in schema_node.children.items():
            matching_key = next((k for k in payload.keys() if k.lower() == child_lk), None)
            
            if matching_key is None:
                if child_node.node_type == "list":
                    coerced_dict[child_node.name] = []
                else:
                    if mock_fallback:
                        coerced_dict[child_node.name] = validate_payload_against_schema(
                            None, child_node, mock_fallback=True, depth=depth+1, parent_path=parent_path + [child_node.name]
                        )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Missing required field '{'.'.join(str(p) for p in parent_path + [child_node.name])}' in payload."
                        )
            else:
                coerced_dict[matching_key] = validate_payload_against_schema(
                    payload[matching_key], child_node, mock_fallback, depth=depth+1, parent_path=parent_path + [matching_key]
                )
        return coerced_dict
        
    elif schema_node.node_type == "list":
        if payload is None:
            return []
            
        if not isinstance(payload, list):
            raise HTTPException(
                status_code=400,
                detail=f"Expected list structure at '{'.'.join(str(p) for p in parent_path)}' but found primitive/dict."
            )
            
        coerced_list = []
        for idx, item in enumerate(payload):
            coerced_item = validate_payload_against_schema(
                item, schema_node.element_node, mock_fallback, depth=depth+1, parent_path=parent_path + [idx]
            )
            coerced_list.append(coerced_item)
        return coerced_list


def validate_and_coerce_payload(
    payload: dict,
    schema_fields: list[DocumentTypeField],
    mock_fallback: bool = False
) -> dict:
    expanded = expand_payload(payload)
    collisions = check_casing_collisions(expanded)
    if collisions:
        raise HTTPException(status_code=400, detail=collisions)
    schema_tree = build_schema_tree(schema_fields)
    return validate_payload_against_schema(expanded, schema_tree, mock_fallback)


def expand_flat_dict(flat: dict[str, any]) -> dict[str, any]:
    """Converts a flat dictionary with dot-notation keys into a nested dictionary structure."""
    nested = {}
    for key, val in flat.items():
        parts = key.split(".")
        d = nested
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = val
    return nested


from jinja2.runtime import Context

class RecursiveCaseInsensitiveDict:
    def __init__(self, data: dict):
        self._data = data
        self._keys_lower = {k.lower(): k for k in data.keys()}

    def __getattribute__(self, name: str) -> any:
        if name.startswith("__") and name not in (
            "__init__",
            "__repr__",
            "__getitem__",
            "__setitem__",
            "__delitem__",
            "__contains__",
            "__len__",
            "__iter__",
            "__getattr__",
            "__getattribute__",
        ):
            raise AttributeError(f"Access to private attribute '{name}' is blocked.")
        if not name.startswith("_"):
            keys_lower = super().__getattribute__("_keys_lower")
            if name.lower() in keys_lower:
                return self[name]
        return super().__getattribute__(name)

    def __getattr__(self, name: str) -> any:
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(str(e))

    def __getitem__(self, key: str) -> any:
        if not isinstance(key, str):
            return self._data[key]
        if key.startswith("__"):
            raise KeyError(f"Private keys are protected: '{key}'")
        lk = key.lower()
        if lk in self._keys_lower:
            orig_key = self._keys_lower[lk]
            val = self._data[orig_key]
            return self._wrap_value(val)
        raise KeyError(key)

    def get(self, key: str, default: any = None) -> any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        if not isinstance(key, str):
            return key in self._data
        return key.lower() in self._keys_lower

    def _wrap_value(self, val: any) -> any:
        if isinstance(val, dict):
            return RecursiveCaseInsensitiveDict(val)
        elif isinstance(val, list):
            return RecursiveCaseInsensitiveList(val)
        return val

    def keys(self):
        return self._data.keys()

    def items(self):
        return [(k, self._wrap_value(v)) for k, v in self._data.items()]

    def values(self):
        return [self._wrap_value(v) for v in self._data.values()]

    def __repr__(self) -> str:
        return f"RecursiveCaseInsensitiveDict({self._data!r})"


class RecursiveCaseInsensitiveList:
    def __init__(self, data: list):
        self._data = data

    def __getattribute__(self, name: str) -> any:
        if name.startswith("__") and name not in (
            "__init__",
            "__repr__",
            "__getitem__",
            "__setitem__",
            "__delitem__",
            "__contains__",
            "__len__",
            "__iter__",
            "__getattr__",
            "__getattribute__",
        ):
            raise AttributeError(f"Access to private attribute '{name}' is blocked.")
        return super().__getattribute__(name)

    def __getitem__(self, idx: int) -> any:
        if isinstance(idx, str) and idx.startswith("__"):
            raise KeyError(f"Private keys are protected: '{idx}'")
        val = self._data[idx]
        if isinstance(val, dict):
            return RecursiveCaseInsensitiveDict(val)
        elif isinstance(val, list):
            return RecursiveCaseInsensitiveList(val)
        return val

    def __getattr__(self, name: str) -> any:
        raise AttributeError(f"'RecursiveCaseInsensitiveList' object has no attribute '{name}'")

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        for val in self._data:
            if isinstance(val, dict):
                yield RecursiveCaseInsensitiveDict(val)
            elif isinstance(val, list):
                yield RecursiveCaseInsensitiveList(val)
            else:
                yield val

    def __repr__(self) -> str:
        return f"RecursiveCaseInsensitiveList({self._data!r})"


class CaseInsensitiveContext(Context):
    def resolve_or_missing(self, key):
        lk = key.lower()
        matching_key = next((k for k in self.parent.keys() if k.lower() == lk), None)
        if matching_key is not None:
            val = self.parent[matching_key]
        else:
            matching_key = next((k for k in self.vars.keys() if k.lower() == lk), None)
            if matching_key is not None:
                val = self.vars[matching_key]
            else:
                return super().resolve_or_missing(key)
        
        if isinstance(val, dict):
            return RecursiveCaseInsensitiveDict(val)
        elif isinstance(val, list):
            return RecursiveCaseInsensitiveList(val)
        return val


class CaseInsensitiveSandboxedEnvironment(SandboxedEnvironment):
    context_class = CaseInsensitiveContext


def render_html_page_to_pdf(html_content: str, context: dict) -> bytes:
    """Renders a Jinja2 template and compiles it to PDF bytes using xhtml2pdf."""
    env = CaseInsensitiveSandboxedEnvironment(autoescape=True)
    env.filters["date_format"] = date_format_filter

    try:
        template = env.from_string(html_content)
        wrapped_context = context if isinstance(context, RecursiveCaseInsensitiveDict) else RecursiveCaseInsensitiveDict(context)
        rendered_html = template.render(wrapped_context)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Template rendering failed: {str(e)}"
        )

    base_css = """
    <style>
        @page {
            size: letter portrait;
            margin: 1in;
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
        }
    </style>
    """
    final_html = base_css + rendered_html

    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        src=final_html,
        dest=pdf_buffer
    )
    if pisa_status.err:
        raise HTTPException(
            status_code=500,
            detail="HTML to PDF compilation failed."
        )
    return pdf_buffer.getvalue()


def generate_composed_pdf(
    design: DocumentDesign,
    payload: dict,
    db: SQLAlchemySession,
    mock_fallback: bool = False
) -> bytes:
    """Composes a single merged PDF from a design, its pages, and client data."""
    # 1. Validate and coerce payload fields
    expanded_payload = validate_and_coerce_payload(payload, design.document_type.fields, mock_fallback)

    # 3. Pre-fetch templates and static assets to minimize DB calls in rendering loop
    template_page_ids = {page.content_id for page in design.pages if page.block_type == "html_template"}
    templates_by_id = {}
    if template_page_ids:
        templates = db.query(HtmlTemplate).filter(HtmlTemplate.id.in_(template_page_ids)).all()
        templates_by_id = {template.id: template for template in templates}

    static_page_ids = {page.content_id for page in design.pages if page.block_type == "static_pdf"}
    assets_by_id = {}
    if static_page_ids:
        assets = db.query(StaticPdfAsset).filter(StaticPdfAsset.id.in_(static_page_ids)).all()
        assets_by_id = {asset.id: asset for asset in assets}

    # 4. Merging pages
    writer = PdfWriter()

    for page in design.pages:
        if page.block_type == "html_template":
            html_content = ""
            template = templates_by_id.get(page.content_id)
            if template:
                html_content = template.html
            else:
                html_content = (page.snapshot or {}).get("html", "")

            if not html_content:
                raise HTTPException(
                    status_code=400,
                    detail=f"HTML template content is empty for page position {page.position}."
                )

            pdf_bytes = render_html_page_to_pdf(html_content, expanded_payload)
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for p in reader.pages:
                writer.add_page(p)

        elif page.block_type == "static_pdf":
            asset = assets_by_id.get(page.content_id)
            stored_path = ""
            if asset:
                stored_path = asset.stored_path
            else:
                stored_path = (page.snapshot or {}).get("stored_path", "")

            if not stored_path:
                raise HTTPException(
                    status_code=400,
                    detail=f"Static PDF asset path not specified for page position {page.position}."
                )

            if not os.path.exists(stored_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"Static PDF file not found at {stored_path} for page position {page.position}."
                )

            reader = PdfReader(stored_path)
            for p in reader.pages:
                writer.add_page(p)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported page block type '{page.block_type}' at position {page.position}."
            )

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
