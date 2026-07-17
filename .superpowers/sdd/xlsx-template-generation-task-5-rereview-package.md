# Task 5 Re-Review Package
 M backend/app/api/issuances.py
 M backend/app/schemas/document_issuance.py
 M backend/app/services/issuance_jobs.py
 M backend/app/services/storage/local.py
 M backend/app/services/storage/s3.py
 M backend/app/workers/document_generation.py
 M backend/tests/test_async_generation_jobs.py
?? .superpowers/sdd/xlsx-template-generation-task-5-report.md
?? backend/app/services/document_generation.py
?? backend/tests/test_xlsx_issuance_generation.py

## File: backend/app/services/document_generation.py
```
from dataclasses import dataclass

from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.document_issuance import DocumentIssuance
from app.services.pdf_generator import generate_composed_pdf
from app.services.storage.base import StorageProvider
from app.services.xlsx_renderer import render_xlsx_template

PDF_MIME_TYPE = "application/pdf"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True)
class GeneratedDocument:
    content: bytes
    mime_type: str
    filename: str
    extension: str


def generate_document_file(
    issuance: DocumentIssuance,
    db: SQLAlchemySession,
    storage_provider: StorageProvider,
) -> GeneratedDocument:
    design = issuance.design_version
    if design.output_format == "xlsx":
        if design.xlsx_template is None:
            raise ValueError("XLSX design is missing its template")
        workbook_bytes = storage_provider.get(
            design.xlsx_template.storage_key,
            category="xlsx_templates",
        )
        content = render_xlsx_template(workbook_bytes, issuance.input_data)
        return GeneratedDocument(
            content=content,
            mime_type=XLSX_MIME_TYPE,
            filename=f"{issuance.id}.xlsx",
            extension="xlsx",
        )

    content = generate_composed_pdf(
        design,
        issuance.input_data,
        db,
        storage_provider,
        mock_fallback=False,
    )
    return GeneratedDocument(
        content=content,
        mime_type=PDF_MIME_TYPE,
        filename=f"{issuance.id}.pdf",
        extension="pdf",
    )

```

## File: backend/app/services/issuance_jobs.py
```
def enqueue_document_generation(issuance_id: str) -> str:
    """Enqueues document generation via a Celery worker task.

    Lazily imports the task to allow app startup and testing before the
    worker module is fully defined.
    """
    from app.workers.document_generation import generate_document
    task = generate_document.delay(issuance_id)
    return str(task.id)

```

## File: backend/app/workers/document_generation.py
```
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import joinedload, selectinload

from app.workers.celery_app import celery_app
from app.db import SessionLocal
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_design import DocumentDesign
from app.services.document_generation import generate_document_file
from app.dependencies import get_storage_provider

logger = logging.getLogger(__name__)


def _generate_document_impl(issuance_id: str) -> None:
    db = SessionLocal()
    try:
        issuance_uuid = issuance_id if isinstance(issuance_id, uuid.UUID) else uuid.UUID(issuance_id)
        # Lock issuance row for update to prevent concurrent task runs from racing
        issuance = (
            db.query(DocumentIssuance)
            .filter(DocumentIssuance.id == issuance_uuid)
            .with_for_update()
            .first()
        )

        if not issuance:
            logger.error(f"DocumentIssuance {issuance_id} not found.")
            return

        if issuance.status != "queued":
            logger.info(f"DocumentIssuance {issuance_id} has status '{issuance.status}'. Skipping generation.")
            return

        # 1. Update status to processing
        issuance.status = "processing"
        issuance.started_at = datetime.utcnow()
        db.commit()

        # Re-fetch for generation logic to ensure we are operating on clean DB state
        design = (
            db.query(DocumentDesign)
            .options(
                joinedload(DocumentDesign.document_type),
                joinedload(DocumentDesign.created_by),
                joinedload(DocumentDesign.xlsx_template),
                selectinload(DocumentDesign.pages),
            )
            .filter(DocumentDesign.id == issuance.design_version_id)
            .first()
        )

        if not design:
            raise ValueError(f"DocumentDesign {issuance.design_version_id} not found.")

        # 2. Generate document bytes
        storage_provider = get_storage_provider()
        issuance.design_version = design
        generated = generate_document_file(issuance, db, storage_provider)

        # 3. Save to storage
        storage_key = storage_provider.save(
            f"{issuance.id}.{generated.extension}",
            generated.content,
            category="issuances"
        )

        # 4. Update status to success
        issuance.storage_key = storage_key
        issuance.output_format = design.output_format
        issuance.mime_type = generated.mime_type
        issuance.filename = generated.filename
        issuance.status = "success"
        issuance.completed_at = datetime.utcnow()

        # 5. Create tracelog
        tracelog = DocumentTracelog(
            issuance_id=issuance.id,
            user_id=issuance.user_id,
            event_type="generation",
            metadata_={
                "source": "Celery Worker",
                "design_id": str(design.id),
            },
        )
        db.add(tracelog)
        db.commit()
        logger.info(f"Successfully generated document for DocumentIssuance {issuance_id}")

    except Exception as e:
        db.rollback()
        logger.exception(f"Error generating document for DocumentIssuance {issuance_id}")
        
        # Open a new transaction to record the failure status securely
        fail_db = SessionLocal()
        try:
            issuance_uuid = issuance_id if isinstance(issuance_id, uuid.UUID) else uuid.UUID(issuance_id)
            issuance = fail_db.query(DocumentIssuance).filter(DocumentIssuance.id == issuance_uuid).first()
            if issuance:
                issuance.status = "failure"
                # Truncate error message to avoid DB constraints or excessive sizes
                issuance.error_message = str(e)[:1000]
                issuance.completed_at = datetime.utcnow()
                fail_db.commit()
        except Exception as fail_err:
            logger.exception(f"Failed to record failure status for {issuance_id}: {fail_err}")
        finally:
            fail_db.close()
        
        raise e
    finally:
        db.close()


@celery_app.task(name="app.workers.document_generation.generate_document")
def generate_document(issuance_id: str) -> None:
    """Task to generate a document file asynchronously."""
    return _generate_document_impl(issuance_id)


@celery_app.task(name="app.workers.document_generation.generate_document_pdf")
def generate_document_pdf(issuance_id: str) -> None:
    """Backward-compatible task name for already queued PDF generation jobs."""
    return _generate_document_impl(issuance_id)

```

## File: backend/app/api/issuances.py
```
from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.user import User
from app.dependencies import get_storage_provider
from app.services.storage.base import StorageProvider
from app.schemas.document_issuance import (
    DocumentIssuanceLibraryItem,
    DocumentIssuanceShareOut,
    DocumentTracelogOut,
)
from app.utils.signature import generate_issuance_signature, verify_issuance_signature

router = APIRouter(prefix="/api/issuances", tags=["issuances"])
public_router = APIRouter(prefix="/api/public/document-issuances", tags=["public-issuances"])


def _request_metadata(request: Request, route: str) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "route": route,
    }


def _require_issuance(db: SQLAlchemySession, issuance_id: UUID) -> DocumentIssuance:
    issuance = (
        db.query(DocumentIssuance)
        .options(
            joinedload(DocumentIssuance.design_version),
            joinedload(DocumentIssuance.user),
        )
        .filter(DocumentIssuance.id == issuance_id)
        .first()
    )
    if issuance is None:
        raise HTTPException(status_code=404, detail="Document issuance not found")
    return issuance


def _issuance_out(issuance: DocumentIssuance) -> DocumentIssuanceLibraryItem:
    return DocumentIssuanceLibraryItem(
        id=issuance.id,
        design_version_id=issuance.design_version_id,
        design_name=issuance.design_version.name,
        output_format=issuance.output_format,
        mime_type=issuance.mime_type,
        filename=issuance.filename,
        preview_storage_key=issuance.preview_storage_key,
        status=issuance.status,
        design_status=issuance.design_version.status,
        design_version_number=issuance.design_version.version_number,
        user_id=issuance.user_id,
        generated_by_email=issuance.user.email,
        input_data=issuance.input_data,
        metadata_values=issuance.metadata_values,
        created_at=issuance.created_at,
        preview_url=f"/api/issuances/{issuance.id}/preview",
        download_url=f"/api/issuances/{issuance.id}/download",
        celery_task_id=issuance.celery_task_id,
        error_message=issuance.error_message,
        queued_at=issuance.queued_at,
        started_at=issuance.started_at,
        completed_at=issuance.completed_at,
        retry_count=issuance.retry_count,
    )


def _document_response(
    issuance: DocumentIssuance,
    storage_provider: StorageProvider,
    disposition: str = "attachment",
) -> Response:
    try:
        return storage_provider.get_download_response(
            issuance.storage_key,
            filename=issuance.filename or f"{issuance.id}.pdf",
            category="issuances",
            disposition=disposition,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Issued document file not found on storage")


def _append_tracelog(
    db: SQLAlchemySession,
    issuance: DocumentIssuance,
    event_type: Literal["download", "share"],
    user_id: UUID | None,
    metadata: dict,
) -> None:
    db.add(
        DocumentTracelog(
            issuance_id=issuance.id,
            user_id=user_id,
            event_type=event_type,
            metadata_=metadata,
        )
    )
    db.commit()


def _verify_issuance_ready(issuance: DocumentIssuance) -> None:
    if issuance.status in ("queued", "processing"):
        raise HTTPException(
            status_code=409,
            detail="Document generation is not complete"
        )
    if issuance.status == "failure":
        raise HTTPException(
            status_code=409,
            detail=issuance.error_message or "Document generation failed"
        )
    if not issuance.storage_key:
        raise HTTPException(
            status_code=409,
            detail="Document file is not ready"
        )


@public_router.get("/{issuance_id}/download")
def public_download_issuance(
    issuance_id: UUID,
    signature: str,
    request: Request,
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    if not verify_issuance_signature(issuance_id, signature):
        raise HTTPException(status_code=403, detail="Invalid document signature")

    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    response = _document_response(issuance, storage_provider)
    _append_tracelog(
        db,
        issuance,
        "download",
        None,
        _request_metadata(request, f"GET /api/public/document-issuances/{issuance.id}/download"),
    )
    return response


@router.get("", response_model=list[DocumentIssuanceLibraryItem])
def list_issuances(
    design_name: str | None = None,
    id: UUID | None = None,
    status: Literal["queued", "processing", "success", "failure"] | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    metadata_key: str | None = None,
    metadata_value: str | None = None,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentIssuanceLibraryItem]:
    query = (
        db.query(DocumentIssuance)
        .join(DocumentIssuance.design_version)
        .join(DocumentIssuance.user)
        .options(
            joinedload(DocumentIssuance.design_version),
            joinedload(DocumentIssuance.user),
        )
    )

    if design_name:
        query = query.filter(DocumentDesign.name.ilike(f"%{design_name}%"))
    if id is not None:
        query = query.filter(DocumentIssuance.id == id)
    if status is not None:
        query = query.filter(DocumentIssuance.status == status)
    if created_from is not None:
        query = query.filter(DocumentIssuance.created_at >= datetime.combine(created_from, time.min))
    if created_to is not None:
        query = query.filter(DocumentIssuance.created_at <= datetime.combine(created_to, time.max))
    if metadata_key and metadata_value is not None:
        query = query.filter(
            func.coalesce(func.json_extract_path_text(DocumentIssuance.metadata_values, metadata_key), "").ilike(
                f"%{metadata_value}%"
            )
        )

    issuances = query.order_by(DocumentIssuance.created_at.desc()).all()
    return [_issuance_out(issuance) for issuance in issuances]


@router.get("/{issuance_id}", response_model=DocumentIssuanceLibraryItem)
def get_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuanceLibraryItem:
    return _issuance_out(_require_issuance(db, issuance_id))


@router.get("/{issuance_id}/preview")
def preview_issuance(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    return _document_response(issuance, storage_provider, disposition="inline")


@router.get("/{issuance_id}/download")
def download_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
    storage_provider = Depends(get_storage_provider),
):
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    response = _document_response(issuance, storage_provider)
    _append_tracelog(
        db,
        issuance,
        "download",
        user.id,
        _request_metadata(request, f"GET /api/issuances/{issuance.id}/download"),
    )
    return response


@router.post("/{issuance_id}/share", response_model=DocumentIssuanceShareOut)
def share_issuance(
    issuance_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentIssuanceShareOut:
    issuance = _require_issuance(db, issuance_id)
    _verify_issuance_ready(issuance)
    signature = generate_issuance_signature(issuance.id)
    public_url = f"/api/public/document-issuances/{issuance.id}/download?signature={signature}"
    _append_tracelog(
        db,
        issuance,
        "share",
        user.id,
        _request_metadata(request, f"POST /api/issuances/{issuance.id}/share"),
    )
    return DocumentIssuanceShareOut(public_url=public_url)


@router.get("/{issuance_id}/tracelogs", response_model=list[DocumentTracelogOut])
def list_issuance_tracelogs(
    issuance_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentTracelog]:
    _require_issuance(db, issuance_id)
    return (
        db.query(DocumentTracelog)
        .filter(DocumentTracelog.issuance_id == issuance_id)
        .order_by(DocumentTracelog.created_at.asc())
        .all()
    )

```

## File: backend/app/schemas/document_issuance.py
```
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentTracelogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issuance_id: UUID
    event_type: str
    user_id: UUID | None
    metadata: dict = Field(validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime


class DocumentIssuanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_version_id: UUID
    file_path: str | None = None
    output_format: str = "pdf"
    mime_type: str | None = None
    filename: str | None = None
    preview_storage_key: str | None = None
    user_id: UUID
    input_data: dict
    metadata_values: dict | None = None
    status: str
    created_at: datetime

    celery_task_id: str | None = None
    error_message: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


class DocumentIssuanceLibraryItem(BaseModel):
    id: UUID
    design_version_id: UUID
    design_name: str
    output_format: str = "pdf"
    mime_type: str | None = None
    filename: str | None = None
    preview_storage_key: str | None = None
    status: str
    design_status: str
    design_version_number: int | None
    user_id: UUID
    generated_by_email: str
    input_data: dict
    metadata_values: dict | None = None
    created_at: datetime
    preview_url: str
    download_url: str

    celery_task_id: str | None = None
    error_message: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0


class DocumentIssuanceShareOut(BaseModel):
    public_url: str

```

## File: backend/app/services/storage/local.py
```
import io
import mimetypes
import os
from pathlib import Path
from fastapi import Response
from fastapi.responses import FileResponse

from app.services.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, root_paths: dict[str, str]):
        self.root_paths = root_paths

    def _get_path(self, key: str, category: str) -> Path:
        path = Path(key)
        if path.is_absolute():
            return path
        root = self.root_paths.get(category)
        if not root:
            raise ValueError(f"Unknown storage category: {category}")
        return Path(root) / key

    def save(self, key: str, content: bytes, category: str) -> str:
        path = self._get_path(key, category)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def get(self, key: str, category: str) -> bytes:
        path = self._get_path(key, category)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.read_bytes()

    def get_stream(self, key: str, category: str) -> io.BytesIO:
        return io.BytesIO(self.get(key, category))

    def delete(self, key: str, category: str) -> None:
        path = self._get_path(key, category)
        if path.exists():
            os.remove(path)

    def get_download_response(self, key: str, filename: str, category: str, disposition: str = "attachment") -> Response:
        path = self._get_path(key, category)
        if not path.exists():
            raise FileNotFoundError(f"File not found for download: {path}")
        headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
        media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return FileResponse(
            path,
            media_type=media_type,
            headers=headers,
        )

    def exists(self, key: str, category: str = "issuances") -> bool:
        try:
            path = self._get_path(key, category)
            return path.exists()
        except Exception:
            return False

```

## File: backend/app/services/storage/s3.py
```
import io
import mimetypes
from pathlib import Path
import boto3
from botocore.client import Config
from fastapi import Response
from fastapi.responses import StreamingResponse

from app.services.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(
        self,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region_name: str | None,
        buckets: dict[str, str],
    ):
        self.buckets = buckets
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name or "us-east-1",
            config=Config(signature_version="s3v4"),
        )

    def _clean_key(self, key: str) -> str:
        path = Path(key)
        if path.is_absolute():
            return path.name
        return key

    def _get_bucket(self, category: str) -> str:
        bucket = self.buckets.get(category)
        if not bucket:
            raise ValueError(f"Unknown storage category: {category}")
        return bucket

    def save(self, key: str, content: bytes, category: str) -> str:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        self.s3.put_object(
            Bucket=bucket,
            Key=cleaned_key,
            Body=content,
            ContentType=mimetypes.guess_type(cleaned_key)[0] or "application/octet-stream"
        )
        return cleaned_key

    def get(self, key: str, category: str) -> bytes:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            resp = self.s3.get_object(Bucket=bucket, Key=cleaned_key)
            return resp["Body"].read()
        except Exception as e:
            # Check for NoSuchKey or generic client errors
            raise FileNotFoundError(f"File not found in S3 bucket {bucket}: {cleaned_key} due to {e}")

    def get_stream(self, key: str, category: str) -> io.BytesIO:
        return io.BytesIO(self.get(key, category))

    def delete(self, key: str, category: str) -> None:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.delete_object(Bucket=bucket, Key=cleaned_key)
        except Exception:
            pass

    def get_download_response(self, key: str, filename: str, category: str, disposition: str = "attachment") -> Response:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.head_object(Bucket=bucket, Key=cleaned_key)
        except Exception:
            raise FileNotFoundError(f"File not found in S3 bucket {bucket}: {cleaned_key}")

        resp = self.s3.get_object(Bucket=bucket, Key=cleaned_key)

        def _stream():
            yield from resp["Body"]

        headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
        return StreamingResponse(
            _stream(),
            media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            headers=headers,
        )

    def exists(self, key: str, category: str = "issuances") -> bool:
        cleaned_key = self._clean_key(key)
        bucket = self._get_bucket(category)
        try:
            self.s3.head_object(Bucket=bucket, Key=cleaned_key)
            return True
        except Exception:
            return False

```

## File: backend/tests/test_xlsx_issuance_generation.py
```
from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook, load_workbook

from app.services.document_generation import XLSX_MIME_TYPE, generate_document_file


class _Storage:
    def __init__(self, workbook_bytes: bytes) -> None:
        self.workbook_bytes = workbook_bytes

    def get(self, key: str, category: str) -> bytes:
        assert key == "template.xlsx"
        assert category == "xlsx_templates"
        return self.workbook_bytes


class _Template:
    storage_key = "template.xlsx"


class _Design:
    output_format = "xlsx"
    xlsx_template = _Template()


class _Issuance:
    id = uuid4()
    design_version = _Design()
    input_data = {"cliente": {"nombre": "ACME"}}


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    workbook.active["A1"] = "{{cliente.nombre}}"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_xlsx_mime_type_constant() -> None:
    assert XLSX_MIME_TYPE == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_generate_document_file_renders_xlsx_workbook() -> None:
    issuance = _Issuance()
    generated = generate_document_file(issuance, db=None, storage_provider=_Storage(_workbook_bytes()))

    assert generated.mime_type == XLSX_MIME_TYPE
    assert generated.filename == f"{issuance.id}.xlsx"
    assert generated.extension == "xlsx"
    workbook = load_workbook(BytesIO(generated.content))
    assert workbook.active["A1"].value == "ACME"

```

## File: backend/tests/test_async_generation_jobs.py
```
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.config import settings
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_type import DocumentType
from app.models.user import User
from app.services.document_generation import GeneratedDocument
from app.workers.document_generation import generate_document_pdf
from app.utils.signature import generate_issuance_signature


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub=f"async-sub-{uuid.uuid4()}", email=f"async-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    from app.auth.session_service import create_session
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_design(db_session: SQLAlchemySession, user: User) -> DocumentDesign:
    document_type = DocumentType(
        name=f"Async Type {uuid.uuid4()}",
        description="Async test document type",
        created_by=user,
        fields=[],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Async Design",
        description="Async test design",
        status="active",
        version_group_id=uuid.uuid4(),
        version_number=1,
        created_by=user,
    )
    db_session.add_all([document_type, design])
    db_session.commit()
    db_session.refresh(design)
    return design


def test_enqueue_endpoint_flow(
    client: TestClient,
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)

    # 1. Disable eager mode temporarily to assert queue status
    monkeypatch.setattr(settings, "celery_task_always_eager", False)

    # Mock Celery delay method to prevent calling Redis
    called_delay = False
    def mock_delay(*args, **kwargs):
        nonlocal called_delay
        called_delay = True
        class MockAsyncResult:
            id = "mock-task-123"
        return MockAsyncResult()

    import app.workers.document_generation as dg
    monkeypatch.setattr(dg.generate_document_pdf, "delay", mock_delay)

    response = client.post(f"/api/document-designs/{design.id}/generate", json={"name": "Acme"})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["celery_task_id"] == "mock-task-123"
    assert called_delay is True

    # Check database state
    issuance = db_session.get(DocumentIssuance, data["id"])
    assert issuance is not None
    assert issuance.status == "queued"
    assert issuance.celery_task_id == "mock-task-123"
    assert issuance.storage_key is None


def test_worker_success_path(
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # 1. Create User, Design and Queued Issuance
    user = User(sub=f"async-sub-{uuid.uuid4()}", email="worker@example.com")
    db_session.add(user)
    db_session.commit()

    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={"name": "Worker Success"},
        status="queued",
    )
    db_session.add(issuance)
    db_session.commit()

    # Mock document generation
    monkeypatch.setattr(
        "app.workers.document_generation.generate_document_file",
        lambda *args, **kwargs: GeneratedDocument(
            content=b"%PDF-dummy-success",
            mime_type="application/pdf",
            filename=f"{issuance.id}.pdf",
            extension="pdf",
        ),
    )

    # Call worker task directly
    generate_document_pdf(issuance.id)

    # Reload from DB
    db_session.expire_all()
    updated = db_session.get(DocumentIssuance, issuance.id)
    assert updated.status == "success"
    assert updated.storage_key is not None
    assert updated.output_format == "pdf"
    assert updated.mime_type == "application/pdf"
    assert updated.filename == f"{issuance.id}.pdf"
    assert updated.completed_at is not None
    assert updated.started_at is not None
    assert updated.error_message is None

    # Verify storage contains the file
    from app.dependencies import get_storage_provider
    storage = get_storage_provider()
    assert storage.exists(updated.storage_key) is True
    assert storage.get(updated.storage_key, "issuances") == b"%PDF-dummy-success"

    # Verify tracelog
    tracelog = db_session.query(DocumentTracelog).filter_by(issuance_id=issuance.id).first()
    assert tracelog is not None
    assert tracelog.event_type == "generation"


def test_worker_failure_path(
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(sub=f"async-sub-{uuid.uuid4()}", email="worker-fail@example.com")
    db_session.add(user)
    db_session.commit()

    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={"name": "Worker Fail"},
        status="queued",
    )
    db_session.add(issuance)
    db_session.commit()

    # Force an exception during rendering
    def raise_err(*args, **kwargs):
        raise RuntimeError("PDF engine crashed horribly!")
    monkeypatch.setattr("app.workers.document_generation.generate_document_file", raise_err)

    # Call worker task
    with pytest.raises(Exception):
        generate_document_pdf(issuance.id)

    # Reload from DB
    db_session.expire_all()
    updated = db_session.get(DocumentIssuance, issuance.id)
    assert updated.status == "failure"
    assert updated.completed_at is not None
    assert "PDF engine crashed horribly" in updated.error_message


def test_worker_idempotency(
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(sub=f"async-sub-{uuid.uuid4()}", email="worker-idem@example.com")
    db_session.add(user)
    db_session.commit()

    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={"name": "Worker Idem"},
        status="success",
        storage_key="existing_key.pdf",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(issuance)
    db_session.commit()

    # Track if generator is called
    generator_called = False
    def track_call(*args, **kwargs):
        nonlocal generator_called
        generator_called = True
        return b""
    monkeypatch.setattr("app.workers.document_generation.generate_composed_pdf", track_call)

    # Call task
    generate_document_pdf(issuance.id)

    assert generator_called is False
    # State should remain unchanged
    db_session.refresh(issuance)
    assert issuance.status == "success"
    assert issuance.storage_key == "existing_key.pdf"


def test_download_share_preview_guards_409(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = DocumentIssuance(
        design_version_id=design.id,
        user_id=user.id,
        input_data={},
        status="queued",
    )
    db_session.add(issuance)
    db_session.commit()

    # Authenticated download -> 409
    resp_dl = client.get(f"/api/issuances/{issuance.id}/download")
    assert resp_dl.status_code == 409

    # Share -> 409
    resp_sh = client.post(f"/api/issuances/{issuance.id}/share")
    assert resp_sh.status_code == 409

    # Public download -> 409
    sig = generate_issuance_signature(issuance.id)
    resp_pub = client.get(f"/api/public/document-issuances/{issuance.id}/download?signature={sig}")
    assert resp_pub.status_code == 409

```

## File: .superpowers/sdd/xlsx-template-generation-task-5-report.md
```
# XLSX Template Generation Task 5 Report

## Status

Implemented format-aware document generation for PDF/XLSX issuances.

## Changed Files

- `backend/app/services/document_generation.py`
- `backend/app/services/issuance_jobs.py`
- `backend/app/workers/document_generation.py`
- `backend/app/api/issuances.py`
- `backend/app/services/storage/local.py`
- `backend/app/services/storage/s3.py`
- `backend/tests/test_xlsx_issuance_generation.py`
- `backend/tests/test_async_generation_jobs.py`

## Verification

- `rtk proxy python -m compileall -q backend/app/services/document_generation.py backend/app/services/issuance_jobs.py backend/app/workers/document_generation.py backend/app/api/issuances.py backend/app/schemas/document_issuance.py backend/app/services/storage/local.py backend/app/services/storage/s3.py backend/tests/test_xlsx_issuance_generation.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_xlsx_issuance_generation.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.

## Commit

No commit created. `.git/index.lock` creation has been blocked in this session, and the worktree contains unrelated dirty files.

---

## Review Fix Report

Fixed Task 5 review findings:

- Added a real Celery task wrapper registered under the legacy task name `app.workers.document_generation.generate_document_pdf`, delegating to the shared implementation.
- Updated existing async worker tests to patch `generate_document_file` and assert persisted output metadata.

Verification:

- `rtk proxy python -m compileall -q backend/app/workers/document_generation.py backend/tests/test_async_generation_jobs.py backend/tests/test_xlsx_issuance_generation.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_async_generation_jobs.py tests/test_xlsx_issuance_generation.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.

```
