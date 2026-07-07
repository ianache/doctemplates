import io

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.config import settings
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="pdf-sub", email="pdf@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _make_pdf(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=72, height=72)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_upload_list_detail_and_download_pdf_asset(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    _auth_client(client, db_session)
    original_root = settings.content_storage_root
    settings.content_storage_root = str(tmp_path)
    try:
        pdf_bytes = _make_pdf(2)
        response = client.post(
            "/api/content/static-pdfs",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 201
        created = response.json()
        assert created["filename"] == "sample.pdf"
        assert created["page_count"] == 2
        assert created["download_url"].endswith("/download")

        list_response = client.get("/api/content/static-pdfs")
        assert list_response.status_code == 200
        rows = list_response.json()
        assert len(rows) == 1
        assert rows[0]["filename"] == "sample.pdf"
        assert rows[0]["page_count"] == 2
        assert rows[0]["created_by_email"] == "pdf@example.com"

        asset = db_session.query(StaticPdfAsset).one()
        detail_response = client.get(f"/api/content/static-pdfs/{asset.id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["filename"] == "sample.pdf"
        assert detail["file_size"] > 0
        assert detail["download_url"].endswith("/download")

        download_response = client.get(f"/api/content/static-pdfs/{asset.id}/download")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith("application/pdf")
        downloaded = PdfReader(io.BytesIO(download_response.content))
        assert len(downloaded.pages) == 2
    finally:
        settings.content_storage_root = original_root


def test_upload_page_range_extracts_subset(
    client: TestClient, db_session: SQLAlchemySession, tmp_path
) -> None:
    _auth_client(client, db_session)
    original_root = settings.content_storage_root
    settings.content_storage_root = str(tmp_path)
    try:
        pdf_bytes = _make_pdf(3)
        response = client.post(
            "/api/content/static-pdfs",
            data={"page_start": "2", "page_end": "3"},
            files={"file": ("range.pdf", pdf_bytes, "application/pdf")},
        )

        assert response.status_code == 201
        created = response.json()
        assert created["filename"] == "range.pdf"
        assert created["page_count"] == 2
        assert created["page_start"] == 2
        assert created["page_end"] == 3
    finally:
        settings.content_storage_root = original_root


def test_upload_pdf_requires_auth(client: TestClient, tmp_path) -> None:
    original_root = settings.content_storage_root
    settings.content_storage_root = str(tmp_path)
    try:
        response = client.post(
            "/api/content/static-pdfs",
            files={"file": ("no-auth.pdf", _make_pdf(1), "application/pdf")},
        )
        assert response.status_code == 401
    finally:
        settings.content_storage_root = original_root
