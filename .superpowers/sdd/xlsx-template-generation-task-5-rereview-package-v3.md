# Task 5 Re-Review Package V3
 M backend/app/workers/document_generation.py
 M backend/tests/test_async_generation_jobs.py
 M backend/tests/test_document_tracelogs.py
?? .superpowers/sdd/xlsx-template-generation-task-5-report.md

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
    monkeypatch.setattr(dg.generate_document, "delay", mock_delay)

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
        raise AssertionError("generator should not be called for completed issuance")
    monkeypatch.setattr("app.workers.document_generation.generate_document_file", track_call)

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

## File: backend/tests/test_document_tracelogs.py
```
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_type import DocumentType
from app.models.user import User
from app.services.document_generation import GeneratedDocument


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub=f"trace-sub-{uuid.uuid4()}", email=f"trace-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_design(db_session: SQLAlchemySession, user: User) -> DocumentDesign:
    document_type = DocumentType(
        name=f"Trace Type {uuid.uuid4()}",
        description="Trace test document type",
        created_by=user,
        fields=[],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Trace Design",
        description="Trace test design",
        status="active",
        version_group_id=uuid.uuid4(),
        version_number=1,
        created_by=user,
    )
    db_session.add_all([document_type, design])
    db_session.commit()
    db_session.refresh(design)
    return design


def _create_issuance(
    db_session: SQLAlchemySession,
    user: User,
    design: DocumentDesign,
    *,
    status: str = "success",
) -> DocumentIssuance:
    issuance = DocumentIssuance(
        design_version_id=design.id,
        file_path=f"/tmp/{uuid.uuid4()}.pdf",
        user_id=user.id,
        input_data={"cliente": "Acme"},
        status=status,
    )
    db_session.add(issuance)
    db_session.commit()
    db_session.refresh(issuance)
    return issuance


def test_document_tracelogs_persist_chronologically(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = _create_issuance(db_session, user, design)

    db_session.add_all(
        [
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=user.id,
                event_type="generation",
                metadata_={"source": "generate"},
            ),
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=user.id,
                event_type="download",
                metadata_={"source": "download"},
            ),
        ]
    )
    db_session.commit()

    db_session.refresh(issuance)
    assert [row.event_type for row in issuance.tracelogs] == ["generation", "download"]
    assert issuance.tracelogs[0].metadata_ == {"source": "generate"}


def test_deleting_issuance_cascades_document_tracelogs(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = _create_issuance(db_session, user, design)
    tracelog = DocumentTracelog(
        issuance_id=issuance.id,
        user_id=user.id,
        event_type="generation",
        metadata_={"source": "generate"},
    )
    db_session.add(tracelog)
    db_session.commit()
    tracelog_id = tracelog.id

    db_session.delete(issuance)
    db_session.commit()

    assert db_session.get(DocumentTracelog, tracelog_id) is None


def test_document_tracelog_rejects_invalid_event_type(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    issuance = _create_issuance(db_session, user, design)

    db_session.add(
        DocumentTracelog(
            issuance_id=issuance.id,
            user_id=user.id,
            event_type="preview",
            metadata_={},
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_document_issuance_rejects_invalid_status(
    client: TestClient,
    db_session: SQLAlchemySession,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)

    db_session.add(
        DocumentIssuance(
            design_version_id=design.id,
            file_path=f"/tmp/{uuid.uuid4()}.pdf",
            user_id=user.id,
            input_data={},
            status="pending",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_generate_document_creates_generation_tracelog(
    client: TestClient,
    db_session: SQLAlchemySession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user)
    
    # Mock generation in the Celery worker
    monkeypatch.setattr(
        "app.workers.document_generation.generate_document_file",
        lambda *args, **kwargs: GeneratedDocument(
            content=b"%PDF-1.4\n%%EOF",
            mime_type="application/pdf",
            filename="test.pdf",
            extension="pdf",
        ),
    )

    response = client.post(f"/api/document-designs/{design.id}/generate", json={"name": "Acme"})

    assert response.status_code == 202
    data = response.json()
    issuance = db_session.get(DocumentIssuance, data["id"])
    assert issuance is not None
    assert issuance.status == "success"
    assert len(issuance.tracelogs) == 1
    tracelog = issuance.tracelogs[0]
    assert tracelog.event_type == "generation"
    assert tracelog.user_id == user.id
    assert tracelog.metadata_["source"] == "Celery Worker"
    assert tracelog.metadata_["design_id"] == str(design.id)

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
- `backend/tests/test_document_tracelogs.py`

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
- Updated enqueue test to patch `generate_document.delay`, matching the production enqueue path.
- Updated document tracelog worker test to patch `generate_document_file`.
- Updated worker idempotency test to patch `generate_document_file` and fail if generation is attempted.

Verification:

- `rtk proxy python -m compileall -q backend/app/workers/document_generation.py backend/tests/test_async_generation_jobs.py backend/tests/test_xlsx_issuance_generation.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_async_generation_jobs.py tests/test_xlsx_issuance_generation.py -q }'`: blocked by `failed to open file C:\Users\ilver\AppData\Local\uv\cache\sdists-v9\.git: Access is denied. (os error 5)`.
- `rtk proxy python -m compileall -q backend/tests/test_async_generation_jobs.py backend/tests/test_document_tracelogs.py backend/app/workers/document_generation.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_async_generation_jobs.py tests/test_document_tracelogs.py tests/test_xlsx_issuance_generation.py -q }'`: blocked by the same uv cache access denied error.
- `rtk proxy python -m compileall -q backend/tests/test_async_generation_jobs.py`: passed.
- `rtk proxy powershell -NoProfile -Command '& { Set-Location backend; uv run pytest tests/test_async_generation_jobs.py -q }'`: blocked by the same uv cache access denied error.

```
