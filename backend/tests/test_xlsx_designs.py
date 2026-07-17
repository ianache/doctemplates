from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_design import DocumentDesign
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.models.xlsx_template import XlsxTemplate


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="xlsx-design-sub", email="xlsx-design@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _document_type(
    db_session: SQLAlchemySession,
    user: User,
    name: str = "Workbook Type",
    allowed_output_formats: list[str] | None = None,
) -> DocumentType:
    document_type = DocumentType(
        name=name,
        description=f"{name} description",
        allowed_output_formats=allowed_output_formats or ["pdf"],
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


def _xlsx_template(
    db_session: SQLAlchemySession,
    user: User,
    document_type: DocumentType,
    name: str = "Workbook Template",
    validation_warnings: list[dict] | None = None,
) -> XlsxTemplate:
    template = XlsxTemplate(
        document_type=document_type,
        name=name,
        description=None,
        storage_key=f"{name}.xlsx",
        original_filename=f"{name}.xlsx",
        detected_sheets=[],
        detected_tokens=["cliente.nombre"],
        image_slots=[],
        validation_warnings=validation_warnings or [],
        created_by=user,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def test_create_rejects_xlsx_when_document_type_allows_only_pdf(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf"])

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
        },
    )

    assert response.status_code == 400
    assert "does not allow xlsx output" in response.json()["detail"]


def test_create_requires_template_for_xlsx_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX designs require xlsx_template_id"


def test_create_rejects_xlsx_template_on_pdf_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "PDF design",
            "output_format": "pdf",
            "xlsx_template_id": str(template.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "PDF designs cannot reference an XLSX template"


def test_create_rejects_xlsx_template_from_another_document_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(
        db_session, user, name="Primary Type", allowed_output_formats=["pdf", "xlsx"]
    )
    other_type = _document_type(
        db_session, user, name="Other Type", allowed_output_formats=["pdf", "xlsx"]
    )
    template = _xlsx_template(db_session, user, other_type)

    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "Workbook design",
            "output_format": "xlsx",
            "xlsx_template_id": str(template.id),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template must belong to the design document type"


def test_update_applies_xlsx_design_validation(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)
    create_response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": "PDF design",
            "output_format": "pdf",
        },
    )
    assert create_response.status_code == 201
    design_id = create_response.json()["id"]

    missing_template = client.put(
        f"/api/document-designs/{design_id}",
        json={
            "name": "Workbook design",
            "description": None,
            "output_format": "xlsx",
        },
    )
    assert missing_template.status_code == 400
    assert missing_template.json()["detail"] == "XLSX designs require xlsx_template_id"

    valid_update = client.put(
        f"/api/document-designs/{design_id}",
        json={
            "name": "Workbook design",
            "description": None,
            "output_format": "xlsx",
            "xlsx_template_id": str(template.id),
        },
    )
    assert valid_update.status_code == 200
    assert valid_update.json()["output_format"] == "xlsx"
    assert valid_update.json()["xlsx_template_id"] == str(template.id)


def test_activate_xlsx_design_succeeds_without_pdf_pages(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(db_session, user, document_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_activate_xlsx_design_fails_when_template_has_warnings(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf", "xlsx"])
    template = _xlsx_template(
        db_session,
        user,
        document_type,
        validation_warnings=[{"type": "unknown_schema_token", "cell": "A1"}],
    )
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template has validation warnings"


def test_activate_xlsx_design_rechecks_allowed_output_formats(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(db_session, user, allowed_output_formats=["pdf"])
    template = _xlsx_template(db_session, user, document_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert "does not allow xlsx output" in response.json()["detail"]


def test_activate_xlsx_design_rechecks_template_document_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _document_type(
        db_session, user, name="Primary Type", allowed_output_formats=["pdf", "xlsx"]
    )
    other_type = _document_type(
        db_session, user, name="Other Type", allowed_output_formats=["pdf", "xlsx"]
    )
    template = _xlsx_template(db_session, user, other_type)
    design = DocumentDesign(
        document_type=document_type,
        name="Workbook design",
        output_format="xlsx",
        xlsx_template=template,
        status="draft",
        created_by=user,
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)

    response = client.post(f"/api/document-designs/{design.id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"] == "XLSX template must belong to the design document type"
