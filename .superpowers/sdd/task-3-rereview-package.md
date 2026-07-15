# Task 3 Re-review Package

## Git status
 M backend/app/config.py
 M backend/app/services/content_validation.py
 M backend/pyproject.toml
 M backend/uv.lock
?? backend/app/services/template_ai_agent.py
?? backend/tests/test_template_ai_proposals.py

## Key lockfile evidence

## File: backend/app/services/template_ai_agent.py
`
import json
import re
from collections import Counter
from dataclasses import dataclass

from litellm import completion

from app.services.content_validation import validate_template_tokens
from app.services.pdf_generator import render_html_page_to_pdf


UNSAFE_URL_PATTERN = re.compile(r"(https?:)?//", re.IGNORECASE)
INLINE_EVENT_PATTERN = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
JINJA_MARKER_PATTERN = re.compile(r"{{.*?}}|{%.*?%}", re.DOTALL)


@dataclass
class TemplateAiProposalResult:
    proposed_html: str
    proposed_css: str
    summary: str
    status: str
    validation_errors: list[str]
    is_applyable: bool
    provider: str
    model: str


class TemplateAiAgent:
    def __init__(
        self,
        model: str,
        enabled: bool,
        timeout_seconds: int,
        max_input_chars: int,
        max_output_tokens: int,
    ) -> None:
        self.model = model
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.max_input_chars = max_input_chars
        self.max_output_tokens = max_output_tokens

    def create_proposal(
        self,
        instruction: str,
        current_html: str,
        current_css: str,
        document_fields: list[str],
        mock_data: dict | None,
    ) -> TemplateAiProposalResult:
        if not self.enabled:
            return self._failed("AI requests are disabled.")

        input_size = len(instruction) + len(current_html) + len(current_css) + sum(len(field) for field in document_fields)
        if input_size > self.max_input_chars:
            return self._failed("Template is too large for synchronous AI improvement.")

        messages = self._build_messages(instruction, current_html, current_css, document_fields)

        try:
            response = completion(
                model=self.model,
                messages=messages,
                timeout=self.timeout_seconds,
                max_tokens=self.max_output_tokens,
            )
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:
            return self._failed(f"AI provider did not return valid JSON: {exc}")

        if not isinstance(parsed, dict):
            return self._failed("AI provider JSON response must be an object.")
        if not all(isinstance(parsed.get(field), str) for field in ("html", "css", "summary")):
            return self._failed("AI provider JSON response must include string html, css, and summary fields.")

        proposed_html = parsed["html"]
        proposed_css = parsed["css"]
        summary = parsed["summary"]
        errors = self._validate(current_html, proposed_html, proposed_css, document_fields, mock_data or {})
        status = "valid" if not errors else "invalid"

        return TemplateAiProposalResult(
            proposed_html=proposed_html,
            proposed_css=proposed_css,
            summary=summary,
            status=status,
            validation_errors=errors,
            is_applyable=status == "valid",
            provider="litellm",
            model=self.model,
        )

    def _build_messages(
        self,
        instruction: str,
        current_html: str,
        current_css: str,
        document_fields: list[str],
    ) -> list[dict[str, str]]:
        system = (
            "You improve print-friendly HTML templates. Return only JSON with keys html, css, summary. "
            "Preserve every existing Jinja expression and statement exactly. Do not add JavaScript, external URLs, "
            "external assets, or new business tokens."
        )
        user = json.dumps(
            {
                "instruction": instruction,
                "current_html": current_html,
                "current_css": current_css,
                "allowed_document_fields": document_fields,
            },
            ensure_ascii=False,
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _validate(
        self,
        current_html: str,
        proposed_html: str,
        proposed_css: str,
        document_fields: list[str],
        mock_data: dict,
    ) -> list[str]:
        errors: list[str] = []
        if not proposed_html.strip():
            errors.append("Generated HTML cannot be empty.")
        if "<script" in proposed_html.lower():
            errors.append("Generated HTML cannot include <script> tags.")
        if INLINE_EVENT_PATTERN.search(proposed_html):
            errors.append("Generated HTML cannot include inline event handlers.")
        if UNSAFE_URL_PATTERN.search(proposed_html) or UNSAFE_URL_PATTERN.search(proposed_css):
            errors.append("Generated HTML/CSS cannot reference external network assets.")

        errors.extend(self._validate_exact_jinja_marker_preservation(current_html, proposed_html))

        try:
            validate_template_tokens(proposed_html, document_fields)
        except Exception as exc:
            errors.append(str(getattr(exc, "detail", exc)))

        try:
            render_html_page_to_pdf(proposed_html, mock_data, proposed_css)
        except Exception as exc:
            errors.append(str(getattr(exc, "detail", exc)))

        return errors

    @staticmethod
    def _validate_exact_jinja_marker_preservation(current_html: str, proposed_html: str) -> list[str]:
        required_markers = Counter(JINJA_MARKER_PATTERN.findall(current_html))
        proposed_markers = Counter(JINJA_MARKER_PATTERN.findall(proposed_html))
        missing_markers = required_markers - proposed_markers

        return [
            f"Missing preserved Jinja marker: {marker}"
            for marker, count in missing_markers.items()
            for _ in range(count)
        ]

    def _failed(self, message: str) -> TemplateAiProposalResult:
        return TemplateAiProposalResult(
            proposed_html="",
            proposed_css="",
            summary="",
            status="failed",
            validation_errors=[message],
            is_applyable=False,
            provider="litellm",
            model=self.model,
        )
`

## File: backend/app/services/content_validation.py
`
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
`

## File: backend/tests/test_template_ai_proposals.py
`
import uuid

import pytest

from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers
from app.services.template_ai_agent import TemplateAiAgent


@pytest.fixture
def user(db_session):
    value = User(sub="template-ai-test", email="template-ai@example.com")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


def test_template_ai_proposal_persists_full_history(db_session, user):
    document_type = DocumentType(name="Invoice", description="Invoice document", created_by=user)
    template = HtmlTemplate(
        document_type=document_type,
        name="Invoice base",
        html="<p>{{ customer.name }}</p>",
        css="p { color: black; }",
        token_names=["customer.name"],
        created_by=user,
        mock_data={"customer": {"name": "Ada"}},
    )
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it more formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Added a section wrapper and spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )

    db_session.add(proposal)
    db_session.commit()

    saved = db_session.get(HtmlTemplateAiProposal, proposal.id)
    assert saved is not None
    assert isinstance(saved.id, uuid.UUID)
    assert saved.template_id == template.id
    assert saved.created_by_id == user.id
    assert saved.status == "valid"
    assert saved.validation_errors == []
    assert saved.is_applyable is True
    assert saved.applied_at is None


def test_extract_jinja_markers_includes_expressions_and_statements():
    html = """
    <h1>{{ customer.name }}</h1>
    {% for item in items %}
      <p>{{ item.total | date_format }}</p>
    {% endfor %}
    """

    markers = extract_jinja_markers(html)

    assert "{{ customer.name }}" in markers
    assert "{% for item in items %}" in markers
    assert "{{ item.total | date_format }}" in markers
    assert "{% endfor %}" in markers


def test_validate_preserved_jinja_markers_reports_removed_marker():
    original = "<p>{{ customer.name }}</p>{% for item in items %}{{ item.total }}{% endfor %}"
    proposed = "<p>{{ customer.name }}</p>"

    errors = validate_preserved_jinja_markers(original, proposed)

    assert "Missing preserved Jinja marker: {% for item in items %}" in errors
    assert "Missing preserved Jinja marker: {{ item.total }}" in errors
    assert "Missing preserved Jinja marker: {% endfor %}" in errors


def test_template_ai_agent_returns_applyable_result_for_valid_response(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<section><p>{{ customer.name }}</p></section>","css":"section { padding: 24px; }","summary":"Improved spacing."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Make it more formal",
        current_html="<p>{{ customer.name }}</p>",
        current_css="p { color: black; }",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "valid"
    assert result.is_applyable is True
    assert result.validation_errors == []
    assert result.proposed_html == "<section><p>{{ customer.name }}</p></section>"
    assert result.proposed_css == "section { padding: 24px; }"


def test_template_ai_agent_blocks_removed_existing_token(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<section>No token</section>","css":"","summary":"Removed token."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert "Missing preserved Jinja marker: {{ customer.name }}" in result.validation_errors


def test_template_ai_agent_blocks_script_tags(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<script>alert(1)</script><p>{{ customer.name }}</p>","css":"","summary":"Unsafe."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert "Generated HTML cannot include <script> tags." in result.validation_errors


def test_template_ai_agent_reports_failed_invalid_json(monkeypatch):
    def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "not json"}}]}

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert any("valid JSON" in error for error in result.validation_errors)


def test_template_ai_agent_blocks_removed_duplicate_jinja_marker(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<p>{{ customer.name }}</p>","css":"","summary":"Removed one marker."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p><p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert any("{{ customer.name }}" in error for error in result.validation_errors)


def test_template_ai_agent_blocks_jinja_marker_spacing_rewrite(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<p>{{customer.name}}</p>","css":"","summary":"Changed spacing."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert any("{{ customer.name }}" in error for error in result.validation_errors)


def test_template_ai_agent_fails_when_provider_returns_json_array(monkeypatch):
    def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "[]"}}]}

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert result.validation_errors


def test_template_ai_agent_fails_when_provider_returns_null_html(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {"message": {"content": '{"html":null,"css":"","summary":""}'}}
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert result.proposed_html == ""
    assert "None" not in result.proposed_html
`

## File: backend/app/config.py
`
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables.

    Values are sourced from the repo-root `.env` file (one level up from
    `backend/`) so local dev, tests, and deployment all read from a single
    typed object.
    """

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    oidc_issuer: str
    oidc_api_audience: str
    oidc_jwks_url: str | None = None
    oidc_issuer_aliases: str = ""

    database_url: str
    test_database_url: str

    session_secret: str = ""
    session_cookie_name: str = "docmanagement_session"
    session_ttl_seconds: int = 604800

    secret_key: str | None = None
    frontend_origin: str
    content_storage_root: str = "../.content-storage"
    issuance_storage_root: str = "../.content-storage/issuances"

    # Storage Decoupling Settings
    storage_provider_type: str = "local"
    storage_s3_endpoint_url: str | None = None
    storage_s3_access_key: str | None = None
    storage_s3_secret_key: str | None = None
    storage_s3_region: str | None = None
    storage_s3_bucket_static_pdfs: str = "docmanagement-static-pdfs"
    storage_s3_bucket_issuances: str = "docmanagement-issuances"

    # Celery Settings
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    celery_task_always_eager: bool = False

    ai_requests_enabled: bool = False
    ai_provider_model: str = "gpt-4o-mini"
    ai_request_timeout_seconds: int = 30
    ai_max_input_chars: int = 20000
    ai_max_output_tokens: int = 2000


settings = Settings()
`

## File: backend/pyproject.toml
`
[project]
name = "docmanagement-backend"
version = "0.1.0"
description = "Add your description here"
requires-python = ">=3.12"
dependencies = [
    "alembic>=1.18.5",
    "authlib>=1.7.2",
    "fastapi>=0.139.0",
    "httpx>=0.28.1",
    "itsdangerous>=2.2.0",
    "litellm>=1.80.0",
    "psycopg[binary]>=3.3.4",
    "pydantic-settings>=2.14.2",
    "pypdf>=6.1.0",
    "pyjwt[crypto]>=2.13.0",
    "python-dotenv>=1.2.2",
    "python-multipart>=0.0.20",
    "sqlalchemy>=2.0.51",
    "uvicorn[standard]>=0.50.0",
    "xhtml2pdf>=0.2.16",
    "jinja2>=3.1.5",
    "boto3>=1.43.46",
    "celery[redis]>=5.6.3",
]

[dependency-groups]
dev = [
    "cryptography>=49.0.0",
    "httpx>=0.28.1",
    "pytest>=9.1.1",
    "pytest-asyncio>=1.4.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
`
