from io import BytesIO
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.dependencies import get_storage_provider
from app.models.document_type import DocumentType
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate
from app.schemas.xlsx_template import (
    XlsxTemplateDetail,
    XlsxTemplateListItem,
    XlsxTemplatePreviewRequest,
    XlsxTemplatePreviewResponse,
)
from app.services.storage.base import StorageProvider
from app.services.xlsx_analysis import analyze_xlsx_template
from app.services.xlsx_renderer import preview_xlsx_template


router = APIRouter(prefix="/api/xlsx-templates", tags=["xlsx-templates"])

MAX_WORKBOOK_BYTES = 10 * 1024 * 1024
MAX_ZIP_MEMBERS = 1000
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100


def _reject_macro_enabled_workbook(workbook_bytes: bytes) -> None:
    try:
        with ZipFile(BytesIO(workbook_bytes)) as archive:
            names = {name.lower() for name in archive.namelist()}
            content_types = archive.read("[Content_Types].xml").decode("utf-8", errors="ignore").lower()
    except (BadZipFile, KeyError) as exc:
        raise HTTPException(status_code=400, detail="Invalid .xlsx file") from exc

    if (
        "xl/vbaproject.bin" in names
        or "vnd.ms-office.vbaproject" in content_types
        or "macroenabled" in content_types
    ):
        raise HTTPException(status_code=400, detail="Macro-enabled workbooks not supported")


def _validate_workbook_archive(workbook_bytes: bytes) -> None:
    if len(workbook_bytes) > MAX_WORKBOOK_BYTES:
        raise HTTPException(status_code=400, detail="XLSX file is too large")
    try:
        with ZipFile(BytesIO(workbook_bytes)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                raise HTTPException(status_code=400, detail="XLSX archive has too many files")
            total_uncompressed = sum(info.file_size for info in infos)
            total_compressed = sum(max(info.compress_size, 1) for info in infos)
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise HTTPException(status_code=400, detail="XLSX archive is too large")
            if total_uncompressed / total_compressed > MAX_COMPRESSION_RATIO:
                raise HTTPException(status_code=400, detail="XLSX archive compression ratio is too high")
    except BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid .xlsx file") from exc


def _read_bounded_upload(file: UploadFile) -> bytes:
    content_length = file.headers.get("content-length") if file.headers else None
    if content_length is not None:
        try:
            if int(content_length) > MAX_WORKBOOK_BYTES:
                raise HTTPException(status_code=400, detail="XLSX file is too large")
        except ValueError:
            pass
    workbook_bytes = file.file.read(MAX_WORKBOOK_BYTES + 1)
    if len(workbook_bytes) > MAX_WORKBOOK_BYTES:
        raise HTTPException(status_code=400, detail="XLSX file is too large")
    return workbook_bytes


def _detail(template: XlsxTemplate) -> XlsxTemplateDetail:
    return XlsxTemplateDetail(
        id=template.id,
        document_type_id=template.document_type_id,
        document_type_name=template.document_type.name,
        name=template.name,
        description=template.description,
        original_filename=template.original_filename,
        detected_sheets=list(template.detected_sheets or []),
        detected_tokens=list(template.detected_tokens or []),
        image_slots=list(template.image_slots or []),
        validation_warnings=list(template.validation_warnings or []),
        mock_data=template.mock_data,
        created_by_email=template.created_by.email,
        created_at=template.created_at,
    )


def _get_template(db: SQLAlchemySession, template_id: UUID) -> XlsxTemplate:
    template = (
        db.query(XlsxTemplate)
        .options(joinedload(XlsxTemplate.document_type), joinedload(XlsxTemplate.created_by))
        .filter(XlsxTemplate.id == template_id)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="XLSX template not found")
    return template


@router.post("", response_model=XlsxTemplateDetail, status_code=201)
def upload_xlsx_template(
    document_type_id: UUID = Form(...),
    name: str = Form(...),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> XlsxTemplateDetail:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    document_type = (
        db.query(DocumentType)
        .options(selectinload(DocumentType.fields))
        .filter(DocumentType.id == document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")

    workbook_bytes = _read_bounded_upload(file)
    _validate_workbook_archive(workbook_bytes)
    _reject_macro_enabled_workbook(workbook_bytes)
    try:
        analysis = analyze_xlsx_template(workbook_bytes, {field.name for field in document_type.fields})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid .xlsx file: {exc}") from exc

    storage_key = f"{uuid4()}.xlsx"
    storage_provider.save(storage_key, workbook_bytes, category="xlsx_templates")
    template = XlsxTemplate(
        document_type=document_type,
        name=name,
        description=description,
        storage_key=storage_key,
        original_filename=file.filename,
        detected_sheets=analysis.detected_sheets,
        detected_tokens=analysis.detected_tokens,
        image_slots=analysis.image_slots,
        validation_warnings=analysis.validation_warnings,
        created_by=user,
    )
    db.add(template)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage_provider.delete(storage_key, category="xlsx_templates")
        except Exception:
            pass
        raise
    db.refresh(template)
    db.refresh(document_type)
    db.refresh(user)
    return _detail(template)


@router.get("", response_model=list[XlsxTemplateListItem])
def list_xlsx_templates(
    document_type_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[XlsxTemplateListItem]:
    query = (
        db.query(XlsxTemplate)
        .options(joinedload(XlsxTemplate.document_type), joinedload(XlsxTemplate.created_by))
        .order_by(XlsxTemplate.created_at.desc())
    )
    if document_type_id is not None:
        query = query.filter(XlsxTemplate.document_type_id == document_type_id)
    return [_detail(template) for template in query.all()]


@router.get("/{template_id}", response_model=XlsxTemplateDetail)
def get_xlsx_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> XlsxTemplateDetail:
    return _detail(_get_template(db, template_id))


@router.post("/{template_id}/validate", response_model=XlsxTemplateDetail)
def validate_xlsx_template(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> XlsxTemplateDetail:
    template = _get_template(db, template_id)
    try:
        workbook_bytes = storage_provider.get(template.storage_key, category="xlsx_templates")
        analysis = analyze_xlsx_template(
            workbook_bytes, {field.name for field in template.document_type.fields}
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Stored XLSX template not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid stored .xlsx file: {exc}") from exc

    template.detected_sheets = analysis.detected_sheets
    template.detected_tokens = analysis.detected_tokens
    template.image_slots = analysis.image_slots
    template.validation_warnings = analysis.validation_warnings
    db.commit()
    db.refresh(template)
    return _detail(template)


@router.post("/{template_id}/preview", response_model=XlsxTemplatePreviewResponse)
def preview_xlsx_template_route(
    template_id: UUID,
    request: XlsxTemplatePreviewRequest | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> XlsxTemplatePreviewResponse:
    template = _get_template(db, template_id)
    try:
        workbook_bytes = storage_provider.get(template.storage_key, category="xlsx_templates")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Stored XLSX template not found") from exc

    payload = (
        request.mock_data
        if request is not None and request.mock_data is not None
        else template.mock_data or {}
    )
    try:
        preview = preview_xlsx_template(workbook_bytes, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return XlsxTemplatePreviewResponse(**preview)
