from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.user import User
from app.schemas.content_template import (
    HtmlTemplateCreate,
    HtmlTemplateDetail,
    HtmlTemplateListItem,
    HtmlTemplatePreviewRequest,
    HtmlTemplatePreviewResponse,
)
from app.services.content_validation import validate_template_tokens

router = APIRouter(prefix="/api/content/templates", tags=["content-templates"])


def _detail(template: HtmlTemplate) -> HtmlTemplateDetail:
    return HtmlTemplateDetail(
        id=template.id,
        name=template.name,
        document_type_id=template.document_type_id,
        document_type_name=template.document_type.name,
        html=template.html,
        css=template.css,
        token_names=list(template.token_names or []),
        mock_data=template.mock_data,
        created_by_email=template.created_by.email,
        created_at=template.created_at,
    )


@router.post("", response_model=HtmlTemplateDetail, status_code=201)
def create_html_template(
    payload: HtmlTemplateCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateDetail:
    document_type = (
        db.query(DocumentType)
        .options(joinedload(DocumentType.fields), joinedload(DocumentType.created_by))
        .filter(DocumentType.id == payload.document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")

    tokens = validate_template_tokens(payload.html, [field.name for field in document_type.fields])

    template = HtmlTemplate(
        document_type=document_type,
        name=payload.name,
        html=payload.html,
        css=payload.css,
        token_names=tokens,
        created_by=user,
        mock_data=payload.mock_data,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    db.refresh(document_type)
    db.refresh(user)
    return _detail(template)


@router.get("", response_model=list[HtmlTemplateListItem])
def list_html_templates(
    document_type_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[HtmlTemplateListItem]:
    query = (
        db.query(HtmlTemplate)
        .options(joinedload(HtmlTemplate.document_type), joinedload(HtmlTemplate.created_by))
        .order_by(HtmlTemplate.created_at.desc())
    )
    if document_type_id is not None:
        query = query.filter(HtmlTemplate.document_type_id == document_type_id)
    templates = query.all()
    return [
        HtmlTemplateListItem(
            id=template.id,
            name=template.name,
            document_type_id=template.document_type_id,
            document_type_name=template.document_type.name,
            token_count=len(template.token_names or []),
            created_by_email=template.created_by.email,
            created_at=template.created_at,
        )
        for template in templates
    ]


@router.get("/{template_id}", response_model=HtmlTemplateDetail)
def get_html_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateDetail:
    template = (
        db.query(HtmlTemplate)
        .options(joinedload(HtmlTemplate.document_type), joinedload(HtmlTemplate.created_by))
        .filter(HtmlTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return _detail(template)


@router.put("/{template_id}", response_model=HtmlTemplateDetail)
def update_html_template(
    template_id: UUID,
    payload: HtmlTemplateCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> HtmlTemplateDetail:
    template = (
        db.query(HtmlTemplate)
        .options(joinedload(HtmlTemplate.document_type), joinedload(HtmlTemplate.created_by))
        .filter(HtmlTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    document_type = (
        db.query(DocumentType)
        .options(joinedload(DocumentType.fields))
        .filter(DocumentType.id == payload.document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")

    tokens = validate_template_tokens(payload.html, [field.name for field in document_type.fields])

    template.name = payload.name
    template.document_type_id = payload.document_type_id
    template.html = payload.html
    template.css = payload.css
    template.token_names = tokens
    template.mock_data = payload.mock_data

    db.commit()
    db.refresh(template)
    db.refresh(document_type)
    db.refresh(user)
    return _detail(template)


@router.post("/preview", response_model=HtmlTemplatePreviewResponse)
def preview_template(
    payload: HtmlTemplatePreviewRequest,
    user: User = Depends(get_current_user),
) -> HtmlTemplatePreviewResponse:
    from app.services.pdf_generator import CaseInsensitiveSandboxedEnvironment, RecursiveCaseInsensitiveDict, date_format_filter

    env = CaseInsensitiveSandboxedEnvironment(autoescape=True)
    env.filters["date_format"] = date_format_filter

    try:
        template = env.from_string(payload.html)
        context = payload.mock_data or {}
        wrapped_context = RecursiveCaseInsensitiveDict(context)
        rendered_html = template.render(wrapped_context)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Template rendering failed: {str(e)}"
        )

    return HtmlTemplatePreviewResponse(rendered_html=rendered_html)
