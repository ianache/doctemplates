# Task 6 Re-Review Package
?? .superpowers/sdd/xlsx-template-generation-task-6-report.md
?? backend/app/api/xlsx_templates.py
?? backend/app/schemas/xlsx_template.py
?? backend/app/services/xlsx_renderer.py
?? backend/tests/test_xlsx_preview.py
?? backend/tests/test_xlsx_templates_api.py

## File: backend/app/services/xlsx_renderer.py
```
import copy
import json
from io import BytesIO
from typing import Any

from jinja2.sandbox import SandboxedEnvironment
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from app.services.xlsx_images import normalize_image_value


_JINJA_ENV = SandboxedEnvironment(autoescape=False)
_REPEAT_DEFINED_NAME = "_docman_repeats"


def render_xlsx_template(
    workbook_bytes: bytes,
    payload: dict,
    image_values: dict | None = None,
) -> bytes:
    workbook = load_workbook(BytesIO(workbook_bytes), data_only=False)
    repeat_rows = _render_repeat_rows(workbook, payload)

    for worksheet in workbook.worksheets:
        skipped_rows = repeat_rows.get(worksheet.title, set())
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.row in skipped_rows:
                    continue
                _render_cell(cell, payload)

    _insert_images(workbook, image_values or {})

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def preview_xlsx_template(workbook_bytes: bytes, payload: dict) -> dict:
    rendered_bytes = render_xlsx_template(workbook_bytes, payload)
    workbook = load_workbook(BytesIO(rendered_bytes), data_only=False)
    sheets: list[dict] = []

    for worksheet in workbook.worksheets:
        cells = []
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cells.append({"address": cell.coordinate, "value": cell.value, "style": {}})
        sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "merged_ranges": [str(cell_range) for cell_range in worksheet.merged_cells.ranges],
                "cells": cells,
            }
        )

    return {"sheets": sheets, "warnings": []}


def _render_repeat_rows(workbook, payload: dict) -> dict[str, set[int]]:
    rendered_rows: dict[str, set[int]] = {}
    offset_by_sheet: dict[str, int] = {}

    for spec in _load_repeat_specs(workbook):
        sheet_name = spec["sheet"]
        worksheet = workbook[sheet_name]
        row_index = int(spec["row"]) + offset_by_sheet.get(sheet_name, 0)
        items = _resolve_path(payload, spec["list"])
        if items is None:
            items = []
        if not isinstance(items, list):
            raise ValueError("repeat_list_must_be_array")

        _reject_merged_repeat_row(worksheet, row_index)
        rendered = _render_repeat_row(worksheet, row_index, payload, items)
        rendered_rows.setdefault(sheet_name, set()).update(rendered)
        offset_by_sheet[sheet_name] = offset_by_sheet.get(sheet_name, 0) + len(items) - 1

    return rendered_rows


def _load_repeat_specs(workbook) -> list[dict]:
    defined_name = workbook.defined_names.get(_REPEAT_DEFINED_NAME)
    if defined_name is None:
        return []

    specs: list[dict] = []
    for sheet_name, coordinate in defined_name.destinations:
        worksheet = workbook[sheet_name]
        raw_value = worksheet[coordinate].value
        if raw_value in (None, ""):
            continue
        parsed = json.loads(raw_value)
        if not isinstance(parsed, list):
            raise ValueError("invalid_repeat_metadata")
        for item in parsed:
            if not isinstance(item, dict) or not {"sheet", "row", "list"} <= item.keys():
                raise ValueError("invalid_repeat_metadata")
            specs.append(item)

    return sorted(specs, key=lambda spec: (spec["sheet"], int(spec["row"])))


def _render_repeat_row(worksheet: Worksheet, row_index: int, payload: dict, items: list[dict]) -> set[int]:
    if not items:
        worksheet.delete_rows(row_index, 1)
        return set()

    template_cells = [_snapshot_cell(cell) for cell in worksheet[row_index]]
    template_height = worksheet.row_dimensions[row_index].height
    if len(items) > 1:
        worksheet.insert_rows(row_index + 1, len(items) - 1)

    rendered_rows: set[int] = set()
    for item_index, item in enumerate(items):
        target_row = row_index + item_index
        rendered_rows.add(target_row)
        if template_height is not None:
            worksheet.row_dimensions[target_row].height = template_height
        for template_cell in template_cells:
            target_cell = worksheet.cell(row=target_row, column=template_cell["column"])
            _apply_cell_snapshot(template_cell, target_cell)
            context = {**payload, "item": item}
            _render_cell(target_cell, context)

    return rendered_rows


def _snapshot_cell(cell) -> dict:
    return {
        "column": cell.column,
        "value": cell.value,
        "has_style": cell.has_style,
        "style": copy.copy(cell._style),
        "number_format": cell.number_format,
        "font": copy.copy(cell.font),
        "fill": copy.copy(cell.fill),
        "border": copy.copy(cell.border),
        "alignment": copy.copy(cell.alignment),
        "protection": copy.copy(cell.protection),
    }


def _apply_cell_snapshot(snapshot: dict, target) -> None:
    target.value = snapshot["value"]
    if snapshot["has_style"]:
        target._style = copy.copy(snapshot["style"])
    target.number_format = snapshot["number_format"]
    target.font = copy.copy(snapshot["font"])
    target.fill = copy.copy(snapshot["fill"])
    target.border = copy.copy(snapshot["border"])
    target.alignment = copy.copy(snapshot["alignment"])
    target.protection = copy.copy(snapshot["protection"])


def _render_cell(cell, context: dict) -> None:
    if isinstance(cell.value, str) and "{{" in cell.value:
        cell.value = _escape_formula_text(_JINJA_ENV.from_string(cell.value).render(context))


def _escape_formula_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _insert_images(workbook, image_values: dict) -> None:
    for anchor, raw_value in image_values.items():
        if "!" not in anchor:
            raise ValueError("invalid_image_anchor")
        sheet_name, cell_coordinate = anchor.split("!", 1)
        if sheet_name not in workbook.sheetnames:
            raise ValueError("invalid_image_anchor")
        normalized = normalize_image_value(raw_value)
        image = OpenpyxlImage(BytesIO(normalized.content))
        image.anchor = cell_coordinate
        workbook[sheet_name].add_image(image)


def _reject_merged_repeat_row(worksheet: Worksheet, row_index: int) -> None:
    for merged_range in worksheet.merged_cells.ranges:
        min_col, min_row, max_col, max_row = range_boundaries(str(merged_range))
        del min_col, max_col
        if min_row <= row_index <= max_row:
            raise ValueError("unsupported_merge_in_repeat_range")


def _resolve_path(payload: dict, path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current

```

## File: backend/app/schemas/xlsx_template.py
```
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class XlsxTemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type_id: UUID
    document_type_name: str
    name: str
    description: str | None
    original_filename: str
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]
    mock_data: dict | None
    created_by_email: str
    created_at: datetime


class XlsxTemplateDetail(XlsxTemplateListItem):
    pass


class XlsxTemplatePreviewRequest(BaseModel):
    mock_data: dict | None = None


class XlsxPreviewCell(BaseModel):
    address: str
    value: str | int | float | bool | None
    style: dict = {}


class XlsxPreviewSheet(BaseModel):
    name: str
    max_row: int
    max_column: int
    merged_ranges: list[str]
    cells: list[XlsxPreviewCell]


class XlsxTemplatePreviewResponse(BaseModel):
    sheets: list[XlsxPreviewSheet]
    warnings: list[dict] = []

```

## File: backend/app/api/xlsx_templates.py
```
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

    workbook_bytes = file.file.read()
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

```

## File: backend/tests/test_xlsx_preview.py
```
import io

from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.workbook.defined_name import DefinedName
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.config import settings
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-preview-sub", email="xlsx-preview@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(db_session: SQLAlchemySession, user: User) -> DocumentType:
    document_type = DocumentType(
        name="Preview Workbook",
        description="Preview workbook type",
        allowed_output_formats=["pdf", "xlsx"],
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            )
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["B1"] = "{{cliente.nombre}}"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _repeat_workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "{{item.name}}"
    worksheet["Z1"] = '[{"sheet":"Summary","row":1,"list":"items"}]'
    workbook.defined_names.add(DefinedName("_docman_repeats", attr_text="'Summary'!$Z$1"))
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_preview_returns_sheet_cells(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        upload_response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Preview template"},
            files={
                "file": (
                    "preview.xlsx",
                    _workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert upload_response.status_code == 201
        template_id = upload_response.json()["id"]

        response = client.post(
            f"/api/xlsx-templates/{template_id}/preview",
            json={"mock_data": {"cliente": {"nombre": "ACME"}}},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["sheets"][0]["name"] == "Summary"
        assert body["sheets"][0]["cells"][0]["address"] == "B1"
        assert body["sheets"][0]["cells"][0]["value"] == "ACME"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_uses_template_mock_data_when_body_missing(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        template_id = _upload_preview_template(client, document_type.id)
        template = db_session.get(XlsxTemplate, template_id)
        template.mock_data = {"cliente": {"nombre": "Stored"}}
        db_session.commit()

        response = client.post(f"/api/xlsx-templates/{template_id}/preview")

        assert response.status_code == 200
        assert response.json()["sheets"][0]["cells"][0]["value"] == "Stored"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_empty_mock_data_does_not_fall_back_to_template_mock_data(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        template_id = _upload_preview_template(client, document_type.id)
        template = db_session.get(XlsxTemplate, template_id)
        template.mock_data = {"cliente": {"nombre": "Stored"}}
        db_session.commit()

        response = client.post(f"/api/xlsx-templates/{template_id}/preview", json={"mock_data": {}})

        assert response.status_code == 200
        assert response.json()["sheets"][0]["cells"][0]["value"] == ""
    finally:
        settings.xlsx_template_storage_root = original_root


def test_preview_returns_400_for_renderer_validation_error(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        upload_response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Repeat template"},
            files={
                "file": (
                    "repeat.xlsx",
                    _repeat_workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post(
            f"/api/xlsx-templates/{upload_response.json()['id']}/preview",
            json={"mock_data": {"items": "not-a-list"}},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "repeat_list_must_be_array"
    finally:
        settings.xlsx_template_storage_root = original_root


def _upload_preview_template(client: TestClient, document_type_id) -> str:
    response = client.post(
        "/api/xlsx-templates",
        data={"document_type_id": str(document_type_id), "name": "Preview template"},
        files={
            "file": (
                "preview.xlsx",
                _workbook_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201
    return response.json()["id"]

```

## File: backend/tests/test_xlsx_templates_api.py
```
import io
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.config import settings
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-sub", email="xlsx@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(db_session: SQLAlchemySession, user: User) -> DocumentType:
    document_type = DocumentType(
        name="Workbook",
        description="Workbook template",
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            )
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    workbook.active["A1"] = "{{cliente.nombre}}"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _macro_enabled_workbook_bytes(include_vba_project: bool) -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types><Override ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml" /></Types>',
        )
        if include_vba_project:
            archive.writestr("xl/vbaProject.bin", b"macro")
    return output.getvalue()


def test_upload_list_and_detail_xlsx_template(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)
    try:
        response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Main workbook"},
            files={"file": ("main.xlsx", _workbook_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

        assert response.status_code == 201
        created = response.json()
        assert created["detected_tokens"] == ["cliente.nombre"]
        assert created["document_type_name"] == "Workbook"

        list_response = client.get("/api/xlsx-templates")
        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == created["id"]

        detail_response = client.get(f"/api/xlsx-templates/{created['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["original_filename"] == "main.xlsx"
    finally:
        settings.xlsx_template_storage_root = original_root


def test_upload_rejects_non_xlsx_filename(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)

    for filename in ("macro.xlsm", "notes.txt"):
        response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Invalid workbook"},
            files={"file": (filename, b"not a workbook", "application/octet-stream")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Only .xlsx files are supported"


def test_upload_rejects_renamed_macro_enabled_workbook(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)

    for include_vba_project in (False, True):
        response = client.post(
            "/api/xlsx-templates",
            data={"document_type_id": str(document_type.id), "name": "Macro workbook"},
            files={
                "file": (
                    "macro.xlsx",
                    _macro_enabled_workbook_bytes(include_vba_project),
                    "application/octet-stream",
                )
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Macro-enabled workbooks not supported"


def test_upload_deletes_stored_workbook_when_database_commit_fails(
    client: TestClient, db_session: SQLAlchemySession, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user)
    original_root = settings.xlsx_template_storage_root
    settings.xlsx_template_storage_root = str(tmp_path)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(db_session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
            with pytest.raises(RuntimeError, match="commit failed"):
                client.post(
                    "/api/xlsx-templates",
                    data={"document_type_id": str(document_type.id), "name": "Failed workbook"},
                    files={"file": ("failed.xlsx", _workbook_bytes(), "application/octet-stream")},
                )

        assert list(tmp_path.iterdir()) == []
    finally:
        settings.xlsx_template_storage_root = original_root

```

## File: .superpowers/sdd/xlsx-template-generation-task-6-report.md
```
# XLSX Template Generation Task 6 Report

## Status

Implemented XLSX template preview API.

## Changed Files

- `backend/app/services/xlsx_renderer.py`
- `backend/app/schemas/xlsx_template.py`
- `backend/app/api/xlsx_templates.py`
- `backend/tests/test_xlsx_preview.py`

## Verification

- `rtk proxy python -m compileall -q backend/app/services/xlsx_renderer.py backend/app/schemas/xlsx_template.py backend/app/api/xlsx_templates.py backend/tests/test_xlsx_preview.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_xlsx_preview.py tests/test_xlsx_templates_api.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.

## Commit

No commit created because the repository index is not writable in this session and the worktree contains unrelated dirty files.

---

## Review Fix Report

Fixed Task 6 review findings:

- Made preview request body optional.
- Preserved explicit empty `mock_data` instead of falling back to stored template mock data.
- Converted renderer `ValueError` failures to HTTP 400 responses.
- Restored the existing macro-enabled workbook error detail expected by Task 2 API tests.
- Added focused preview tests for no-body fallback, explicit empty mock data, and renderer validation errors.

Verification:

- `rtk proxy python -m compileall -q backend/app/api/xlsx_templates.py backend/tests/test_xlsx_templates_api.py backend/tests/test_xlsx_preview.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_xlsx_preview.py tests/test_xlsx_templates_api.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.

```
