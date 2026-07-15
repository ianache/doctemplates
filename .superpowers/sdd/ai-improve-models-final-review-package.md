# AI Improve Models Final Review Package

## backend/app/services/ai_model_catalog.py
```
from dataclasses import dataclass


@dataclass(frozen=True)
class AiModelOption:
    id: str
    provider: str
    label: str
    requires: str


@dataclass(frozen=True)
class AiModelCatalog:
    enabled: bool
    default_model: str
    models: list[AiModelOption]


def _split_models(raw_value: str) -> list[str]:
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _provider_for_model(model_id: str) -> str:
    if "/" not in model_id:
        return "openai"
    return model_id.split("/", 1)[0]


def _label_for_model(model_id: str) -> str:
    provider = _provider_for_model(model_id)
    name = model_id.split("/", 1)[1] if "/" in model_id else model_id
    provider_prefix = f"{provider}-"
    if name.lower().startswith(provider_prefix.lower()):
        name = name[len(provider_prefix) :]
    return f"{provider.title()} {name.replace('-', ' ').replace('_', ' ').title()}"


def _required_config(provider: str) -> str:
    return {
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "ollama": "OLLAMA_API_BASE",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(provider, "")


def build_ai_model_catalog(settings) -> AiModelCatalog:
    model_ids = _split_models(settings.ai_allowed_models)
    default_model = settings.ai_default_model or settings.ai_provider_model
    if model_ids and default_model not in model_ids:
        raise ValueError("AI default model must be included in AI_ALLOWED_MODELS.")
    return AiModelCatalog(
        enabled=settings.ai_requests_enabled,
        default_model=default_model,
        models=[
            AiModelOption(
                id=model_id,
                provider=_provider_for_model(model_id),
                label=_label_for_model(model_id),
                requires=_required_config(_provider_for_model(model_id)),
            )
            for model_id in model_ids
        ],
    )


def resolve_ai_model(settings, requested_model: str | None) -> AiModelOption:
    catalog = build_ai_model_catalog(settings)
    if not catalog.models:
        raise ValueError("No AI models are configured.")
    selected_model = requested_model or catalog.default_model
    for option in catalog.models:
        if option.id == selected_model:
            return option
    raise ValueError("AI model is not allowed.")


def is_provider_configured(settings, option: AiModelOption) -> bool:
    config_values = {
        "GEMINI_API_KEY": settings.gemini_api_key,
        "GROQ_API_KEY": settings.groq_api_key,
        "OPENAI_API_KEY": settings.openai_api_key,
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "OLLAMA_API_BASE": settings.ollama_api_base,
    }
    if not option.requires:
        return True
    return bool(config_values[option.requires])
```

## backend/app/api/ai_models.py
```
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models.user import User
from app.services.ai_model_catalog import build_ai_model_catalog

router = APIRouter(prefix="/api/content/ai-models", tags=["ai-models"])


class AiModelOptionOut(BaseModel):
    id: str
    provider: str
    label: str
    requires: str


class AiModelCatalogOut(BaseModel):
    enabled: bool
    default_model: str
    models: list[AiModelOptionOut]


@router.get("", response_model=AiModelCatalogOut)
def get_ai_models(user: User = Depends(get_current_user)) -> AiModelCatalogOut:
    catalog = build_ai_model_catalog(settings)
    return AiModelCatalogOut(
        enabled=catalog.enabled,
        default_model=catalog.default_model,
        models=[AiModelOptionOut(**model.__dict__) for model in catalog.models],
    )
```

## backend/app/config.py
```
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
    ai_default_model: str = "gpt-4o-mini"
    ai_allowed_models: str = "gpt-4o-mini"
    ai_provider_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_api_base: str = "http://localhost:11434"
    ai_request_timeout_seconds: int = 30
    ai_max_input_chars: int = 20000
    ai_max_output_tokens: int = 2000


settings = Settings()
```

## backend/app/main.py
```
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.content_templates import router as content_templates_router
from app.api.document_designs import router as document_designs_router
from app.api.document_types import router as document_types_router
from app.api.health import router as health_router
from app.api import ai_models
from app.api.issuances import public_router as public_issuances_router
from app.api.issuances import router as issuances_router
from app.api.static_pdfs import router as static_pdfs_router
from app.api.template_ai_proposals import router as template_ai_proposals_router
from app.config import settings

app = FastAPI(title="DocManagement API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(document_types_router)
app.include_router(content_templates_router)
app.include_router(static_pdfs_router)
app.include_router(document_designs_router)
app.include_router(issuances_router)
app.include_router(public_issuances_router)
app.include_router(template_ai_proposals_router)
app.include_router(ai_models.router)


@app.get("/")
def root() -> dict[str, str]:
    """Trivial unauthenticated liveness check.

    NOT the protected health endpoint required by AUTH-01 — that endpoint
    is added later (at `/api/health`) once auth gating exists.
    """
    return {"status": "ok"}
```

## backend/app/schemas/template_ai_proposal.py
```
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HtmlTemplateAiProposalCreate(BaseModel):
    instruction: str
    current_html: str
    current_css: str | None = ""
    mock_data: dict | None = None
    model: str | None = None


class HtmlTemplateAiProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    created_by_id: UUID
    instruction: str
    input_html: str
    input_css: str
    proposed_html: str
    proposed_css: str
    summary: str
    provider: str
    model: str
    status: str
    validation_errors: list[str]
    is_applyable: bool
    applied_at: datetime | None
    created_at: datetime
```

## backend/app/api/template_ai_proposals.py
```
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.schemas.template_ai_proposal import HtmlTemplateAiProposalCreate, HtmlTemplateAiProposalOut

router = APIRouter(prefix="/api/content/templates/{template_id}/ai-proposals", tags=["template-ai-proposals"])


def _load_template(template_id: UUID, db: SQLAlchemySession) -> HtmlTemplate:
    template = (
        db.query(HtmlTemplate)
        .options(
            joinedload(HtmlTemplate.document_type).joinedload(DocumentType.fields),
            joinedload(HtmlTemplate.created_by),
        )
        .filter(HtmlTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("", response_model=HtmlTemplateAiProposalOut, status_code=201)
def create_ai_proposal(
    template_id: UUID,
    payload: HtmlTemplateAiProposalCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateAiProposalOut:
    from app.services.template_ai_agent import TemplateAiAgent
    from app.services.ai_model_catalog import is_provider_configured, resolve_ai_model

    template = _load_template(template_id, db)
    try:
        selected_model = resolve_ai_model(settings, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    agent = TemplateAiAgent(
        model=selected_model.id,
        enabled=settings.ai_requests_enabled,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_input_chars=settings.ai_max_input_chars,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    if is_provider_configured(settings, selected_model):
        result = agent.create_proposal(
            instruction=payload.instruction,
            current_html=payload.current_html,
            current_css=payload.current_css or "",
            document_fields=[field.name for field in template.document_type.fields],
            mock_data=payload.mock_data or template.mock_data or {},
        )
    else:
        result = agent.provider_configuration_failed()
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction=payload.instruction,
        input_html=payload.current_html,
        input_css=payload.current_css or "",
        proposed_html=result.proposed_html,
        proposed_css=result.proposed_css,
        summary=result.summary,
        provider=result.provider,
        model=result.model,
        status=result.status,
        validation_errors=result.validation_errors,
        is_applyable=result.is_applyable,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get("", response_model=list[HtmlTemplateAiProposalOut])
def list_ai_proposals(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[HtmlTemplateAiProposalOut]:
    _load_template(template_id, db)
    return (
        db.query(HtmlTemplateAiProposal)
        .filter(HtmlTemplateAiProposal.template_id == template_id)
        .order_by(HtmlTemplateAiProposal.created_at.desc())
        .all()
    )


@router.post("/{proposal_id}/apply", response_model=HtmlTemplateAiProposalOut)
def mark_ai_proposal_applied(
    template_id: UUID,
    proposal_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateAiProposalOut:
    _load_template(template_id, db)
    proposal = (
        db.query(HtmlTemplateAiProposal)
        .filter(
            HtmlTemplateAiProposal.id == proposal_id,
            HtmlTemplateAiProposal.template_id == template_id,
        )
        .first()
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="AI proposal not found")
    if not proposal.is_applyable:
        raise HTTPException(status_code=400, detail="AI proposal is not applyable")
    proposal.applied_at = datetime.utcnow()
    db.commit()
    db.refresh(proposal)
    return proposal
```

## backend/app/services/template_ai_agent.py
```
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

    def provider_configuration_failed(self) -> TemplateAiProposalResult:
        return self._failed("Provider is not configured.")

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
            comment_start = html.find("{#", position)
            starts = [start for start in (expression_start, statement_start, comment_start) if start != -1]
            if not starts:
                break

            marker_start = min(starts)
            if marker_start == comment_start:
                comment_close = html.find("#}", marker_start + 2)
                if comment_close == -1:
                    break
                position = comment_close + 2
                continue

            marker_end = "}}" if marker_start == expression_start else "%}"
            marker_close = TemplateAiAgent._find_jinja_marker_close(html, marker_start + 2, marker_end)
            if marker_close is None:
                position = marker_start + 2
                continue

            marker = html[marker_start : marker_close + len(marker_end)]
            markers.append(marker)
            position = marker_close + len(marker_end)

            if marker_end == "%}" and TemplateAiAgent._is_jinja_block_marker(marker, "raw"):
                raw_end = TemplateAiAgent._find_jinja_raw_block_end(html, position)
                if raw_end is None:
                    break

                raw_end_start, raw_end_close = raw_end
                markers.append(html[raw_end_start : raw_end_close + 2])
                position = raw_end_close + 2

        return markers

    @staticmethod
    def _is_jinja_block_marker(marker: str, name: str) -> bool:
        content = marker[2:-2].strip()
        if content.startswith("-"):
            content = content[1:].lstrip()
        if content.endswith("-"):
            content = content[:-1].rstrip()
        return content == name

    @staticmethod
    def _find_jinja_raw_block_end(html: str, position: int) -> tuple[int, int] | None:
        while True:
            marker_start = html.find("{%", position)
            if marker_start == -1:
                return None

            marker_close = TemplateAiAgent._find_jinja_marker_close(html, marker_start + 2, "%}")
            if marker_close is None:
                return None

            marker = html[marker_start : marker_close + 2]
            if TemplateAiAgent._is_jinja_block_marker(marker, "endraw"):
                return marker_start, marker_close

            position = marker_close + 2

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
```

## backend/tests/test_ai_model_catalog.py
```
from types import SimpleNamespace

import pytest

from app.auth.session_service import create_session
from app.models.user import User
from app.services.ai_model_catalog import (
    AiModelOption,
    build_ai_model_catalog,
    is_provider_configured,
    resolve_ai_model,
)


@pytest.fixture
def user(db_session):
    value = User(sub="ai-model-catalog-test", email="ai-model-catalog@example.com")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


def make_settings(**overrides):
    values = {
        "ai_requests_enabled": True,
        "ai_default_model": "gemini/gemini-2.0-flash",
        "ai_provider_model": "gpt-4o-mini",
        "ai_allowed_models": "gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1",
        "gemini_api_key": "gemini-key",
        "groq_api_key": "",
        "ollama_api_base": "http://localhost:11434",
        "openai_api_key": "",
        "anthropic_api_key": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_get_ai_models_returns_catalog(client, monkeypatch, db_session, user):
    from app.api import ai_models

    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    monkeypatch.setattr(ai_models.settings, "ai_requests_enabled", True)
    monkeypatch.setattr(ai_models.settings, "ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr(ai_models.settings, "ai_provider_model", "gpt-4o-mini")
    monkeypatch.setattr(
        ai_models.settings,
        "ai_allowed_models",
        "gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1",
    )

    response = client.get("/api/content/ai-models")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["default_model"] == "gemini/gemini-2.0-flash"
    assert body["models"][0]["id"] == "gemini/gemini-2.0-flash"
    assert body["models"][0]["requires"] == "GEMINI_API_KEY"


def test_build_ai_model_catalog_parses_allowed_models():
    catalog = build_ai_model_catalog(make_settings())

    assert catalog.enabled is True
    assert catalog.default_model == "gemini/gemini-2.0-flash"
    assert [model.id for model in catalog.models] == [
        "gemini/gemini-2.0-flash",
        "groq/llama-3.1-8b-instant",
        "ollama/llama3.1",
    ]
    assert catalog.models[0].provider == "gemini"
    assert catalog.models[0].label == "Gemini 2.0 Flash"
    assert catalog.models[0].requires == "GEMINI_API_KEY"


def test_resolve_ai_model_uses_default_when_request_omits_model():
    option = resolve_ai_model(make_settings(), None)

    assert option.id == "gemini/gemini-2.0-flash"


def test_resolve_ai_model_rejects_non_allowlisted_model():
    with pytest.raises(ValueError, match="AI model is not allowed"):
        resolve_ai_model(make_settings(), "openai/gpt-5")


def test_empty_allowlist_is_configuration_error_for_resolution():
    with pytest.raises(ValueError, match="No AI models are configured"):
        resolve_ai_model(make_settings(ai_allowed_models=""), None)


def test_default_model_must_be_in_allowlist():
    with pytest.raises(ValueError, match="AI default model must be included"):
        build_ai_model_catalog(
            make_settings(
                ai_default_model="groq/llama-3.1-8b-instant",
                ai_allowed_models="gemini/gemini-2.0-flash",
            )
        )


def test_is_provider_configured_checks_openai_and_anthropic_keys():
    settings = make_settings(openai_api_key="openai-key", anthropic_api_key="anthropic-key")

    assert is_provider_configured(
        settings,
        AiModelOption("gpt-4o-mini", "openai", "GPT 4O Mini", "OPENAI_API_KEY"),
    ) is True
    assert is_provider_configured(
        settings,
        AiModelOption("anthropic/claude-3-5-sonnet", "anthropic", "Anthropic Claude", "ANTHROPIC_API_KEY"),
    ) is True


def test_is_provider_configured_rejects_missing_declared_provider_keys():
    settings = make_settings()

    assert is_provider_configured(
        settings,
        AiModelOption("gpt-4o-mini", "openai", "GPT 4O Mini", "OPENAI_API_KEY"),
    ) is False
    assert is_provider_configured(
        settings,
        AiModelOption("anthropic/claude-3-5-sonnet", "anthropic", "Anthropic Claude", "ANTHROPIC_API_KEY"),
    ) is False


def test_is_provider_configured_accepts_unknown_provider_without_required_config():
    assert is_provider_configured(
        make_settings(),
        AiModelOption("custom/model", "custom", "Custom Model", ""),
    ) is True
```

## backend/tests/test_template_ai_proposals.py
```
import uuid
from datetime import datetime
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers


# Keep collection independent of LiteLLM's Windows OpenSSL import path.
litellm_stub = ModuleType("litellm")
litellm_stub.completion = lambda **kwargs: None
sys.modules["litellm"] = litellm_stub

from app.services.template_ai_agent import TemplateAiAgent, TemplateAiProposalResult


@pytest.fixture
def user(db_session):
    value = User(sub="template-ai-test", email="template-ai@example.com")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


def _auth_client(client: TestClient, db_session: SQLAlchemySession, user: User) -> None:
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)


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


def test_template_ai_agent_blocks_jinja_marker_hidden_in_comment(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"{# {{ customer.name }} #}<p>removed</p>","css":"","summary":"Removed token."}'
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
    assert "Missing preserved Jinja marker: {{ customer.name }}" in result.validation_errors


def test_template_ai_agent_scanner_skips_jinja_markers_in_raw_blocks():
    markers = TemplateAiAgent._extract_jinja_markers(
        "{% raw %}<p>{{ customer.name }}</p>{% endraw %}{{ document.number }}"
    )

    assert markers == ["{% raw %}", "{% endraw %}", "{{ document.number }}"]


def create_template_fixture(db_session, user):
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
    db_session.add(template)
    db_session.commit()
    return template


def test_create_ai_proposal_persists_and_returns_applyable(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)

    def fake_create_proposal(self, **kwargs):
        return TemplateAiProposalResult(
            proposed_html="<section><p>{{ customer.name }}</p></section>",
            proposed_css="section { padding: 24px; }",
            summary="Improved spacing.",
            status="valid",
            validation_errors=[],
            is_applyable=True,
            provider="litellm",
            model="gpt-4o-mini",
        )

    monkeypatch.setattr("app.services.template_ai_agent.TemplateAiAgent.create_proposal", fake_create_proposal)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "gpt-4o-mini")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "gpt-4o-mini")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.openai_api_key", "key")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "mock_data": template.mock_data,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["template_id"] == str(template.id)
    assert body["proposed_html"] == "<section><p>{{ customer.name }}</p></section>"
    assert body["is_applyable"] is True
    assert body["status"] == "valid"


def test_create_ai_proposal_passes_selected_model(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    captured = {}

    def fake_create_proposal(self, **kwargs):
        captured["model"] = self.model
        return TemplateAiProposalResult(
            proposed_html="<section><p>{{ customer.name }}</p></section>",
            proposed_css="section { padding: 24px; }",
            summary="Improved spacing.",
            status="valid",
            validation_errors=[],
            is_applyable=True,
            provider="gemini",
            model=self.model,
        )

    monkeypatch.setattr("app.services.template_ai_agent.TemplateAiAgent.create_proposal", fake_create_proposal)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "gemini/gemini-2.0-flash")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.gemini_api_key", "key")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "mock_data": template.mock_data,
            "model": "gemini/gemini-2.0-flash",
        },
    )

    assert response.status_code == 201
    assert captured["model"] == "gemini/gemini-2.0-flash"
    assert response.json()["model"] == "gemini/gemini-2.0-flash"


def test_create_ai_proposal_rejects_disallowed_model(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "gemini/gemini-2.0-flash")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "gemini/gemini-2.0-flash")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "model": "groq/llama-3.1-8b-instant",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "AI model is not allowed."


def test_create_ai_proposal_returns_failed_when_provider_unconfigured(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_default_model", "groq/llama-3.1-8b-instant")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_allowed_models", "groq/llama-3.1-8b-instant")
    monkeypatch.setattr("app.api.template_ai_proposals.settings.groq_api_key", "")

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "model": "groq/llama-3.1-8b-instant",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["validation_errors"] == ["Provider is not configured."]
    assert body["is_applyable"] is False


def test_apply_ai_proposal_marks_applied_without_mutating_template(client, db_session, user):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Improved spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )
    db_session.add(proposal)
    db_session.commit()

    response = client.post(f"/api/content/templates/{template.id}/ai-proposals/{proposal.id}/apply")

    assert response.status_code == 200
    body = response.json()
    assert body["applied_at"] is not None
    db_session.refresh(template)
    assert template.html == "<p>{{ customer.name }}</p>"


def test_list_ai_proposals_returns_template_proposals(client, db_session, user):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Improved spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )
    db_session.add(proposal)
    db_session.commit()

    response = client.get(f"/api/content/templates/{template.id}/ai-proposals")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(proposal.id)
    assert body[0]["template_id"] == str(template.id)
```

## frontend/src/lib/content.ts
```
import { apiFetch, jsonOrError } from "./api";

export interface AiModelOption {
  id: string;
  provider: string;
  label: string;
  requires: string;
}

export interface AiModelCatalog {
  enabled: boolean;
  default_model: string;
  models: AiModelOption[];
}

export async function getAiModels(): Promise<AiModelCatalog> {
  return jsonOrError(await apiFetch("/api/content/ai-models"));
}

export interface HtmlTemplateListItem {
  id: string;
  name: string;
  document_type_id: string;
  document_type_name: string;
  token_count: number;
  created_by_email: string;
  created_at: string;
}

export interface HtmlTemplateDetail {
  id: string;
  name: string;
  document_type_id: string;
  document_type_name: string;
  html: string;
  css?: string | null;
  token_names: string[];
  mock_data?: Record<string, unknown> | null;
  created_by_email: string;
  created_at: string;
}

export interface HtmlTemplateCreatePayload {
  document_type_id: string;
  name: string;
  html: string;
  css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export interface StaticPdfAssetListItem {
  id: string;
  filename: string;
  page_count: number;
  document_type_id: string | null;
  document_type_name: string | null;
  created_by_email: string;
  created_at: string;
}

export interface StaticPdfAssetDetail {
  id: string;
  filename: string;
  stored_filename: string;
  stored_path: string;
  page_count: number;
  page_start: number | null;
  page_end: number | null;
  file_size: number;
  document_type_id: string | null;
  document_type_name: string | null;
  created_by_email: string;
  created_at: string;
  download_url: string;
}

export async function listHtmlTemplates(documentTypeId?: string): Promise<HtmlTemplateListItem[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/content/templates${query}`));
}

export async function getHtmlTemplate(id: string): Promise<HtmlTemplateDetail | null> {
  const res = await apiFetch(`/api/content/templates/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function createHtmlTemplate(
  payload: HtmlTemplateCreatePayload,
): Promise<HtmlTemplateDetail> {
  return jsonOrError(
    await apiFetch("/api/content/templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function updateHtmlTemplate(
  id: string,
  payload: HtmlTemplateCreatePayload,
): Promise<HtmlTemplateDetail> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export interface HtmlTemplatePreviewPayload {
  html: string;
  css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export interface HtmlTemplatePreviewResponse {
  rendered_html: string;
}

export async function previewHtmlTemplate(
  payload: HtmlTemplatePreviewPayload,
): Promise<HtmlTemplatePreviewResponse> {
  return jsonOrError(
    await apiFetch("/api/content/templates/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function listStaticPdfAssets(documentTypeId?: string): Promise<StaticPdfAssetListItem[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/content/static-pdfs${query}`));
}

export async function getStaticPdfAsset(id: string): Promise<StaticPdfAssetDetail | null> {
  const res = await apiFetch(`/api/content/static-pdfs/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function uploadStaticPdfAsset(
  file: File,
  pageStart: number | null,
  pageEnd: number | null,
): Promise<StaticPdfAssetDetail> {
  const formData = new FormData();
  formData.append("file", file);
  if (pageStart !== null) formData.append("page_start", String(pageStart));
  if (pageEnd !== null) formData.append("page_end", String(pageEnd));

  return jsonOrError(
    await apiFetch("/api/content/static-pdfs", {
      method: "POST",
      body: formData,
    }),
  );
}

export interface TemplateAiProposal {
  id: string;
  template_id: string;
  created_by_id: string;
  instruction: string;
  input_html: string;
  input_css: string;
  proposed_html: string;
  proposed_css: string;
  summary: string;
  provider: string;
  model: string;
  status: "valid" | "invalid" | "failed";
  validation_errors: string[];
  is_applyable: boolean;
  applied_at: string | null;
  created_at: string;
}

export interface TemplateAiProposalCreatePayload {
  instruction: string;
  current_html: string;
  current_css?: string | null;
  mock_data?: Record<string, unknown> | null;
  model?: string | null;
}

export async function createTemplateAiProposal(
  templateId: string,
  payload: TemplateAiProposalCreatePayload,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function listTemplateAiProposals(templateId: string): Promise<TemplateAiProposal[]> {
  return jsonOrError(await apiFetch(`/api/content/templates/${templateId}/ai-proposals`));
}

export async function markTemplateAiProposalApplied(
  templateId: string,
  proposalId: string,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals/${proposalId}/apply`, {
      method: "POST",
    }),
  );
}
```

## frontend/src/pages/content/components/AiProposalPanel.tsx
```
import { useEffect, useState } from "react";

import {
  createTemplateAiProposal,
  getAiModels,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type AiModelCatalog,
  type TemplateAiProposal,
} from "../../../lib/content";

interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  mockDataError: string | null;
  onCssChange: (value: string) => void;
  onMockDataJsonChange: (value: string) => void;
  onApply: (proposal: TemplateAiProposal) => void;
}

const selectedModelStorageKey = "docmanagement.aiImprove.selectedModel";

function parseMockData(mockDataJson: string): Record<string, unknown> | null {
  if (!mockDataJson.trim()) return null;
  const parsed = JSON.parse(mockDataJson);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Mock data must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

function formatAiError(error: unknown): string {
  const message = error instanceof Error ? error.message : "AI proposal failed.";
  if (message.includes("AI requests are disabled")) {
    return "AI Improve is disabled in this environment. Set AI_REQUESTS_ENABLED=true and configure a provider API key on the backend, then restart the service.";
  }
  return message;
}

export default function AiProposalPanel({
  templateId,
  html,
  css,
  mockDataJson,
  mockDataError,
  onCssChange,
  onMockDataJsonChange,
  onApply,
}: AiProposalPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [proposals, setProposals] = useState<TemplateAiProposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<TemplateAiProposal | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "html" | "css">("summary");
  const [panelTab, setPanelTab] = useState<"chat" | "settings">("chat");
  const [modelCatalog, setModelCatalog] = useState<AiModelCatalog | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelError, setModelError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProposals([]);
    setActiveProposal(null);
    setError(null);
    if (!templateId) return;
    let cancelled = false;
    listTemplateAiProposals(templateId)
      .then((rows) => {
        if (cancelled) return;
        setProposals(rows);
        setActiveProposal(rows[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load AI proposal history.");
      });
    return () => {
      cancelled = true;
    };
  }, [templateId]);

  useEffect(() => {
    let cancelled = false;
    getAiModels()
      .then((catalog) => {
        if (cancelled) return;
        setModelCatalog(catalog);
        const storedModel = localStorage.getItem(selectedModelStorageKey);
        const storedModelIsAllowed = catalog.models.some((model) => model.id === storedModel);
        const defaultModelIsAllowed = catalog.models.some((model) => model.id === catalog.default_model);
        const nextModel = storedModelIsAllowed
          ? storedModel!
          : defaultModelIsAllowed
            ? catalog.default_model
            : catalog.models[0]?.id ?? "";
        setSelectedModel(nextModel);
        if (nextModel) localStorage.setItem(selectedModelStorageKey, nextModel);
      })
      .catch((err) => {
        if (!cancelled) setModelError(err instanceof Error ? err.message : "We couldn't load AI models.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectModel = (model: string) => {
    setSelectedModel(model);
    localStorage.setItem(selectedModelStorageKey, model);
  };

  const requestProposal = async () => {
    if (!templateId || !instruction.trim()) return;
    if (mockDataError) {
      setError("Fix the mock preview data JSON before generating an AI proposal.");
      return;
    }
    if (!selectedModel) {
      setError("Select an AI model before generating a proposal.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
        model: selectedModel || null,
      });
      setProposals((current) => [proposal, ...current]);
      setActiveProposal(proposal);
      setActiveTab("summary");
    } catch (err) {
      setError(formatAiError(err));
    } finally {
      setLoading(false);
    }
  };

  const applyProposal = async () => {
    if (!templateId || !activeProposal || !activeProposal.is_applyable) return;
    setApplying(true);
    setError(null);
    try {
      const applied = await markTemplateAiProposalApplied(templateId, activeProposal.id);
      onApply(applied);
      setProposals((current) => current.map((proposal) => (proposal.id === applied.id ? applied : proposal)));
      setActiveProposal(applied);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Applying the AI proposal failed.");
    } finally {
      setApplying(false);
    }
  };

  return (
    <section className="flex h-full min-h-0 flex-col bg-white">
      <div className="flex border-b border-outline-variant bg-surface-container-low px-sm pt-sm">
        <button
          type="button"
          onClick={() => setPanelTab("chat")}
          className={`border-b-2 px-sm py-xs text-xs font-bold ${panelTab === "chat" ? "border-primary text-primary" : "border-transparent text-secondary"}`}
        >
          AI Chat
        </button>
        <button
          type="button"
          onClick={() => setPanelTab("settings")}
          className={`border-b-2 px-sm py-xs text-xs font-bold ${panelTab === "settings" ? "border-primary text-primary" : "border-transparent text-secondary"}`}
        >
          Settings
        </button>
      </div>

      {panelTab === "settings" ? (
        <div className="flex min-h-0 flex-1 flex-col gap-md overflow-y-auto p-sm">
          <label className="flex min-h-48 flex-1 flex-col gap-xs text-[11px] font-bold uppercase text-secondary">
            CSS Style
            <textarea
              value={css}
              onChange={(event) => onCssChange(event.target.value)}
              placeholder="/* Write custom CSS rules here */"
              className="min-h-40 flex-1 resize-none rounded border border-outline-variant bg-slate-900 p-sm font-mono text-xs normal-case text-slate-100 focus:border-primary focus:outline-none"
            />
          </label>
          <label className="flex min-h-48 flex-1 flex-col gap-xs text-[11px] font-bold uppercase text-secondary">
            Mock Preview Data
            <textarea
              value={mockDataJson}
              onChange={(event) => onMockDataJsonChange(event.target.value)}
              placeholder={'{\n  "cliente": {\n    "nombre": "Juan Perez"\n  }\n}'}
              className={`min-h-40 flex-1 resize-none rounded border bg-slate-900 p-sm font-mono text-xs normal-case text-slate-100 focus:outline-none ${mockDataError ? "border-error focus:border-error" : "border-outline-variant focus:border-primary"}`}
            />
            {mockDataError ? <span className="normal-case text-xs font-normal text-error">{mockDataError}</span> : null}
          </label>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-sm overflow-y-auto p-sm">
          <div className="flex items-center gap-xs">
            <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
            <h3 className="font-headings text-sm font-bold text-on-surface">AI Improve</h3>
          </div>

          {!templateId ? <p className="text-xs text-secondary">AI improvements are available after this template is created.</p> : null}

          <label className="text-[11px] font-bold uppercase text-secondary">
            Model
            <select
              value={selectedModel}
              onChange={(event) => selectModel(event.target.value)}
              disabled={!modelCatalog || modelCatalog.models.length === 0}
              className="mt-xs w-full rounded border border-outline-variant bg-white p-sm text-xs normal-case text-on-surface focus:border-primary focus:outline-none disabled:opacity-50"
            >
              <option value="">{modelCatalog ? "No AI models available" : "Loading AI models..."}</option>
              {modelCatalog?.models.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
          </label>
          {modelError ? <p className="text-xs text-error">{modelError}</p> : null}

          <textarea
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            rows={3}
            aria-label="AI improvement instruction"
            className="w-full rounded border border-outline-variant p-sm text-xs text-on-surface focus:border-primary focus:outline-none"
          />

          <button
            type="button"
            onClick={requestProposal}
            disabled={loading || !templateId || !instruction.trim() || !selectedModel || Boolean(mockDataError)}
            className="rounded bg-primary px-md py-xs text-xs font-bold text-white disabled:opacity-50"
          >
            {loading ? "Generating..." : "Suggest improvement"}
          </button>

          {error ? <p className="text-xs text-error">{error}</p> : null}

          {activeProposal ? (
        <div className="space-y-sm border-t border-outline-variant pt-sm">
          <div className="flex gap-xs">
            {(["summary", "html", "css"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded px-sm py-xs text-xs font-bold ${
                  activeTab === tab ? "bg-primary text-white" : "bg-surface-container text-secondary"
                }`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>

          {activeTab === "summary" ? (
            <div className="space-y-xs text-xs">
              <p className="text-on-surface">{activeProposal.summary || "No summary provided."}</p>
              {activeProposal.validation_errors.length ? (
                <ul className="list-disc pl-md text-error">
                  {activeProposal.validation_errors.map((validationError) => (
                    <li key={validationError}>{validationError}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <textarea
              readOnly
              value={activeTab === "html" ? activeProposal.proposed_html : activeProposal.proposed_css}
              rows={10}
              className="w-full rounded border border-outline-variant bg-slate-900 p-sm font-mono text-xs text-slate-100"
            />
          )}

          <button
            type="button"
            onClick={applyProposal}
            disabled={applying || !activeProposal.is_applyable}
            className="rounded border border-primary px-md py-xs text-xs font-bold text-primary disabled:border-outline-variant disabled:text-secondary"
          >
            {applying ? "Applying..." : "Apply proposal"}
          </button>
        </div>
          ) : null}

          {proposals.length ? (
        <div className="border-t border-outline-variant pt-sm">
          <h4 className="text-[11px] font-bold uppercase text-secondary">History</h4>
          <div className="mt-xs max-h-32 overflow-y-auto space-y-xs">
            {proposals.map((proposal) => (
              <button
                key={proposal.id}
                type="button"
                onClick={() => setActiveProposal(proposal)}
                className="block w-full rounded border border-outline-variant px-sm py-xs text-left text-xs hover:bg-surface-container"
              >
                <span className="font-bold">{proposal.status}</span> - {new Date(proposal.created_at).toLocaleString()}
              </button>
            ))}
          </div>
        </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
```

## frontend/src/pages/content/HtmlTemplateCreatePage.tsx
```
import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createHtmlTemplate,
  getHtmlTemplate,
  updateHtmlTemplate,
  previewHtmlTemplate,
  type TemplateAiProposal,
} from "../../lib/content";
import { getDocumentType, listDocumentTypes, type DocumentTypeDetail, type DocumentTypeListItem } from "../../lib/documentTypes";
import { buildSchemaFieldTree, type SchemaFieldTreeNode } from "../../lib/schemaFields";
import AiProposalPanel from "./components/AiProposalPanel";

function getDragTextForNode(node: SchemaFieldTreeNode, fields: any[]): string {
  if (node.type === "list") {
    const listPath = node.fullPath;
    const cleanPath = listPath.replace(/\[\]/g, "");
    const listVar = cleanPath.split(".").pop() || "item";
    const itemAlias = listVar.slice(0, -1) || "item";

    const childFields = fields.filter(f => f.name.startsWith(cleanPath + "."));
    const columns = childFields.map(f => {
      const relPath = f.name.slice((cleanPath + ".").length);
      return {
        header: relPath.split(".").pop() || relPath,
        expr: `{{ ${itemAlias}.${relPath} }}`
      };
    });

    if (columns.length === 0) {
      columns.push({ header: "Item", expr: `{{ ${itemAlias} }}` });
    }

    return `
<table>
  <thead>
    <tr>
      ${columns.map(c => `<th>${c.header}</th>`).join("\n      ")}
    </tr>
  </thead>
  <tbody>
    {% for ${itemAlias} in ${cleanPath} %}
    <tr>
      ${columns.map(c => `<td>${c.expr}</td>`).join("\n      ")}
    </tr>
    {% endfor %}
  </tbody>
</table>`;
  }

  const isInsideList = node.fullPath.includes("[]");
  if (isInsideList) {
    const parts = node.fullPath.split("[]");
    const listPart = parts[0];
    const subPart = parts[1];
    const listVar = listPart.split(".").pop() || "item";
    const itemAlias = listVar.slice(0, -1) || "item";
    const cleanSubPart = subPart.startsWith(".") ? subPart.slice(1) : subPart;

    return `{% for ${itemAlias} in ${listPart} %}{{ ${itemAlias}.${cleanSubPart} }}{% endfor %}`;
  }

  return `{{ ${node.fullPath} }}`;
}

export default function HtmlTemplateCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = !!id;

  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [html, setHtml] = useState("");
  const [htmlTouched, setHtmlTouched] = useState(false);
  const [css, setCss] = useState("");
  const [mockDataJson, setMockDataJson] = useState("");
  const [mockDataError, setMockDataError] = useState<string | null>(null);

  // Layout & Editing Modes
  const [editorMode, setEditorMode] = useState<"code" | "preview">("code");
  const [collapsedTokens, setCollapsedTokens] = useState<Set<string>>(new Set());
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    
    const init = async () => {
      try {
        const rows = await listDocumentTypes();
        if (cancelled) return;
        setDocumentTypes(rows);

        if (isEditMode && id) {
          const t = await getHtmlTemplate(id);
          if (cancelled) return;
          if (t) {
            setName(t.name);
            setDocumentTypeId(t.document_type_id);
            setHtml(t.html);
            setHtmlTouched(true);
            if (t.css) {
              setCss(t.css);
            }
            if (t.mock_data) {
              setMockDataJson(JSON.stringify(t.mock_data, null, 2));
            }
          }
        } else {
          setDocumentTypeId(rows[0]?.id ?? "");
        }
      } catch (err) {
        console.error("Failed to load template/document types", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    init();

    return () => {
      cancelled = true;
    };
  }, [id, isEditMode]);

  useEffect(() => {
    if (!documentTypeId) {
      setSelectedDocumentType(null);
      return;
    }

    let cancelled = false;
    getDocumentType(documentTypeId).then((detail) => {
      if (cancelled) return;
      if (detail) {
        setSelectedDocumentType(detail);

        // Default HTML structure based on Document Type fields
        if (!htmlTouched && !isEditMode) {
          const defaultHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${name || "Template"}</title>
</head>
<body>
  <div class="template-container">
    <h1>${name || "DOCUMENT"}</h1>
    <p>Asociado a: ${detail.name}</p>
    <hr/>
    <!-- Drag and drop tokens here -->
  </div>
</body>
</html>`;
          setHtml(defaultHtml);
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, [documentTypeId, htmlTouched, isEditMode, name]);

  const handleSetEditorMode = (mode: "code" | "preview") => {
    setEditorMode(mode);
  };

  const handleApplyAiProposal = (proposal: TemplateAiProposal) => {
    setHtml(proposal.proposed_html);
    setCss(proposal.proposed_css);
    setHtmlTouched(true);
  };

  useEffect(() => {
    if (editorMode !== "preview") return;

    let cancelled = false;
    const fetchPreview = async () => {
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        let parsedMock: Record<string, unknown> | null = null;
        if (mockDataJson.trim()) {
          try {
            parsedMock = JSON.parse(mockDataJson);
          } catch {
            throw new Error("Invalid Mock Data JSON structure.");
          }
        }
        const resp = await previewHtmlTemplate({
          html,
          css,
          mock_data: parsedMock,
        });
        if (cancelled) return;
        setPreviewHtml(resp.rendered_html);
      } catch (err) {
        if (cancelled) return;
        setPreviewError(err instanceof Error ? err.message : "Failed to load preview.");
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    };

    const delayDebounceFn = setTimeout(() => {
      fetchPreview();
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(delayDebounceFn);
    };
  }, [editorMode, html, css, mockDataJson]);

  const srcDocContent = useMemo(() => {
    const cleanHtml = previewHtml || "";
    const styleTag = `<style>${css || ""}</style>`;
    if (cleanHtml.includes("<head>")) {
      return cleanHtml.replace("<head>", `<head>${styleTag}`);
    } else if (cleanHtml.includes("<HEAD>")) {
      return cleanHtml.replace("<HEAD>", `<HEAD>${styleTag}`);
    } else {
      return `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            ${styleTag}
          </head>
          <body>
            ${cleanHtml}
          </body>
        </html>
      `;
    }
  }, [previewHtml, css]);

  const handleTextareaDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    const token = e.dataTransfer.getData("text/plain");
    if (!token) return;

    const textarea = e.currentTarget;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const nextHtml = text.substring(0, start) + token + text.substring(end);

    setHtml(nextHtml);
    setHtmlTouched(true);
  };

  const handleSubmitForm = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!name.trim()) {
      setSubmitError("Template name is required.");
      return;
    }
    if (!documentTypeId) {
      setSubmitError("Choose a document type.");
      return;
    }

    let parsedMock: Record<string, unknown> | null = null;
    if (mockDataJson.trim()) {
      try {
        parsedMock = JSON.parse(mockDataJson);
        if (typeof parsedMock !== "object" || parsedMock === null || Array.isArray(parsedMock)) {
          setSubmitError("Mock Data JSON must be a valid JSON object.");
          return;
        }
      } catch (err) {
        setSubmitError(`Mock Data JSON has syntax errors: ${err instanceof Error ? err.message : "Error"}`);
        return;
      }
    }

    try {
      if (isEditMode && id) {
        await updateHtmlTemplate(id, {
          document_type_id: documentTypeId,
          name,
          html,
          css,
          mock_data: parsedMock,
        });
        navigate("/content/templates");
      } else {
        await createHtmlTemplate({
          document_type_id: documentTypeId,
          name,
          html,
          css,
          mock_data: parsedMock,
        });
        navigate("/content/templates");
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We couldn't save this template.");
    }
  };

  const toggleTokenNode = (nodeId: string) => {
    setCollapsedTokens((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const tokenTree = useMemo(() => {
    if (!selectedDocumentType?.fields) return [];
    return buildSchemaFieldTree(selectedDocumentType.fields);
  }, [selectedDocumentType]);

  const renderTokenNode = (node: SchemaFieldTreeNode) => {
    const isLeaf = node.type === "leaf";
    const isCollapsed = collapsedTokens.has(node.id);

    return (
      <div key={node.id} className="select-none mt-xs">
        <div
          draggable
          onDragStart={(e) => {
            if (selectedDocumentType) {
              const text = getDragTextForNode(node, selectedDocumentType.fields);
              e.dataTransfer.setData("text/plain", text);
            }
          }}
          className={`flex items-center gap-xs py-xs px-sm rounded cursor-grab hover:bg-surface-container-high transition-colors group border border-transparent active:border-primary/30 ${
            isLeaf ? "text-on-surface" : "font-bold text-secondary"
          }`}
        >
          {!isLeaf ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggleTokenNode(node.id);
              }}
              className="material-symbols-outlined text-secondary hover:text-primary transition-colors text-[18px] focus:outline-none"
            >
              {isCollapsed ? "chevron_right" : "expand_more"}
            </button>
          ) : (
            <div className="w-[18px]"></div>
          )}

          <span className="material-symbols-outlined text-[18px] text-outline">
            {node.type === "list"
              ? "list"
              : node.type === "object"
              ? (isCollapsed ? "folder" : "folder_open")
              : "description"}
          </span>
          <span className="text-body-sm font-semibold">{node.name}</span>
        </div>

        {!isLeaf && !isCollapsed && node.children && (
          <div className="pl-md border-l border-outline-variant ml-sm space-y-xs">
            {node.children.map(renderTokenNode)}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden -m-lg">
      {/* Top action header bar */}
      <div className="h-14 flex items-center px-lg bg-surface-container-lowest border-b border-outline-variant shrink-0 justify-between">
        <div className="flex items-center gap-md">
          <h1 className="font-headings text-[20px] font-bold tracking-tight text-on-surface">
            {isEditMode ? "Edit HTML Template" : "New HTML Template"}
          </h1>
        </div>
        <div className="flex items-center gap-sm">
          <Link
            to="/content/templates"
            className="rounded border border-outline-variant bg-surface-container px-md py-xs text-xs font-bold text-secondary hover:bg-surface-container-high transition-all"
          >
            Cancel
          </Link>
          <button
            onClick={handleSubmitForm}
            type="button"
            className="rounded bg-primary px-md py-xs text-xs font-bold text-white hover:bg-primary/90 transition-all shadow-sm"
          >
            {isEditMode ? "Save Changes" : "Create Template"}
          </button>
        </div>
      </div>

      {/* Main Workspace (3 Panels) */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden min-h-0 bg-surface-container-low">
        {/* PANEL 1: Left Panel - Metadata & Tokens */}
        <aside className="col-span-3 border-r border-outline-variant bg-surface flex flex-col overflow-hidden h-full">
          <div className="p-md space-y-md border-b border-outline-variant shrink-0 bg-white">
            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Template Name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                placeholder="e.g. Booking Confirmation"
                className="mt-xs w-full rounded border border-outline-variant px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white font-semibold"
              />
            </label>

            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Associated Document Type
              <select
                value={documentTypeId}
                onChange={(event) => {
                  setDocumentTypeId(event.target.value);
                  setHtmlTouched(false);
                }}
                className="mt-xs w-full rounded border border-outline-variant px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white font-semibold"
              >
                {loading ? <option>Loading...</option> : null}
                {!loading && documentTypes.length === 0 ? <option value="">No document types available</option> : null}
                {documentTypes.map((documentType) => (
                  <option key={documentType.id} value={documentType.id}>
                    {documentType.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Token Explorer title */}
          <div className="p-md bg-surface-container-low flex items-center justify-between shrink-0">
            <h3 className="font-headings text-sm font-bold text-on-surface flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-[20px]">explore</span>
              EXPLORADOR DE TOKENS
            </h3>
          </div>

          {/* Token Explorer Tree (Scrollable) */}
          <div className="flex-1 overflow-y-auto p-md">
            {!selectedDocumentType?.fields?.length ? (
              <div className="text-center py-lg border border-dashed border-outline-variant rounded bg-surface p-sm">
                <p className="text-xs text-secondary">
                  Select a document type above to explore available tokens.
                </p>
              </div>
            ) : (
              <div className="space-y-xs pr-xs">
                {tokenTree.map(renderTokenNode)}
              </div>
            )}
          </div>

          <div className="p-md bg-primary-container/10 border-t border-outline-variant shrink-0">
            <p className="text-[10px] leading-tight text-on-surface-variant italic">
              Tip: Drag tokens directly into the editor to generate dynamic syntax automatically.
            </p>
          </div>
        </aside>

        {/* PANEL 2: Central Panel - Workspace (Canvas & Tabs) */}
        <section className="col-span-6 flex flex-col bg-surface-container-low overflow-hidden h-full">
          <div className="h-12 flex items-center px-md bg-white border-b border-outline-variant shadow-sm z-10 shrink-0">
            <div className="flex bg-surface-container rounded p-[2px]">
              <button
                type="button"
                className={`px-md py-1 font-bold text-xs rounded transition-all flex items-center gap-xs ${
                  editorMode === "code"
                    ? "bg-white text-primary shadow-sm"
                    : "text-secondary hover:text-primary"
                }`}
                onClick={() => handleSetEditorMode("code")}
              >
                <span className="material-symbols-outlined text-[16px]">code</span>
                Source
              </button>
              <button
                type="button"
                className={`px-md py-1 font-bold text-xs rounded transition-all flex items-center gap-xs ${
                  editorMode === "preview"
                    ? "bg-white text-primary shadow-sm"
                    : "text-secondary hover:text-primary"
                }`}
                onClick={() => handleSetEditorMode("preview")}
              >
                <span className="material-symbols-outlined text-[16px]">pageview</span>
                Preview
              </button>
            </div>
            {submitError && (
              <span className="ml-md text-xs text-error font-medium truncate max-w-[250px]">
                {submitError}
              </span>
            )}
          </div>

          {/* Canvas Container (Scrollable) */}
          <div className="flex-1 p-md overflow-y-auto flex flex-col items-center">
            {editorMode === "code" && (
              <div className="w-full max-w-[800px] border border-outline-variant rounded-lg overflow-hidden flex bg-white shadow-md">
                {/* Line numbers dummy sidebar */}
                <div className="w-12 bg-surface-container-low border-r border-outline-variant py-sm text-right pr-sm select-none font-mono text-[11px] text-outline text-height-relaxed">
                  {Array.from({ length: Math.max(25, html.split("\n").length) }).map((_, i) => (
                    <div key={i}>{i + 1}</div>
                  ))}
                </div>
                <textarea
                  value={html}
                  onChange={(event) => {
                    setHtml(event.target.value);
                    setHtmlTouched(true);
                  }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleTextareaDrop}
                  rows={28}
                  placeholder="<!-- Write your HTML template code directly here. Drag and drop tokens. -->"
                  className="flex-1 w-full bg-slate-900 text-slate-100 p-sm font-mono text-sm leading-relaxed focus:outline-none resize-none min-h-[600px]"
                />
              </div>
            )}



            {editorMode === "preview" && (
              <div className="w-full max-w-[800px] bg-white min-h-[1056px] shadow-lg rounded border border-outline-variant flex flex-col relative overflow-hidden">
                {previewLoading && (
                  <div className="absolute inset-0 bg-white/75 flex items-center justify-center z-25">
                    <span className="material-symbols-outlined animate-spin text-primary text-[32px]">progress_activity</span>
                  </div>
                )}
                {previewError ? (
                  <div className="p-xl flex-1 flex flex-col items-center justify-center text-center gap-md text-error bg-error-container/10">
                    <span className="material-symbols-outlined text-[48px]">error_outline</span>
                    <div>
                      <h3 className="font-bold text-on-surface">Preview Rendering Failed</h3>
                      <p className="text-xs text-secondary mt-xs max-w-md font-mono">{previewError}</p>
                    </div>
                  </div>
                ) : (
                  <iframe
                    title="Jinja Template Preview"
                    className="w-full flex-1 min-h-[600px] border-0"
                    srcDoc={srcDocContent}
                  />
                )}
              </div>
            )}
          </div>
        </section>

        {/* PANEL 3: AI chat and template settings */}
        <section className="col-span-3 border-l border-outline-variant flex flex-col bg-surface overflow-hidden h-full">
          <AiProposalPanel
            templateId={isEditMode && id ? id : null}
            html={html}
            css={css}
            mockDataJson={mockDataJson}
            mockDataError={mockDataError}
            onCssChange={setCss}
            onMockDataJsonChange={(value) => {
              setMockDataJson(value);
              try {
                if (value.trim()) JSON.parse(value);
                setMockDataError(null);
              } catch (err) {
                setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
              }
            }}
            onApply={handleApplyAiProposal}
          />
        </section>
      </div>
    </div>
  );
}
```

## .env.example
```
OIDC_ISSUER=http://localhost:8080/realms/docmanagement
OIDC_ISSUER_ALIASES=
OIDC_JWKS_URL=
OIDC_CLIENT_ID=docmanagement-backend
OIDC_CLIENT_SECRET=<set-local-backend-client-secret>
OIDC_API_AUDIENCE=docmanagement-backend
POSTGRES_USER=docmanagement
POSTGRES_PASSWORD=<set-local-postgres-password>
POSTGRES_DB=docmanagement
DATABASE_URL=postgresql+psycopg://docmanagement:<set-local-postgres-password>@localhost:5432/docmanagement
TEST_DATABASE_URL=postgresql+psycopg://docmanagement:<set-local-postgres-password>@localhost:5432/docmanagement_test
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=<set-local-keycloak-admin-password>
KEYCLOAK_BACKEND_CLIENT_SECRET=<set-local-backend-client-secret>
KEYCLOAK_API_CLIENT_SECRET=<set-local-api-client-secret>
KEYCLOAK_ALICE_PASSWORD=<set-local-alice-password>
KEYCLOAK_BOB_PASSWORD=<set-local-bob-password>
SESSION_SECRET=<set-local-random-session-secret>
SESSION_COOKIE_NAME=bff_session
SESSION_TTL_SECONDS=604800
FRONTEND_ORIGIN=http://localhost:5173
BACKEND_URL=http://localhost:8001

# Storage Decoupling Configuration
STORAGE_PROVIDER_TYPE=local  # 'local' or 's3'
STORAGE_S3_ENDPOINT_URL=http://localhost:9000
STORAGE_S3_ACCESS_KEY=admin
STORAGE_S3_SECRET_KEY=password123
STORAGE_S3_REGION=us-east-1
STORAGE_S3_BUCKET_STATIC_PDFS=docmanagement-static-pdfs
STORAGE_S3_BUCKET_ISSUANCES=docmanagement-issuances

MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=password123

# Celery/Redis Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# AI Improve is disabled by default. To enable it, set AI_REQUESTS_ENABLED=true,
# configure a provider API key below, and restart/recreate the backend service
# when running through Docker Compose.
AI_REQUESTS_ENABLED=false
AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
AI_PROVIDER_MODEL=gpt-4o-mini
AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_INPUT_CHARS=20000
AI_MAX_OUTPUT_TOKENS=2000
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# GEMINI_API_KEY=
# GROQ_API_KEY=
# OLLAMA_API_BASE=http://host.docker.internal:11434
```

## docker-compose.yml
```
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER:?POSTGRES_USER is required}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      POSTGRES_DB: ${POSTGRES_DB:?POSTGRES_DB is required}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - ./postgres/init:/docker-entrypoint-initdb.d:ro
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U docmanagement -d docmanagement"]
      interval: 5s
      timeout: 5s
      retries: 20

  keycloak:
    image: quay.io/keycloak/keycloak:26.6
    command: start-dev --import-realm
    environment:
      KC_BOOTSTRAP_ADMIN_USERNAME: ${KEYCLOAK_ADMIN_USERNAME:?KEYCLOAK_ADMIN_USERNAME is required}
      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:?KEYCLOAK_ADMIN_PASSWORD is required}
      KEYCLOAK_BACKEND_CLIENT_SECRET: ${KEYCLOAK_BACKEND_CLIENT_SECRET:?KEYCLOAK_BACKEND_CLIENT_SECRET is required}
      KEYCLOAK_API_CLIENT_SECRET: ${KEYCLOAK_API_CLIENT_SECRET:?KEYCLOAK_API_CLIENT_SECRET is required}
      KEYCLOAK_ALICE_PASSWORD: ${KEYCLOAK_ALICE_PASSWORD:?KEYCLOAK_ALICE_PASSWORD is required}
      KEYCLOAK_BOB_PASSWORD: ${KEYCLOAK_BOB_PASSWORD:?KEYCLOAK_BOB_PASSWORD is required}
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./keycloak/import:/opt/keycloak/data/import:ro
      - keycloak-data:/opt/keycloak/data
    depends_on:
      postgres:
        condition: service_healthy

  backend:
    build:
      context: ./backend
    environment:
      OIDC_ISSUER: http://localhost:8080/realms/docmanagement
      OIDC_ISSUER_ALIASES: http://keycloak:8080/realms/docmanagement
      OIDC_JWKS_URL: http://keycloak:8080/realms/docmanagement/protocol/openid-connect/certs
      OIDC_API_AUDIENCE: docmanagement-backend
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:?POSTGRES_USER is required}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@postgres:5432/${POSTGRES_DB:?POSTGRES_DB is required}
      TEST_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:?POSTGRES_USER is required}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@postgres:5432/docmanagement_test
      FRONTEND_ORIGIN: http://localhost:5173
      CONTENT_STORAGE_ROOT: /app/.content-storage
      STORAGE_PROVIDER_TYPE: ${STORAGE_PROVIDER_TYPE:-local}
      STORAGE_S3_ENDPOINT_URL: http://minio:9000
      STORAGE_S3_ACCESS_KEY: ${MINIO_ROOT_USER:-admin}
      STORAGE_S3_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-password123}
      STORAGE_S3_REGION: us-east-1
      STORAGE_S3_BUCKET_STATIC_PDFS: docmanagement-static-pdfs
      STORAGE_S3_BUCKET_ISSUANCES: docmanagement-issuances
      AI_REQUESTS_ENABLED: ${AI_REQUESTS_ENABLED:-false}
      AI_DEFAULT_MODEL: ${AI_DEFAULT_MODEL:-gemini/gemini-2.0-flash}
      AI_PROVIDER_MODEL: ${AI_PROVIDER_MODEL:-gpt-4o-mini}
      AI_ALLOWED_MODELS: ${AI_ALLOWED_MODELS:-gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1}
      AI_REQUEST_TIMEOUT_SECONDS: ${AI_REQUEST_TIMEOUT_SECONDS:-30}
      AI_MAX_INPUT_CHARS: ${AI_MAX_INPUT_CHARS:-20000}
      AI_MAX_OUTPUT_TOKENS: ${AI_MAX_OUTPUT_TOKENS:-2000}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      GROQ_API_KEY: ${GROQ_API_KEY:-}
      OLLAMA_API_BASE: ${OLLAMA_API_BASE:-http://host.docker.internal:11434}
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    ports:
      - "127.0.0.1:8001:8000"
    volumes:
      - content-storage:/app/.content-storage
    depends_on:
      postgres:
        condition: service_healthy
      keycloak:
        condition: service_started
      redis:
        condition: service_started

  bff:
    build:
      context: ./bff
    environment:
      OIDC_ISSUER: http://keycloak:8080/realms/docmanagement
      OIDC_CLIENT_ID: docmanagement-backend
      OIDC_CLIENT_SECRET: ${KEYCLOAK_BACKEND_CLIENT_SECRET:?KEYCLOAK_BACKEND_CLIENT_SECRET is required}
      SESSION_SECRET: ${SESSION_SECRET:?SESSION_SECRET is required}
      SESSION_COOKIE_NAME: bff_session
      SESSION_TTL_SECONDS: 604800
      SESSION_COOKIE_SECURE: "False"
      BACKEND_URL: http://backend:8000
      FRONTEND_ORIGIN: http://localhost:5173
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      backend:
        condition: service_started
      keycloak:
        condition: service_started

  frontend:
    build:
      context: ./frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000
    ports:
      - "127.0.0.1:5173:5173"
    depends_on:
      bff:
        condition: service_started

  minio:
    image: minio/minio:RELEASE.2024-01-28T22-35-53Z
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-admin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-password123}
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
    volumes:
      - minio-data:/data

  redis:
    image: redis:7-alpine
    ports:
      - "127.0.0.1:6379:6379"

  worker:
    build:
      context: ./backend
    command: uv run celery -A app.workers.celery_app worker --loglevel=info
    environment:
      OIDC_ISSUER: http://localhost:8080/realms/docmanagement
      OIDC_ISSUER_ALIASES: http://keycloak:8080/realms/docmanagement
      OIDC_JWKS_URL: http://keycloak:8080/realms/docmanagement/protocol/openid-connect/certs
      OIDC_API_AUDIENCE: docmanagement-backend
      FRONTEND_ORIGIN: http://localhost:5173
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:?POSTGRES_USER is required}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@postgres:5432/${POSTGRES_DB:?POSTGRES_DB is required}
      TEST_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:?POSTGRES_USER is required}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@postgres:5432/docmanagement_test
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      CONTENT_STORAGE_ROOT: /app/.content-storage
      STORAGE_PROVIDER_TYPE: ${STORAGE_PROVIDER_TYPE:-local}
      STORAGE_S3_ENDPOINT_URL: http://minio:9000
      STORAGE_S3_ACCESS_KEY: ${MINIO_ROOT_USER:-admin}
      STORAGE_S3_SECRET_KEY: ${MINIO_ROOT_PASSWORD:-password123}
      STORAGE_S3_REGION: us-east-1
      STORAGE_S3_BUCKET_STATIC_PDFS: docmanagement-static-pdfs
      STORAGE_S3_BUCKET_ISSUANCES: docmanagement-issuances
    volumes:
      - content-storage:/app/.content-storage
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  pgdata:
  keycloak-data:
  content-storage:
  minio-data:
```
