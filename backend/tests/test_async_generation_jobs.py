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

    # Mock PDF generation
    monkeypatch.setattr(
        "app.workers.document_generation.generate_composed_pdf",
        lambda *args, **kwargs: b"%PDF-dummy-success",
    )

    # Call worker task directly
    generate_document_pdf(issuance.id)

    # Reload from DB
    db_session.expire_all()
    updated = db_session.get(DocumentIssuance, issuance.id)
    assert updated.status == "success"
    assert updated.storage_key is not None
    assert updated.completed_at is not None
    assert updated.started_at is not None
    assert updated.error_message is None

    # Verify storage contains the file
    from app.services.content_storage import get_storage_provider
    storage = get_storage_provider()
    assert storage.exists(updated.storage_key) is True
    assert storage.read(updated.storage_key) == b"%PDF-dummy-success"

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
    monkeypatch.setattr("app.workers.document_generation.generate_composed_pdf", raise_err)

    # Call worker task
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
