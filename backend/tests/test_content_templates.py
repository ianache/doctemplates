import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="content-sub", email="content@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_document_type(db_session: SQLAlchemySession, user: User) -> DocumentType:
    document_type = DocumentType(
        name="Policy",
        description="Policy template",
        created_by=user,
        fields=[
            DocumentTypeField(
                name="cliente.nombre",
                type="string",
                description="Customer name",
                position=0,
            ),
            DocumentTypeField(
                name="cliente.edad",
                type="number",
                description="Customer age",
                position=1,
            ),
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def test_create_template_rejects_unknown_tokens(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)

    response = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Bad template",
            "html": "<p>{{cliente.nombre}}</p><p>{{cliente.inexistente}}</p>",
        },
    )

    assert response.status_code == 400
    assert "cliente.inexistente" in response.text


def test_create_list_and_detail_template(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)

    create_response = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Main template",
            "html": "<p>{{cliente.nombre}}</p><p>{{cliente.edad}}</p>",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Main template"
    assert created["document_type_name"] == "Policy"
    assert created["token_names"] == ["cliente.edad", "cliente.nombre"]

    list_response = client.get("/api/content/templates")
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Main template"
    assert rows[0]["document_type_name"] == "Policy"
    assert rows[0]["token_count"] == 2
    assert rows[0]["created_by_email"] == "content@example.com"

    template = db_session.query(HtmlTemplate).one()
    detail_response = client.get(f"/api/content/templates/{template.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["html"] == "<p>{{cliente.nombre}}</p><p>{{cliente.edad}}</p>"
    assert detail["token_names"] == ["cliente.edad", "cliente.nombre"]
    assert detail["created_by_email"] == "content@example.com"


def test_create_template_requires_auth(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = User(sub="content-no-auth", email="content-no-auth@example.com")
    db_session.add(user)
    db_session.commit()
    document_type = _create_document_type(db_session, user)

    response = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "No auth",
            "html": "<p>{{cliente.nombre}}</p>",
        },
    )

    assert response.status_code == 401


def test_create_template_case_insensitive_and_fallback(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    
    # Create DocumentType with list field
    document_type = DocumentType(
        name="Contract",
        description="Contract desc",
        created_by=user,
        fields=[
            DocumentTypeField(name="cliente.nombre", type="string", position=0),
            DocumentTypeField(name="cliente.contactos[].nombre", type="string", position=1),
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)

    # 1. Test case variations: Cliente.Nombre and cliente.nombre
    response1 = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Case template",
            "html": "<p>{{Cliente.Nombre}}</p>",
        },
    )
    assert response1.status_code == 201
    assert response1.json()["token_names"] == ["Cliente.Nombre"]

    # 2. Test loop variable fallback: c.nombre
    response2 = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Loop template",
            "html": "<p>{% for c in cliente.contactos %}{{c.nombre}}{% endfor %}</p>",
        },
    )
    assert response2.status_code == 201
    assert response2.json()["token_names"] == ["cliente.contactos", "cliente.contactos[].nombre"]


def test_update_template_success(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)

    # First create a template
    create_response = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Original Name",
            "html": "<p>{{cliente.nombre}}</p>",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    template_id = created["id"]

    # Now update it
    update_response = client.put(
        f"/api/content/templates/{template_id}",
        json={
            "document_type_id": str(document_type.id),
            "name": "Updated Name",
            "html": "<p>{{cliente.nombre}} ({{cliente.edad}})</p>",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Updated Name"
    assert updated["html"] == "<p>{{cliente.nombre}} ({{cliente.edad}})</p>"
    assert set(updated["token_names"]) == {"cliente.nombre", "cliente.edad"}


def test_update_template_rejects_unknown_tokens(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)

    create_response = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Original Name",
            "html": "<p>{{cliente.nombre}}</p>",
        },
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/content/templates/{template_id}",
        json={
            "document_type_id": str(document_type.id),
            "name": "Updated Name",
            "html": "<p>{{cliente.inexistente}}</p>",
        },
    )
    assert update_response.status_code == 400
    assert "cliente.inexistente" in update_response.text


def test_update_template_requires_auth(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)

    create_response = client.post(
        "/api/content/templates",
        json={
            "document_type_id": str(document_type.id),
            "name": "Original Name",
            "html": "<p>{{cliente.nombre}}</p>",
        },
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    # Clear authorization cookie
    client.cookies.clear()

    update_response = client.put(
        f"/api/content/templates/{template_id}",
        json={
            "document_type_id": str(document_type.id),
            "name": "Updated Name",
            "html": "<p>{{cliente.nombre}}</p>",
        },
    )
    assert update_response.status_code == 401


def test_update_template_not_found(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    fake_id = "00000000-0000-0000-0000-000000000000"

    update_response = client.put(
        f"/api/content/templates/{fake_id}",
        json={
            "document_type_id": str(document_type.id),
            "name": "Updated Name",
            "html": "<p>{{cliente.nombre}}</p>",
        },
    )
    assert update_response.status_code == 404


def test_preview_template_success(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)
    response = client.post(
        "/api/content/templates/preview",
        json={
            "html": "<p>Hello, {{ cliente.nombre }}!</p>",
            "css": ".para { color: red; }",
            "mock_data": {"cliente": {"nombre": "Maria"}}
        }
    )
    assert response.status_code == 200
    assert response.json()["rendered_html"] == "<p>Hello, Maria!</p>"


def test_preview_template_invalid_jinja(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)
    response = client.post(
        "/api/content/templates/preview",
        json={
            "html": "<p>Hello, {% if cliente.nombre %}</p>",  # Missing endif
            "mock_data": {"cliente": {"nombre": "Maria"}}
        }
    )
    assert response.status_code == 400
    assert "Template rendering failed" in response.json()["detail"]

