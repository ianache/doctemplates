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
    document_fields = [field.name for field in template.document_type.fields]
    if agent.is_input_too_large(
        payload.instruction,
        payload.current_html,
        payload.current_css or "",
        document_fields,
    ):
        result = agent.input_size_failed()
    elif not agent.enabled:
        result = agent.requests_disabled()
    elif is_provider_configured(settings, selected_model):
        result = agent.create_proposal(
            instruction=payload.instruction,
            current_html=payload.current_html,
            current_css=payload.current_css or "",
            document_fields=document_fields,
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
        provider=selected_model.provider,
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
