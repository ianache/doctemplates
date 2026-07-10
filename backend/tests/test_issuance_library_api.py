import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_design import DocumentDesign
from app.models.document_issuance import DocumentIssuance
from app.models.document_tracelog import DocumentTracelog
from app.models.document_type import DocumentType
from app.models.user import User
from app.utils.signature import generate_issuance_signature


def test_issuance_signature_is_stable_and_sha256_hex() -> None:
    from app.utils.signature import generate_issuance_signature

    issuance_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    signature = generate_issuance_signature(issuance_id)

    assert signature == generate_issuance_signature(issuance_id)
    assert len(signature) == 64
    assert int(signature, 16) >= 0


def test_issuance_signature_verification_rejects_tampering() -> None:
    from app.utils.signature import generate_issuance_signature, verify_issuance_signature

    issuance_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    signature = generate_issuance_signature(issuance_id)

    assert verify_issuance_signature(issuance_id, signature)
    assert not verify_issuance_signature(issuance_id, "0" + signature[1:])


def test_public_download_rejects_bad_signature_without_auth(client: TestClient) -> None:
    issuance_id = uuid.uuid4()

    response = client.get(f"/api/public/document-issuances/{issuance_id}/download?signature=bad")

    assert response.status_code == 403


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub=f"library-sub-{uuid.uuid4()}", email=f"library-{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_design(
    db_session: SQLAlchemySession,
    user: User,
    *,
    name: str,
    status: str = "active",
    version_number: int = 1,
) -> DocumentDesign:
    document_type = DocumentType(
        name=f"Library Type {uuid.uuid4()}",
        description="Library test document type",
        created_by=user,
        fields=[],
    )
    design = DocumentDesign(
        document_type=document_type,
        name=name,
        description="Library test design",
        status=status,
        version_group_id=uuid.uuid4(),
        version_number=version_number,
        created_by=user,
    )
    db_session.add_all([document_type, design])
    db_session.commit()
    db_session.refresh(design)
    return design


def _write_pdf(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4\n%%EOF")
    return path


def _create_issuance(
    db_session: SQLAlchemySession,
    user: User,
    design: DocumentDesign,
    tmp_path: Path,
    *,
    status: str = "success",
    created_at: datetime | None = None,
    input_data: dict | None = None,
) -> DocumentIssuance:
    issuance = DocumentIssuance(
        design_version_id=design.id,
        file_path=str(_write_pdf(tmp_path, f"{uuid.uuid4()}.pdf")),
        user_id=user.id,
        input_data=input_data or {"cliente": "Acme"},
        status=status,
    )
    if created_at is not None:
        issuance.created_at = created_at
    db_session.add(issuance)
    db_session.commit()
    db_session.refresh(issuance)
    return issuance


def test_list_issuances_applies_all_filters_against_issuance_status(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    alpha = _create_design(db_session, user, name="Alpha Contract")
    beta = _create_design(db_session, user, name="Beta Contract")
    included = _create_issuance(
        db_session,
        user,
        alpha,
        tmp_path,
        status="success",
        created_at=datetime(2026, 7, 3, 12, 0, 0),
    )
    _create_issuance(
        db_session,
        user,
        alpha,
        tmp_path,
        status="failure",
        created_at=datetime(2026, 7, 3, 12, 0, 0),
    )
    _create_issuance(
        db_session,
        user,
        beta,
        tmp_path,
        status="success",
        created_at=datetime(2026, 7, 3, 12, 0, 0),
    )

    response = client.get(
        "/api/issuances",
        params={
            "design_name": "Alpha",
            "id": str(included.id),
            "status": "success",
            "created_from": "2026-07-01",
            "created_to": "2026-07-04",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert [row["id"] for row in data] == [str(included.id)]
    assert data[0]["status"] == "success"
    assert data[0]["design_name"] == "Alpha Contract"


def test_list_issuances_filters_failure_status_and_rejects_unknown_status(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Failure Contract")
    failed = _create_issuance(db_session, user, design, tmp_path, status="failure")
    _create_issuance(db_session, user, design, tmp_path, status="success")

    response = client.get("/api/issuances", params={"status": "failure"})

    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [str(failed.id)]

    bad_response = client.get("/api/issuances", params={"status": "pending"})
    assert bad_response.status_code in (400, 422)


def test_get_issuance_detail_returns_library_metadata(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Detail Contract", status="superseded", version_number=3)
    issuance = _create_issuance(db_session, user, design, tmp_path, input_data={"name": "Ada"})

    response = client.get(f"/api/issuances/{issuance.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(issuance.id)
    assert data["design_version_id"] == str(design.id)
    assert data["design_name"] == "Detail Contract"
    assert data["status"] == "success"
    assert data["design_status"] == "superseded"
    assert data["design_version_number"] == 3
    assert data["user_id"] == str(user.id)
    assert data["generated_by_email"] == user.email
    assert data["input_data"] == {"name": "Ada"}
    assert data["preview_url"] == f"/api/issuances/{issuance.id}/preview"
    assert data["download_url"] == f"/api/issuances/{issuance.id}/download"


def test_preview_serves_pdf_without_download_tracelog(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Preview Contract")
    issuance = _create_issuance(db_session, user, design, tmp_path)

    response = client.get(f"/api/issuances/{issuance.id}/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert db_session.query(DocumentTracelog).filter_by(event_type="download").count() == 0


def test_authenticated_download_logs_download_tracelog(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Download Contract")
    issuance = _create_issuance(db_session, user, design, tmp_path)

    response = client.get(f"/api/issuances/{issuance.id}/download", headers={"user-agent": "library-test"})

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    tracelog = db_session.query(DocumentTracelog).filter_by(event_type="download").one()
    assert tracelog.issuance_id == issuance.id
    assert tracelog.user_id == user.id
    assert tracelog.metadata_["route"] == f"GET /api/issuances/{issuance.id}/download"
    assert tracelog.metadata_["user_agent"] == "library-test"


def test_share_returns_public_url_and_logs_share_tracelog(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Share Contract")
    issuance = _create_issuance(db_session, user, design, tmp_path)

    response = client.post(f"/api/issuances/{issuance.id}/share", headers={"user-agent": "share-test"})

    assert response.status_code == 200
    public_url = response.json()["public_url"]
    assert public_url.startswith(f"/api/public/document-issuances/{issuance.id}/download?signature=")
    assert public_url.endswith(generate_issuance_signature(issuance.id))
    tracelog = db_session.query(DocumentTracelog).filter_by(event_type="share").one()
    assert tracelog.user_id == user.id
    assert tracelog.metadata_["route"] == f"POST /api/issuances/{issuance.id}/share"
    assert tracelog.metadata_["user_agent"] == "share-test"


def test_valid_public_download_logs_anonymous_download(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Public Contract")
    issuance = _create_issuance(db_session, user, design, tmp_path)
    client.cookies.clear()

    signature = generate_issuance_signature(issuance.id)
    response = client.get(
        f"/api/public/document-issuances/{issuance.id}/download?signature={signature}",
        headers={"user-agent": "public-test"},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    tracelog = db_session.query(DocumentTracelog).filter_by(event_type="download").one()
    assert tracelog.issuance_id == issuance.id
    assert tracelog.user_id is None
    assert tracelog.metadata_["route"] == f"GET /api/public/document-issuances/{issuance.id}/download"
    assert tracelog.metadata_["user_agent"] == "public-test"


def test_tracelogs_are_returned_chronologically(
    client: TestClient,
    db_session: SQLAlchemySession,
    tmp_path: Path,
) -> None:
    user = _auth_client(client, db_session)
    design = _create_design(db_session, user, name="Trace Contract")
    issuance = _create_issuance(db_session, user, design, tmp_path)
    db_session.add_all(
        [
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=user.id,
                event_type="share",
                metadata_={"order": 2},
                created_at=datetime(2026, 7, 3, 12, 0, 0),
            ),
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=user.id,
                event_type="generation",
                metadata_={"order": 1},
                created_at=datetime(2026, 7, 3, 11, 0, 0),
            ),
            DocumentTracelog(
                issuance_id=issuance.id,
                user_id=None,
                event_type="download",
                metadata_={"order": 3},
                created_at=datetime(2026, 7, 3, 13, 0, 0),
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/issuances/{issuance.id}/tracelogs")

    assert response.status_code == 200
    assert [row["event_type"] for row in response.json()] == ["generation", "share", "download"]
    assert [row["metadata"]["order"] for row in response.json()] == [1, 2, 3]
