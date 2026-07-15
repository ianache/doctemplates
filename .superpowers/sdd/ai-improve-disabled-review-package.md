# AI Improve Disabled Review Package

## User-reported symptom
When using AI Improve in the web UI, the user receives: AI requests are disabled.

## Relevant status
MM .env.example
D  backend/app/api/template_ai_proposals.py
MM backend/app/config.py
D  backend/app/services/template_ai_agent.py
MM frontend/src/lib/content.ts
MM frontend/src/pages/content/HtmlTemplateCreatePage.tsx
D  frontend/src/pages/content/components/AiProposalPanel.tsx
?? backend/app/api/template_ai_proposals.py
?? backend/app/services/template_ai_agent.py
?? frontend/src/pages/content/components/AiProposalPanel.tsx

## File: .env.example
`
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

AI_REQUESTS_ENABLED=false
AI_PROVIDER_MODEL=gpt-4o-mini
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_INPUT_CHARS=20000
AI_MAX_OUTPUT_TOKENS=2000
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
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
`

## File: backend/app/api/template_ai_proposals.py
`
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

    template = _load_template(template_id, db)
    agent = TemplateAiAgent(
        model=settings.ai_provider_model,
        enabled=settings.ai_requests_enabled,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_input_chars=settings.ai_max_input_chars,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    result = agent.create_proposal(
        instruction=payload.instruction,
        current_html=payload.current_html,
        current_css=payload.current_css or "",
        document_fields=[field.name for field in template.document_type.fields],
        mock_data=payload.mock_data or template.mock_data or {},
    )
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
`

## File: frontend/src/pages/content/components/AiProposalPanel.tsx
`
import { useEffect, useState } from "react";

import {
  createTemplateAiProposal,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type TemplateAiProposal,
} from "../../../lib/content";

interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  onApply: (proposal: TemplateAiProposal) => void;
}

function parseMockData(mockDataJson: string): Record<string, unknown> | null {
  if (!mockDataJson.trim()) return null;
  const parsed = JSON.parse(mockDataJson);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Mock data must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

export default function AiProposalPanel({ templateId, html, css, mockDataJson, onApply }: AiProposalPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [proposals, setProposals] = useState<TemplateAiProposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<TemplateAiProposal | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "html" | "css">("summary");
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

  const requestProposal = async () => {
    if (!templateId || !instruction.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
      });
      setProposals((current) => [proposal, ...current]);
      setActiveProposal(proposal);
      setActiveTab("summary");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI proposal failed.");
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

  if (!templateId) {
    return (
      <div className="rounded border border-outline-variant bg-surface-container-low p-sm text-xs text-secondary">
        AI improvements are available after this template is created.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-sm rounded border border-outline-variant bg-white p-sm">
      <div className="flex items-center gap-xs">
        <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
        <h3 className="font-headings text-sm font-bold text-on-surface">AI Improve</h3>
      </div>

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
        disabled={loading || !instruction.trim()}
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
    </section>
  );
}
`

## File: frontend/src/pages/content/HtmlTemplateCreatePage.tsx
`
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

        {/* PANEL 3: Right Panel - Styles & Preview Data */}
        <section className="col-span-3 border-l border-outline-variant flex flex-col bg-surface overflow-hidden h-full">
          <div className="h-1/3 overflow-y-auto border-b border-outline-variant p-sm bg-surface">
            <AiProposalPanel
              templateId={isEditMode && id ? id : null}
              html={html}
              css={css}
              mockDataJson={mockDataJson}
              onApply={handleApplyAiProposal}
            />
          </div>

          {/* CSS Styles Section */}
          <div className="h-1/3 flex flex-col border-b border-outline-variant overflow-hidden">
            <div className="p-md bg-surface-container-low flex items-center justify-between shrink-0">
              <div className="flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">css</span>
                <h3 className="font-headings text-sm font-bold text-on-surface">CSS Styles</h3>
              </div>
            </div>
            <div className="flex-1 p-sm bg-white overflow-hidden flex flex-col">
              <textarea
                value={css}
                onChange={(e) => setCss(e.target.value)}
                placeholder={`/* Write custom CSS rules here */\n.title {\n  color: #1a73e8;\n  font-size: 24px;\n}`}
                className="flex-1 w-full rounded border border-outline-variant p-sm font-mono text-xs text-on-surface focus:border-primary focus:outline-none bg-slate-900 text-slate-100 resize-none"
              />
            </div>
          </div>

          {/* Mock Data Section */}
          <div className="h-1/3 flex flex-col overflow-hidden">
            <div className="p-md bg-surface-container-low flex items-center justify-between shrink-0">
              <div className="flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">data_object</span>
                <h3 className="font-headings text-sm font-bold text-on-surface">Mock Preview Data</h3>
              </div>
              {mockDataError && (
                <span className="text-[10px] text-error font-mono truncate max-w-[120px]" title={mockDataError}>
                  Error
                </span>
              )}
            </div>
            <div className="flex-1 p-sm bg-white overflow-hidden flex flex-col">
              <textarea
                value={mockDataJson}
                onChange={(e) => {
                  setMockDataJson(e.target.value);
                  try {
                    if (e.target.value.trim()) {
                      JSON.parse(e.target.value);
                      setMockDataError(null);
                    } else {
                      setMockDataError(null);
                    }
                  } catch (err) {
                    setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
                  }
                }}
                placeholder={`{\n  "cliente": {\n    "nombre": "Juan Pérez"\n  }\n}`}
                className={`flex-1 w-full rounded border font-mono text-xs p-sm bg-slate-900 text-slate-100 focus:outline-none resize-none ${
                  mockDataError ? "border-error focus:border-error" : "border-outline-variant focus:border-primary"
                }`}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
`

## File: frontend/src/lib/content.ts
`
import { apiFetch, jsonOrError } from "./api";

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
`

## File: docs/superpowers/specs/2026-07-15-ai-template-agent-design.md
`
# AI Template Agent Design

Date: 2026-07-15
Phase: 16 - AI agent for page templating
Status: Design approved for user review

## Goal

Add an AI-assisted improvement workflow for existing HTML content templates. The first version helps template editors improve layout, print styling, and visual structure for an existing template while preserving its current Jinja tokens and meaning.

The feature is proposal-first: the AI never mutates the template directly. It returns a reviewable HTML/CSS proposal, strict backend validation decides whether the proposal can be applied, and the user must explicitly apply and then save the template.

## Non-Goals

- Generating a brand-new template from an empty prompt.
- Chat-style multi-turn template editing.
- Adding admin or auditor roles.
- Automatically saving AI output to the template.
- Moving AI work into asynchronous jobs in the first version.
- Allowing AI to add, remove, or reinterpret business tokens.

## Recommended Approach

Use a proposal-first backend agent.

The backend owns this feature because it already owns template persistence, document type schemas, Jinja validation, preview rendering, PDF rendering, and authentication. The frontend remains a review and apply surface. The BFF remains a session-aware proxy and should not contain custom AI orchestration.

The implementation should keep the AI call synchronous for Phase 16, but isolate it behind a service boundary so a later phase can move proposal creation to an async job without changing the proposal table or editor contract.

## Architecture

Add a backend proposal layer around existing HTML template editing.

New backend pieces:

- `HtmlTemplateAiProposal` SQLAlchemy model and Alembic migration.
- Pydantic schemas for proposal create, list, detail, validation, and apply responses.
- Routes under the existing content-template API namespace:
  - `POST /api/content/templates/{template_id}/ai-proposals`
  - `GET /api/content/templates/{template_id}/ai-proposals`
  - `POST /api/content/templates/{template_id}/ai-proposals/{proposal_id}/apply`
- `TemplateAiAgent` service that builds prompts, calls LiteLLM, parses output, validates output, and persists proposals.
- Backend config fields:
  - `ai_requests_enabled`
  - `ai_provider_model`
  - `ai_request_timeout_seconds`
  - `ai_max_input_chars`
  - `ai_max_output_tokens`

Provider API keys should use LiteLLM-supported environment variables such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Do not store provider secrets in the database.

Frontend additions:

- API helpers in the content client module.
- An AI improvement panel in the existing HTML template edit workspace.
- Proposal history and review UI.
- Apply behavior that updates local editor fields but does not save the template automatically.

## Data Model

`HtmlTemplateAiProposal` should be linked to `html_templates` and users.

Required fields:

- `id`
- `template_id`
- `created_by_id`
- `instruction`
- `input_html`
- `input_css`
- `proposed_html`
- `proposed_css`
- `summary`
- `provider`
- `model`
- `status`
- `validation_errors`
- `is_applyable`
- `applied_at`
- `created_at`

Recommended status values:

- `valid`
- `invalid`
- `failed`

Persist full proposal history, including invalid proposals, so template editors can understand what was suggested, why it failed, and which proposals were applied. In Phase 16, history is visible to users who can edit the template. Admin and auditor visibility is deferred until explicit roles exist.

## Data Flow

1. User opens an existing HTML template edit page.
2. Frontend loads template detail through the current content API.
3. User opens the AI improvement panel and enters an instruction such as "make this page look more formal and print-friendly".
4. Frontend calls `POST /api/content/templates/{template_id}/ai-proposals` with the instruction and the current unsaved `html` and `css` values.
5. Backend loads the persisted template and document type fields.
6. Backend sends LiteLLM a constrained JSON-only prompt containing:
   - user instruction
   - current HTML
   - current CSS
   - document type field names and types
   - existing extracted Jinja tokens and statements
   - output contract
7. Backend expects JSON with `html`, `css`, and `summary`.
8. Backend validates the result strictly.
9. Backend persists the full proposal and validation result.
10. Frontend shows the proposal and history.
11. Valid proposals show an Apply action. Invalid proposals show validation errors and cannot be applied.
12. On Apply, frontend replaces local editor `html` and `css` values and calls the apply endpoint to mark the proposal applied.
13. User uses the existing Save Changes action to persist the edited template.

## Validation and Safety

A proposal is applyable only if all gates pass:

- Model response is valid JSON with `html`, `css`, and `summary`.
- Generated HTML parses as Jinja using the existing sandboxed environment.
- Generated tokens are valid for the selected document type.
- Every existing Jinja expression and statement from the current input HTML is still present in the generated HTML.
- Preview rendering succeeds using current editor mock data when supplied, otherwise the stored template mock data.
- HTML does not include `<script>` tags.
- HTML does not include inline event handler attributes such as `onclick`.
- HTML and CSS do not reference external network assets or unsafe URLs.
- Request input size is below the synchronous feature limit.

Invalid proposals are still persisted with validation errors, but the API must set `is_applyable=false` and the UI must not render an Apply action for them.

## Prompt Contract

The service prompt should instruct the model to:

- Improve layout, print styling, typography, spacing, and visual hierarchy.
- Preserve all existing Jinja expressions and statements.
- Use only tokens already present in the current template.
- Avoid adding JavaScript.
- Avoid external fonts, images, scripts, and remote URLs.
- Return only JSON.

Expected model response:

```json
{
  "html": "<!DOCTYPE html>...",
  "css": "body { ... }",
  "summary": "Improved spacing, headings, and print-friendly table styling."
}
```

The backend must treat the prompt contract as untrusted input. It must parse, validate, and sanitize the response before marking a proposal applyable.

## Frontend Experience

Enable the AI panel only for edit mode because proposals attach to an existing persisted template.

Panel states:

- New-template disabled state explaining that AI improvements are available after the template is created.
- Instruction input.
- Loading state while proposal creation is in progress.
- Valid proposal state with summary and Apply button.
- Invalid proposal state with validation errors and no Apply button.
- Proposal history list, newest first.

Review UI should keep the first version simple:

- Tabs for `Summary`, `HTML`, and `CSS`.
- Read-only current vs proposed blocks or side-by-side textareas.
- No new diff dependency unless one already exists in the project.

Apply behavior:

- Replaces local `html` and `css` editor state.
- Marks the proposal applied server-side.
- Does not call the existing template save endpoint.
- Leaves final persistence to the existing Save Changes button.

## Error Handling

Backend should return clear errors for:

- AI requests disabled.
- Missing provider configuration.
- Template not found.
- Template too large for synchronous AI improvement.
- LiteLLM timeout or provider failure.
- Invalid model output.
- Validation failures.

Provider failures should persist a `failed` proposal record when enough request context exists. Validation failures should persist an `invalid` proposal record with user-readable validation errors.

Frontend should:

- Keep the user's current editor content unchanged on request failure.
- Show provider and validation errors near the AI panel.
- Allow retry with a revised instruction.
- Never offer Apply for failed or invalid proposals.

## Testing

Backend tests:

- Successful proposal creation with LiteLLM mocked.
- Invalid JSON/model response is persisted as invalid or failed and is not applyable.
- Unknown tokens fail validation.
- Removed existing tokens or Jinja statements fail validation.
- Unsafe HTML/CSS fails validation.
- Preview-render failure blocks applyability.
- Proposal history lists only proposals for the selected template.
- Apply endpoint marks the proposal applied without mutating the template.

Frontend verification:

- AI panel is disabled for new templates.
- Edit-mode proposal request uses current unsaved HTML/CSS.
- Valid proposal can be applied into local editor fields.
- Invalid proposal displays validation errors and no Apply action.
- History renders newest proposals.

Manual UAT:

1. Edit an existing template.
2. Ask AI to improve print-friendly layout.
3. Confirm a valid proposal appears.
4. Apply the proposal.
5. Save the template.
6. Preview or generate a document using the template.

## Future Extensions

- New-template generation from prompt.
- Async proposal jobs for slow providers.
- Multi-turn assistant panel.
- Admin and auditor proposal visibility.
- Version comparison between applied proposals and saved template revisions.
- Provider selection per request.

`

## File: docs/superpowers/plans/2026-07-15-ai-template-agent.md
`
# AI Template Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a proposal-first AI improvement workflow for existing HTML templates that returns validated, persisted HTML/CSS proposals and lets users apply them into the editor before saving.

**Architecture:** Backend owns proposal creation, LiteLLM orchestration, strict validation, proposal persistence, and apply tracking under the existing content-template API. Frontend adds an edit-mode AI panel that requests proposals, displays history, and applies valid proposals into local editor state without auto-saving. The synchronous backend service boundary must be narrow enough to move proposal creation to async jobs later.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic, Jinja2 sandbox validation, LiteLLM, React 19, TypeScript, Vite, existing BFF proxy.

## Global Constraints

- Use LiteLLM as the first AI runtime abstraction.
- Keep AI requests synchronous in Phase 16, but isolate the service boundary for future async jobs.
- Persist full proposal history, including invalid and failed proposals.
- Do not add admin or auditor roles in Phase 16.
- Proposal history is visible to users who can edit the template.
- AI output must be review-first and never auto-save a template.
- Valid proposals can change CSS and full HTML formatting, but must preserve every existing Jinja expression and statement.
- A proposal is applyable only after strict backend validation and preview rendering pass.
- BFF stays a session-aware proxy; do not add custom AI orchestration there.
- Use `rtk` prefixes in verification commands.

---

## File Structure

Create:

- `backend/alembic/versions/0014_template_ai_proposals.py` - migration for proposal history.
- `backend/app/models/template_ai_proposal.py` - proposal persistence model.
- `backend/app/schemas/template_ai_proposal.py` - API request and response schemas.
- `backend/app/services/template_ai_agent.py` - prompt construction, LiteLLM call, response parsing, and validation orchestration.
- `backend/app/api/template_ai_proposals.py` - proposal routes.
- `backend/tests/test_template_ai_proposals.py` - backend API/service tests.
- `frontend/src/pages/content/components/AiProposalPanel.tsx` - editor-side AI proposal panel.

Modify:

- `backend/app/models/__init__.py` - export the proposal model.
- `backend/app/main.py` - include the proposal router.
- `backend/app/config.py` - add AI configuration fields.
- `backend/pyproject.toml` - add `litellm` if not already installed in the backend environment.
- `backend/app/services/content_validation.py` - expose helpers for extracting Jinja expressions/statements when needed.
- `frontend/src/lib/content.ts` - add typed proposal API helpers.
- `frontend/src/pages/content/HtmlTemplateCreatePage.tsx` - mount AI panel in edit mode and wire Apply into local state.

---

## Task 1: Proposal Persistence Model and Migration

**Files:**

- Create: `backend/alembic/versions/0014_template_ai_proposals.py`
- Create: `backend/app/models/template_ai_proposal.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces SQLAlchemy class `HtmlTemplateAiProposal`.
- Later tasks import `HtmlTemplateAiProposal` from `app.models.template_ai_proposal`.
- Status values are exact strings: `valid`, `invalid`, `failed`.

- [ ] **Step 1: Write failing model persistence test**

Add this test to `backend/tests/test_template_ai_proposals.py`:

```python
import uuid

from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal


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
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_template_ai_proposal_persists_full_history -v"
```

Expected: FAIL with import error for `app.models.template_ai_proposal`.

- [ ] **Step 3: Add model**

Create `backend/app/models/template_ai_proposal.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

AI_PROPOSAL_STATUSES = ("valid", "invalid", "failed")


class HtmlTemplateAiProposal(Base):
    __tablename__ = "html_template_ai_proposals"
    __table_args__ = (
        CheckConstraint(
            f"status IN {AI_PROPOSAL_STATUSES!r}",
            name="ck_html_template_ai_proposal_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("html_templates.id", ondelete="CASCADE"),
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    instruction: Mapped[str] = mapped_column(Text)
    input_html: Mapped[str] = mapped_column(Text)
    input_css: Mapped[str] = mapped_column(Text, default="")
    proposed_html: Mapped[str] = mapped_column(Text, default="")
    proposed_css: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(default="litellm")
    model: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="invalid")
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_applyable: Mapped[bool] = mapped_column(default=False)
    applied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    template: Mapped["HtmlTemplate"] = relationship()
    created_by: Mapped["User"] = relationship()
```

Modify `backend/app/models/__init__.py`:

```python
from app.models.template_ai_proposal import HtmlTemplateAiProposal
```

- [ ] **Step 4: Add migration**

Create `backend/alembic/versions/0014_template_ai_proposals.py`:

```python
"""Create HTML template AI proposal history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "html_template_ai_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("template_id", sa.Uuid(), sa.ForeignKey("html_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("input_html", sa.Text(), nullable=False),
        sa.Column("input_css", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("proposed_css", sa.Text(), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider", sa.String(), nullable=False, server_default="litellm"),
        sa.Column("model", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="invalid"),
        sa.Column("validation_errors", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False, server_default="[]"),
        sa.Column("is_applyable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('valid', 'invalid', 'failed')",
            name="ck_html_template_ai_proposal_status",
        ),
    )
    op.create_index("ix_html_template_ai_proposals_template_id", "html_template_ai_proposals", ["template_id"])
    op.create_index("ix_html_template_ai_proposals_created_by_id", "html_template_ai_proposals", ["created_by_id"])


def downgrade() -> None:
    op.drop_index("ix_html_template_ai_proposals_created_by_id", table_name="html_template_ai_proposals")
    op.drop_index("ix_html_template_ai_proposals_template_id", table_name="html_template_ai_proposals")
    op.drop_table("html_template_ai_proposals")
```

- [ ] **Step 5: Run test and verify it passes**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_template_ai_proposal_persists_full_history -v"
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add backend/alembic/versions/0014_template_ai_proposals.py backend/app/models/template_ai_proposal.py backend/app/models/__init__.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: add template ai proposal model"
```

---

## Task 2: Validation Helpers for AI Proposals

**Files:**

- Modify: `backend/app/services/content_validation.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces `extract_jinja_markers(html: str) -> set[str]`.
- Produces `validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]`.
- Later service task uses these helpers to enforce token and statement preservation.

- [ ] **Step 1: Write failing validation helper tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers


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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_extract_jinja_markers_includes_expressions_and_statements tests/test_template_ai_proposals.py::test_validate_preserved_jinja_markers_reports_removed_marker -v"
```

Expected: FAIL with import error for the new helper functions.

- [ ] **Step 3: Implement marker helpers**

Add near the top of `backend/app/services/content_validation.py`:

```python
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
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_extract_jinja_markers_includes_expressions_and_statements tests/test_template_ai_proposals.py::test_validate_preserved_jinja_markers_reports_removed_marker -v"
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
rtk git add backend/app/services/content_validation.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: validate preserved jinja markers"
```

---

## Task 3: AI Agent Service with Strict Validation

**Files:**

- Create: `backend/app/services/template_ai_agent.py`
- Modify: `backend/app/config.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces `TemplateAiAgent.create_proposal(...) -> TemplateAiProposalResult`.
- Produces `TemplateAiProposalResult` dataclass with `proposed_html`, `proposed_css`, `summary`, `status`, `validation_errors`, `is_applyable`, `provider`, `model`.
- Later API route calls `TemplateAiAgent(settings).create_proposal(...)`.

- [ ] **Step 1: Write failing service tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
import pytest

from app.services.template_ai_agent import TemplateAiAgent


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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k template_ai_agent -v"
```

Expected: FAIL with import error for `app.services.template_ai_agent`.

- [ ] **Step 3: Add backend dependency and config**

Modify `backend/pyproject.toml` dependencies:

```toml
"litellm>=1.80.0",
```

Modify `backend/app/config.py` inside `Settings`:

```python
ai_requests_enabled: bool = False
ai_provider_model: str = "gpt-4o-mini"
ai_request_timeout_seconds: int = 30
ai_max_input_chars: int = 20000
ai_max_output_tokens: int = 2000
```

- [ ] **Step 4: Implement service**

Create `backend/app/services/template_ai_agent.py`:

```python
import json
import re
from dataclasses import dataclass

from litellm import completion

from app.services.content_validation import validate_preserved_jinja_markers, validate_template_tokens
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

        proposed_html = str(parsed.get("html", ""))
        proposed_css = str(parsed.get("css", ""))
        summary = str(parsed.get("summary", ""))
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

        errors.extend(validate_preserved_jinja_markers(current_html, proposed_html))

        try:
            validate_template_tokens(proposed_html, document_fields)
        except Exception as exc:
            errors.append(str(getattr(exc, "detail", exc)))

        try:
            render_html_page_to_pdf(proposed_html, mock_data, proposed_css)
        except Exception as exc:
            errors.append(str(getattr(exc, "detail", exc)))

        return errors

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

- [ ] **Step 5: Run service tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k template_ai_agent -v"
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add backend/pyproject.toml backend/app/config.py backend/app/services/template_ai_agent.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: add template ai agent service"
```

---

## Task 4: Proposal API Routes

**Files:**

- Create: `backend/app/schemas/template_ai_proposal.py`
- Create: `backend/app/api/template_ai_proposals.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces API routes:
  - `POST /api/content/templates/{template_id}/ai-proposals`
  - `GET /api/content/templates/{template_id}/ai-proposals`
  - `POST /api/content/templates/{template_id}/ai-proposals/{proposal_id}/apply`
- Later frontend task consumes exact response fields from `HtmlTemplateAiProposalOut`.

- [ ] **Step 1: Write failing API tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
from datetime import datetime

from app.services.template_ai_agent import TemplateAiProposalResult


def test_create_ai_proposal_persists_and_returns_applyable(client, db_session, user, monkeypatch):
    template = create_template_fixture(db_session, user)

    def fake_create_proposal(**kwargs):
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

    monkeypatch.setattr("app.api.template_ai_proposals.TemplateAiAgent.create_proposal", fake_create_proposal)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)

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


def test_apply_ai_proposal_marks_applied_without_mutating_template(client, db_session, user):
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
```

Add this fixture helper above the API tests:

```python
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
```

- [ ] **Step 2: Run API tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k 'create_ai_proposal or apply_ai_proposal' -v"
```

Expected: FAIL with route not found or import error.

- [ ] **Step 3: Add schemas**

Create `backend/app/schemas/template_ai_proposal.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HtmlTemplateAiProposalCreate(BaseModel):
    instruction: str
    current_html: str
    current_css: str | None = ""
    mock_data: dict | None = None


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

- [ ] **Step 4: Add routes**

Create `backend/app/api/template_ai_proposals.py`:

```python
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.schemas.template_ai_proposal import HtmlTemplateAiProposalCreate, HtmlTemplateAiProposalOut
from app.services.template_ai_agent import TemplateAiAgent

router = APIRouter(prefix="/api/content/templates/{template_id}/ai-proposals", tags=["template-ai-proposals"])


def _load_template(template_id: UUID, db: SQLAlchemySession) -> HtmlTemplate:
    template = (
        db.query(HtmlTemplate)
        .options(joinedload(HtmlTemplate.document_type).joinedload("fields"), joinedload(HtmlTemplate.created_by))
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
    template = _load_template(template_id, db)
    agent = TemplateAiAgent(
        model=settings.ai_provider_model,
        enabled=settings.ai_requests_enabled,
        timeout_seconds=settings.ai_request_timeout_seconds,
        max_input_chars=settings.ai_max_input_chars,
        max_output_tokens=settings.ai_max_output_tokens,
    )
    result = agent.create_proposal(
        instruction=payload.instruction,
        current_html=payload.current_html,
        current_css=payload.current_css or "",
        document_fields=[field.name for field in template.document_type.fields],
        mock_data=payload.mock_data or template.mock_data or {},
    )
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

If SQLAlchemy rejects the string-based nested `joinedload`, replace `_load_template` options with the typed field import:

```python
from app.models.document_type import DocumentType

.options(joinedload(HtmlTemplate.document_type).joinedload(DocumentType.fields), joinedload(HtmlTemplate.created_by))
```

- [ ] **Step 5: Include router**

Modify `backend/app/main.py`:

```python
from app.api.template_ai_proposals import router as template_ai_proposals_router
```

And add:

```python
app.include_router(template_ai_proposals_router)
```

- [ ] **Step 6: Run API tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -k 'create_ai_proposal or apply_ai_proposal' -v"
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
rtk git add backend/app/schemas/template_ai_proposal.py backend/app/api/template_ai_proposals.py backend/app/main.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: expose template ai proposal api"
```

---

## Task 5: Frontend API Client

**Files:**

- Modify: `frontend/src/lib/content.ts`

**Interfaces:**

- Produces `TemplateAiProposal` interface.
- Produces `createTemplateAiProposal(templateId, payload)`.
- Produces `listTemplateAiProposals(templateId)`.
- Produces `markTemplateAiProposalApplied(templateId, proposalId)`.
- Later UI task imports these functions.

- [ ] **Step 1: Add TypeScript interfaces and client functions**

Modify `frontend/src/lib/content.ts`:

```ts
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

- [ ] **Step 2: Run frontend type build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
rtk git add frontend/src/lib/content.ts
rtk git commit -m "feat: add template ai proposal client"
```

---

## Task 6: AI Proposal Panel UI

**Files:**

- Create: `frontend/src/pages/content/components/AiProposalPanel.tsx`
- Modify: `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`

**Interfaces:**

- `AiProposalPanel` props:
  - `templateId: string | null`
  - `html: string`
  - `css: string`
  - `mockDataJson: string`
  - `onApply(proposal: TemplateAiProposal): void`
- Consumes frontend API helpers from Task 5.

- [ ] **Step 1: Create panel component**

Create `frontend/src/pages/content/components/AiProposalPanel.tsx`:

```tsx
import { useEffect, useState } from "react";

import {
  createTemplateAiProposal,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type TemplateAiProposal,
} from "../../../lib/content";

interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  onApply: (proposal: TemplateAiProposal) => void;
}

function parseMockData(mockDataJson: string): Record<string, unknown> | null {
  if (!mockDataJson.trim()) return null;
  const parsed = JSON.parse(mockDataJson);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Mock data must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

export default function AiProposalPanel({ templateId, html, css, mockDataJson, onApply }: AiProposalPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [proposals, setProposals] = useState<TemplateAiProposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<TemplateAiProposal | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "html" | "css">("summary");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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

  const requestProposal = async () => {
    if (!templateId || !instruction.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
      });
      setProposals((current) => [proposal, ...current]);
      setActiveProposal(proposal);
      setActiveTab("summary");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI proposal failed.");
    } finally {
      setLoading(false);
    }
  };

  const applyProposal = async () => {
    if (!templateId || !activeProposal || !activeProposal.is_applyable) return;
    const applied = await markTemplateAiProposalApplied(templateId, activeProposal.id);
    onApply(applied);
    setProposals((current) => current.map((proposal) => (proposal.id === applied.id ? applied : proposal)));
    setActiveProposal(applied);
  };

  if (!templateId) {
    return (
      <div className="rounded border border-outline-variant bg-surface-container-low p-sm text-xs text-secondary">
        AI improvements are available after this template is created.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-sm rounded border border-outline-variant bg-white p-sm">
      <div className="flex items-center gap-xs">
        <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
        <h3 className="font-headings text-sm font-bold text-on-surface">AI Improve</h3>
      </div>

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
        disabled={loading || !instruction.trim()}
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
            disabled={!activeProposal.is_applyable}
            className="rounded border border-primary px-md py-xs text-xs font-bold text-primary disabled:border-outline-variant disabled:text-secondary"
          >
            Apply proposal
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
    </section>
  );
}
```

- [ ] **Step 2: Mount panel in editor**

Modify `frontend/src/pages/content/HtmlTemplateCreatePage.tsx` imports:

```tsx
import AiProposalPanel from "./components/AiProposalPanel";
import type { TemplateAiProposal } from "../../lib/content";
```

Add handler inside `HtmlTemplateCreatePage`:

```tsx
const handleApplyAiProposal = (proposal: TemplateAiProposal) => {
  setHtml(proposal.proposed_html);
  setCss(proposal.proposed_css);
  setHtmlTouched(true);
};
```

Insert the panel at the top of the right panel before the CSS section. Change the CSS and mock-data panel heights from `h-1/2` to flexible thirds:

```tsx
<div className="h-1/3 overflow-y-auto border-b border-outline-variant p-sm bg-surface">
  <AiProposalPanel
    templateId={isEditMode && id ? id : null}
    html={html}
    css={css}
    mockDataJson={mockDataJson}
    onApply={handleApplyAiProposal}
  />
</div>
```

Then update the CSS and mock-data wrappers to:

```tsx
<div className="h-1/3 flex flex-col border-b border-outline-variant overflow-hidden">
```

and:

```tsx
<div className="h-1/3 flex flex-col overflow-hidden">
```

- [ ] **Step 3: Run frontend build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
rtk git add frontend/src/pages/content/components/AiProposalPanel.tsx frontend/src/pages/content/HtmlTemplateCreatePage.tsx
rtk git commit -m "feat: add ai proposal panel"
```

---

## Task 7: End-to-End Verification and Documentation

**Files:**

- Modify: `.env.example`
- Modify: `.planning/ROADMAP.md`
- Create or modify: `.planning/phases/16-ai-agent-for-page-templating/16-01-PLAN.md`

**Interfaces:**

- Documents required environment variables and verification commands.
- Marks Phase 16 planning artifacts consistently with GSD conventions.

- [ ] **Step 1: Document AI environment configuration**

Add to `.env.example`:

```dotenv
AI_REQUESTS_ENABLED=false
AI_PROVIDER_MODEL=gpt-4o-mini
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_INPUT_CHARS=20000
AI_MAX_OUTPUT_TOKENS=2000
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
```

- [ ] **Step 2: Run backend proposal tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -v"
```

Expected: PASS.

- [ ] **Step 3: Run existing template regression tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_content_templates.py tests/test_template_ast_validation.py tests/test_pdf_generator.py -v"
```

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 5: Manual UAT**

Run the app with the existing local development flow, then verify:

```text
1. Open an existing HTML template in edit mode.
2. Confirm AI Improve panel is visible.
3. Enter: Make this template more formal and print-friendly.
4. Confirm a valid proposal appears.
5. Confirm invalid validation errors block Apply when the mocked/provider output removes a token.
6. Apply a valid proposal.
7. Confirm local HTML and CSS fields update.
8. Click Save Changes.
9. Preview or generate a document using the saved template.
```

- [ ] **Step 6: Commit documentation and planning updates**

Run:

```bash
rtk git add .env.example .planning/ROADMAP.md .planning/phases/16-ai-agent-for-page-templating/16-01-PLAN.md
rtk git commit -m "docs: document ai template agent verification"
```

---

## Self-Review Notes

Spec coverage:

- Proposal-first backend agent is covered by Tasks 3 and 4.
- LiteLLM abstraction is covered by Task 3.
- Strict validation is covered by Tasks 2 and 3.
- Persisted full proposal history is covered by Tasks 1 and 4.
- Frontend review/apply flow is covered by Tasks 5 and 6.
- No admin/auditor role work is introduced.
- Sync-first, async-ready service boundary is covered by `TemplateAiAgent`.

Completeness scan:

- No deferred implementation markers are used.
- Every task has files, interfaces, commands, and expected outcomes.

Type consistency:

- Backend proposal status values are consistent across model, service, schemas, and frontend types.
- API response field names match Pydantic schema and frontend interfaces.
- Frontend Apply uses `proposed_html` and `proposed_css`, matching backend response fields.
`
