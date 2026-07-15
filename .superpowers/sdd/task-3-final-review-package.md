# Task 3 Final Re-review Package

## Report
# Task 3 Report

## Status

DONE_WITH_CONCERNS

## Files Changed

- `backend/app/services/template_ai_agent.py`
- `backend/app/config.py`
- `backend/pyproject.toml`
- `backend/tests/test_template_ai_proposals.py`
- `.superpowers/sdd/task-3-report.md`

## Tests Run and Results

- Red phase: `uv run pytest tests/test_template_ai_proposals.py -k template_ai_agent -v` failed as expected with `ModuleNotFoundError: No module named 'app.services.template_ai_agent'`.
- Focused agent tests: `python -m pytest tests/test_template_ai_proposals.py -k template_ai_agent -v -p no:cacheprovider` passed with a temporary LiteLLM test shim: 4 passed, 3 deselected.
- Syntax check: `python -m compileall -q app/services/template_ai_agent.py` passed.
- Scoped `git diff --check` passed. `backend/uv.lock` was restored after a failed dependency-resolution attempt and has no remaining changes.

## Self-Review Notes

- The service follows the specified result contract and returns failed results for disabled requests, oversized input, and invalid provider JSON.
- Generated output is validated for empty HTML, scripts, inline event handlers, external URLs, preserved Jinja markers, allowed template tokens, and PDF rendering.
- The implementation only changes the Task 3 code/config/dependency/test files plus this required report; no API routes, frontend files, or commits were made.

## Concerns

- Importing the installed `litellm==1.80.0` in this Windows environment terminates with `OPENSSL_Uplink(...): no OPENSSL_Applink`. This prevents an unshimmed pytest run despite the service importing LiteLLM exactly as required.
- `uv run` initially could not resolve packages because of certificate trust; retrying with `--native-tls` then selected LiteLLM 1.92.0, whose source build requires Rust and a writable user-profile cache that is unavailable. The project dependency remains the required `litellm>=1.80.0`; `uv.lock` was not changed.

## Task 3 Review Fix Report

### Status

DONE_WITH_CONCERNS

### Files Changed

- `backend/app/services/template_ai_agent.py`
- `backend/tests/test_template_ai_proposals.py`
- `backend/uv.lock`
- `.superpowers/sdd/task-3-report.md`

### Tests Run and Results

- Red phase: the four new regression tests failed as expected: duplicate marker removal and marker whitespace rewrites were accepted, an array raised `AttributeError`, and null HTML was coerced to `"None"`.
- `backend/.venv/Scripts/python.exe -m pytest tests/test_template_ai_proposals.py -k template_ai_agent -v -p no:cacheprovider` passed: 8 passed, 3 deselected.
- Complete target file, using an in-memory LiteLLM import shim only because the installed Windows LiteLLM import fails before tests can monkeypatch it: 11 passed, 1 existing FastAPI/httpx deprecation warning.
- `backend/.venv/Scripts/python.exe -m compileall -q app/services/template_ai_agent.py` passed.
- `UV_CACHE_DIR=backend/.uv-cache uv lock --check` passed: resolved 114 packages.
- Scoped `git diff --check` exited 0; it emitted unrelated working-tree line-ending warnings and could not read an unrelated generated PDF in `backend/tmp`.

### Lockfile

`backend/uv.lock` was updated successfully with `uv lock --native-tls` and now records `litellm 1.92.0` plus its transitive dependencies.

### Self-Review Notes

- `TemplateAiAgent` now compares raw Jinja expression and statement marker occurrences with a `Counter`, so duplicate removals and any exact-text rewrite fail validation. The Task 2 public helper remains unchanged.
- Provider responses must be JSON objects containing string `html`, `css`, and `summary` fields. Arrays, missing fields, nulls, and non-string values return failed, non-applyable proposals without coercion.
- Temporary test shims were removed. No files were staged or committed.

### Concerns

- The existing Windows virtual environment still cannot import its installed LiteLLM before monkeypatching, due to the prior `OPENSSL_Uplink(...): no OPENSSL_Applink` issue. Tests therefore used an in-memory import shim; the lockfile itself is current and validates successfully.

## Task 3 Strict Jinja Preservation Follow-up

### Status

Resolved the remaining strict Jinja preservation finding. The AI proposal validator now scans expressions and statements while tracking quoted strings and escapes, so a `}}` inside a Jinja string literal cannot terminate a marker early.

### Files Changed

- `backend/app/services/template_ai_agent.py`
- `backend/tests/test_template_ai_proposals.py`
- `.superpowers/sdd/task-3-report.md`

### Tests Run and Results

- The direct `uv run pytest` command could not access the user-level uv cache, and direct pytest collection remains blocked by the existing Windows LiteLLM OpenSSL import problem.
- With an in-memory LiteLLM import shim, `backend/.venv/Scripts/python.exe -m pytest tests/test_template_ai_proposals.py -v -p no:cacheprovider` passed: 12 passed, 1 existing FastAPI/httpx deprecation warning.
- `backend/.venv/Scripts/python.exe -m compileall -q app/services/template_ai_agent.py` passed.

### Self-Review Notes

- Added regression coverage proving that changing `{{ '}}' }}` to `{{ '}}' | upper }}` produces an invalid, non-applyable proposal and reports the missing original marker.
- The scanner preserves duplicate-occurrence counting and exact raw marker comparison while remaining local to `template_ai_agent.py`; Task 2 public helpers were not changed.
- Reviewed the scoped files after verification. No files were staged or committed.

### Concerns

- The local Windows LiteLLM import remains unsuitable for direct test collection before monkeypatching, so the focused suite required the temporary in-memory shim. The suite has one pre-existing FastAPI/httpx deprecation warning.

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
        required_markers = Counter(TemplateAiAgent._extract_jinja_markers(current_html))
        proposed_markers = Counter(TemplateAiAgent._extract_jinja_markers(proposed_html))
        missing_markers = required_markers - proposed_markers

        return [
            f"Missing preserved Jinja marker: {marker}"
            for marker, count in missing_markers.items()
            for _ in range(count)
        ]

    @staticmethod
    def _extract_jinja_markers(html: str) -> list[str]:
        markers: list[str] = []
        position = 0

        while position < len(html):
            expression_start = html.find("{{", position)
            statement_start = html.find("{%", position)
            starts = [start for start in (expression_start, statement_start) if start != -1]
            if not starts:
                break

            marker_start = min(starts)
            marker_end = "}}" if marker_start == expression_start else "%}"
            marker_close = TemplateAiAgent._find_jinja_marker_close(html, marker_start + 2, marker_end)
            if marker_close is None:
                position = marker_start + 2
                continue

            markers.append(html[marker_start : marker_close + len(marker_end)])
            position = marker_close + len(marker_end)

        return markers

    @staticmethod
    def _find_jinja_marker_close(html: str, position: int, marker_end: str) -> int | None:
        quote: str | None = None
        escaped = False

        while position < len(html):
            character = html[position]
            if quote is not None:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
            elif character in ("'", '"'):
                quote = character
            elif html.startswith(marker_end, position):
                return position

            position += 1

        return None

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


def test_template_ai_agent_blocks_jinja_marker_rewrite_with_closing_delimiter_in_string(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<p>{{ \'}}\' | upper }}</p>","css":"","summary":"Changed expression."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ '}}' }}</p>",
        current_css="",
        document_fields=[],
        mock_data={},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert "Missing preserved Jinja marker: {{ '}}' }}" in result.validation_errors


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
