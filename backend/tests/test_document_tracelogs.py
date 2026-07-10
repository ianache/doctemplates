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
    monkeypatch.setattr(
        "app.api.document_designs.generate_composed_pdf",
        lambda design, payload, db, mock_fallback=False: b"%PDF-1.4\n%%EOF",
    )

    response = client.post(f"/api/document-designs/{design.id}/generate", json={"name": "Acme"})

    assert response.status_code == 201
    data = response.json()
    issuance = db_session.get(DocumentIssuance, data["id"])
    assert issuance is not None
    assert issuance.status == "success"
    assert len(issuance.tracelogs) == 1
    tracelog = issuance.tracelogs[0]
    assert tracelog.event_type == "generation"
    assert tracelog.user_id == user.id
    assert tracelog.metadata_["source"] == "POST /api/document-designs/{design_id}/generate"
    assert tracelog.metadata_["design_id"] == str(design.id)
