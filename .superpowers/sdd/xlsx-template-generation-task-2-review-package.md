# Task 2 Review Package
## Git Diff
diff --git a/backend/app/config.py b/backend/app/config.py
index de72327..eff58b8 100644
--- a/backend/app/config.py
+++ b/backend/app/config.py
@@ -27,6 +27,7 @@ class Settings(BaseSettings):
     frontend_origin: str
     content_storage_root: str = "../.content-storage"
     issuance_storage_root: str = "../.content-storage/issuances"
+    xlsx_template_storage_root: str = "../.content-storage/xlsx-templates"
 
     # Storage Decoupling Settings
     storage_provider_type: str = "local"
@@ -36,11 +37,25 @@ class Settings(BaseSettings):
     storage_s3_region: str | None = None
     storage_s3_bucket_static_pdfs: str = "docmanagement-static-pdfs"
     storage_s3_bucket_issuances: str = "docmanagement-issuances"
+    storage_s3_bucket_xlsx_templates: str = "docmanagement-xlsx-templates"
 
     # Celery Settings
     celery_broker_url: str = "redis://redis:6379/0"
     celery_result_backend: str = "redis://redis:6379/1"
     celery_task_always_eager: bool = False
 
+    ai_requests_enabled: bool = False
+    ai_default_model: str = "gpt-4o-mini"
+    ai_allowed_models: str = "gpt-4o-mini"
+    ai_provider_model: str = "gpt-4o-mini"
+    gemini_api_key: str = ""
+    groq_api_key: str = ""
+    openai_api_key: str = ""
+    anthropic_api_key: str = ""
+    ollama_api_base: str = "http://localhost:11434"
+    ai_request_timeout_seconds: int = 30
+    ai_max_input_chars: int = 20000
+    ai_max_output_tokens: int = 2000
+
 
 settings = Settings()
diff --git a/backend/app/dependencies.py b/backend/app/dependencies.py
index 46ffcd8..12d1f66 100644
--- a/backend/app/dependencies.py
+++ b/backend/app/dependencies.py
@@ -17,6 +17,7 @@ def get_storage_provider() -> StorageProvider:
             buckets={
                 "static_pdfs": settings.storage_s3_bucket_static_pdfs,
                 "issuances": settings.storage_s3_bucket_issuances,
+                "xlsx_templates": settings.storage_s3_bucket_xlsx_templates,
             }
         )
     else:
@@ -24,5 +25,6 @@ def get_storage_provider() -> StorageProvider:
             root_paths={
                 "static_pdfs": settings.content_storage_root,
                 "issuances": settings.issuance_storage_root,
+                "xlsx_templates": settings.xlsx_template_storage_root,
             }
         )
diff --git a/backend/app/main.py b/backend/app/main.py
index 04fadda..770aa78 100644
--- a/backend/app/main.py
+++ b/backend/app/main.py
@@ -5,9 +5,12 @@ from app.api.content_templates import router as content_templates_router
 from app.api.document_designs import router as document_designs_router
 from app.api.document_types import router as document_types_router
 from app.api.health import router as health_router
+from app.api import ai_models
 from app.api.issuances import public_router as public_issuances_router
 from app.api.issuances import router as issuances_router
 from app.api.static_pdfs import router as static_pdfs_router
+from app.api.template_ai_proposals import router as template_ai_proposals_router
+from app.api.xlsx_templates import router as xlsx_templates_router
 from app.config import settings
 
 app = FastAPI(title="DocManagement API")
@@ -24,9 +27,12 @@ app.include_router(health_router)
 app.include_router(document_types_router)
 app.include_router(content_templates_router)
 app.include_router(static_pdfs_router)
+app.include_router(xlsx_templates_router)
 app.include_router(document_designs_router)
 app.include_router(issuances_router)
 app.include_router(public_issuances_router)
+app.include_router(template_ai_proposals_router)
+app.include_router(ai_models.router)
 
 
 @app.get("/")
diff --git a/backend/pyproject.toml b/backend/pyproject.toml
index 8581600..da1f81c 100644
--- a/backend/pyproject.toml
+++ b/backend/pyproject.toml
@@ -9,6 +9,7 @@ dependencies = [
     "fastapi>=0.139.0",
     "httpx>=0.28.1",
     "itsdangerous>=2.2.0",
+    "litellm>=1.80.0",
     "psycopg[binary]>=3.3.4",
     "pydantic-settings>=2.14.2",
     "pypdf>=6.1.0",
@@ -21,6 +22,8 @@ dependencies = [
     "jinja2>=3.1.5",
     "boto3>=1.43.46",
     "celery[redis]>=5.6.3",
+    "openpyxl>=3.1.5",
+    "pillow>=11.0.0",
 ]
 
 [dependency-groups]

## New Files

### backend/app/schemas/xlsx_template.py
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

### backend/app/services/xlsx_analysis.py
import re
from dataclasses import dataclass
from io import BytesIO

from openpyxl import load_workbook


TOKEN_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*}}")


@dataclass
class XlsxTemplateAnalysis:
    detected_sheets: list[dict]
    detected_tokens: list[str]
    image_slots: list[dict]
    validation_warnings: list[dict]


def analyze_xlsx_template(workbook_bytes: bytes, schema_tokens: set[str]) -> XlsxTemplateAnalysis:
    workbook = load_workbook(BytesIO(workbook_bytes), read_only=False, data_only=False)
    detected_sheets: list[dict] = []
    detected_tokens: list[str] = []
    validation_warnings: list[dict] = []
    seen_tokens: set[str] = set()

    for worksheet in workbook.worksheets:
        detected_sheets.append(
            {
                "name": worksheet.title,
                "max_row": worksheet.max_row,
                "max_column": worksheet.max_column,
                "print_area": str(worksheet.print_area) if worksheet.print_area else None,
                "merged_ranges": [str(cell_range) for cell_range in worksheet.merged_cells.ranges],
            }
        )
        for row in worksheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                for token in TOKEN_PATTERN.findall(cell.value):
                    if token not in seen_tokens:
                        seen_tokens.add(token)
                        detected_tokens.append(token)
                    if token not in schema_tokens:
                        validation_warnings.append(
                            {
                                "type": "unknown_schema_token",
                                "sheet": worksheet.title,
                                "cell": cell.coordinate,
                                "message": f"Token '{{{{{token}}}}}' is not defined by the document type",
                                "suggestion": "Add the field to the document type or replace the token",
                            }
                        )

    return XlsxTemplateAnalysis(
        detected_sheets=detected_sheets,
        detected_tokens=detected_tokens,
        image_slots=[],
        validation_warnings=validation_warnings,
    )

### backend/app/api/xlsx_templates.py
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload, selectinload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.dependencies import get_storage_provider
from app.models.document_type import DocumentType
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate
from app.schemas.xlsx_template import XlsxTemplateDetail, XlsxTemplateListItem
from app.services.storage.base import StorageProvider
from app.services.xlsx_analysis import analyze_xlsx_template


router = APIRouter(prefix="/api/xlsx-templates", tags=["xlsx-templates"])


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
    db.commit()
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

### backend/tests/test_xlsx_analysis.py
import io

from openpyxl import Workbook

from app.services.xlsx_analysis import analyze_xlsx_template


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["A1"] = "Customer: {{cliente.nombre}}"
    worksheet.print_area = "A1:C12"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_analyze_xlsx_template_extracts_sheet_token_and_print_area() -> None:
    analysis = analyze_xlsx_template(_workbook_bytes(), {"cliente.nombre"})

    assert analysis.detected_sheets == [
        {
            "name": "Summary",
            "max_row": 1,
            "max_column": 1,
            "print_area": "'Summary'!$A$1:$C$12",
            "merged_ranges": [],
        }
    ]
    assert analysis.detected_tokens == ["cliente.nombre"]
    assert analysis.validation_warnings == []
    assert analysis.image_slots == []


def test_analyze_xlsx_template_warns_for_unknown_schema_token() -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Summary"
    worksheet["B4"] = "{{cliente.desconocido}}"
    output = io.BytesIO()
    workbook.save(output)

    analysis = analyze_xlsx_template(output.getvalue(), {"cliente.nombre"})

    assert analysis.validation_warnings[0]["type"] == "unknown_schema_token"
    assert analysis.validation_warnings[0]["cell"] == "B4"
    assert analysis.validation_warnings[0]["sheet"] == "Summary"

### backend/tests/test_xlsx_templates_api.py
import io

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
