from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.user import User


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="design-sub", email="design@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_document_type(
    db_session: SQLAlchemySession,
    user: User,
    name: str = "Policy",
    field_names: list[str] | None = None,
) -> DocumentType:
    fields = field_names or ["cliente.nombre", "cliente.edad"]
    document_type = DocumentType(
        name=name,
        description=f"{name} document type",
        created_by=user,
        fields=[
            DocumentTypeField(
                name=field_name,
                type="string",
                description=field_name,
                position=index,
            )
            for index, field_name in enumerate(fields)
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _create_template(
    db_session: SQLAlchemySession,
    user: User,
    document_type: DocumentType,
    name: str = "Template",
    token_names: list[str] | None = None,
) -> HtmlTemplate:
    tokens = token_names or ["cliente.nombre"]
    template = HtmlTemplate(
        document_type=document_type,
        name=name,
        html="".join(f"<p>{{{{{token}}}}}</p>" for token in tokens),
        token_names=tokens,
        created_by=user,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)
    return template


def _create_pdf(
    db_session: SQLAlchemySession,
    user: User,
    filename: str = "static.pdf",
    document_type: DocumentType | None = None,
) -> StaticPdfAsset:
    asset = StaticPdfAsset(
        original_filename=filename,
        stored_filename=filename,
        stored_path=f"/tmp/{filename}",
        page_count=2,
        page_start=None,
        page_end=None,
        file_size=128,
        document_type=document_type,
        created_by=user,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset


def _create_design(
    client: TestClient,
    document_type: DocumentType,
    name: str = "Policy Design",
) -> dict:
    response = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(document_type.id),
            "name": name,
            "description": "A composed policy document",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_and_detail_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)

    created = _create_design(client, document_type)
    assert created["status"] == "draft"
    assert created["document_type_id"] == str(document_type.id)
    assert created["document_type_name"] == "Policy"
    assert created["created_by_email"] == "design@example.com"
    assert created["pages"] == []

    list_response = client.get("/api/document-designs")
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Policy Design"
    assert rows[0]["page_count"] == 0

    detail_response = client.get(f"/api/document-designs/{created['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Policy Design"


def test_design_requests_require_auth(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = User(sub="design-no-auth", email="design-no-auth@example.com")
    db_session.add(user)
    db_session.commit()
    document_type = _create_document_type(db_session, user)

    response = client.post(
        "/api/document-designs",
        json={"document_type_id": str(document_type.id), "name": "No auth"},
    )

    assert response.status_code == 401


def test_add_pages_snapshots_compatibility_and_reorder(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    other_type = _create_document_type(db_session, user, name="Invoice", field_names=["invoice.id"])
    template = _create_template(db_session, user, document_type, name="Main template")
    other_template = _create_template(
        db_session,
        user,
        other_type,
        name="Wrong template",
        token_names=["invoice.id"],
    )
    global_pdf = _create_pdf(db_session, user, filename="global.pdf")
    typed_pdf = _create_pdf(db_session, user, filename="typed.pdf", document_type=document_type)
    other_pdf = _create_pdf(db_session, user, filename="other.pdf", document_type=other_type)
    design = _create_design(client, document_type)

    template_response = client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id), "title": "Template page"},
    )
    assert template_response.status_code == 201
    template_page = template_response.json()
    assert template_page["block_type"] == "html_template"
    assert template_page["position"] == 0
    assert template_page["snapshot"]["name"] == "Main template"
    assert template_page["snapshot"]["token_names"] == ["cliente.nombre"]

    wrong_template_response = client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(other_template.id)},
    )
    assert wrong_template_response.status_code == 400

    global_pdf_response = client.post(
        f"/api/document-designs/{design['id']}/pages/static-pdf",
        json={"static_pdf_asset_id": str(global_pdf.id), "title": "Global PDF"},
    )
    assert global_pdf_response.status_code == 201

    typed_pdf_response = client.post(
        f"/api/document-designs/{design['id']}/pages/static-pdf",
        json={"static_pdf_asset_id": str(typed_pdf.id), "title": "Typed PDF"},
    )
    assert typed_pdf_response.status_code == 201
    typed_pdf_page = typed_pdf_response.json()
    assert typed_pdf_page["snapshot"]["filename"] == "typed.pdf"

    duplicate_pdf_response = client.post(
        f"/api/document-designs/{design['id']}/pages/static-pdf",
        json={"static_pdf_asset_id": str(typed_pdf.id)},
    )
    assert duplicate_pdf_response.status_code == 400

    incompatible_pdf_response = client.post(
        f"/api/document-designs/{design['id']}/pages/static-pdf",
        json={"static_pdf_asset_id": str(other_pdf.id)},
    )
    assert incompatible_pdf_response.status_code == 400

    reordered_ids = [
        typed_pdf_page["id"],
        global_pdf_response.json()["id"],
        template_page["id"],
    ]
    reorder_response = client.patch(
        f"/api/document-designs/{design['id']}/pages/reorder",
        json={"page_ids": reordered_ids},
    )
    assert reorder_response.status_code == 200
    assert [page["id"] for page in reorder_response.json()["pages"]] == reordered_ids
    assert [page["position"] for page in reorder_response.json()["pages"]] == [0, 1, 2]


def test_update_delete_and_activate_design(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    empty_design = _create_design(client, document_type, name="Empty")

    empty_activate = client.post(f"/api/document-designs/{empty_design['id']}/activate")
    assert empty_activate.status_code == 400

    design = _create_design(client, document_type, name="Ready")
    page_response = client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    assert page_response.status_code == 201
    page = page_response.json()

    update_response = client.patch(
        f"/api/document-designs/{design['id']}/pages/{page['id']}",
        json={"title": "Updated title", "notes": "Internal note", "config": {"copies": 2}},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated title"
    assert update_response.json()["notes"] == "Internal note"
    assert update_response.json()["config"] == {"copies": 2}

    activate_response = client.post(f"/api/document-designs/{design['id']}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["status"] == "active"

    delete_response = client.delete(f"/api/document-designs/{design['id']}/pages/{page['id']}")
    assert delete_response.status_code == 204


def test_activation_reports_invalid_template_tokens(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type, token_names=["cliente.nombre"])
    design = _create_design(client, document_type)

    page_response = client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    assert page_response.status_code == 201

    template.token_names = ["cliente.nombre", "cliente.inexistente"]
    template.html = "<p>{{cliente.nombre}}</p><p>{{cliente.inexistente}}</p>"
    db_session.commit()

    activate_response = client.post(f"/api/document-designs/{design['id']}/activate")
    assert activate_response.status_code == 400
    assert "cliente.inexistente" in activate_response.text
