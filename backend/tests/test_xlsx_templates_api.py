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
