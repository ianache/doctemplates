from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="doc-types-sub", email="doc-types@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def test_create_document_type(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)
    response = client.post(
        "/api/document-types",
        json={
            "name": "Vehicle Insurance Contract",
            "description": "Fleet/basic insurance contract",
            "fields": [
                {"name": "cliente.nombre", "type": "string", "description": "Customer name"},
                {"name": "cliente.edad", "type": "number", "description": "Customer age"},
                {"name": "servicio.es_flota", "type": "boolean", "description": "Fleet flag"},
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Vehicle Insurance Contract"
    assert body["description"] == "Fleet/basic insurance contract"
    assert body["created_by_email"] == "doc-types@example.com"
    assert [field["name"] for field in body["fields"]] == [
        "cliente.nombre",
        "cliente.edad",
        "servicio.es_flota",
    ]
    assert [field["type"] for field in body["fields"]] == ["string", "number", "boolean"]
    assert [field["description"] for field in body["fields"]] == [
        "Customer name",
        "Customer age",
        "Fleet flag",
    ]

    document_type = db_session.query(DocumentType).one()
    assert document_type.name == "Vehicle Insurance Contract"
    assert [field.position for field in document_type.fields] == [0, 1, 2]


def test_create_rejects_duplicate_field_names(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    _auth_client(client, db_session)
    response = client.post(
        "/api/document-types",
        json={
            "name": "Broken Contract",
            "description": None,
            "fields": [
                {"name": "cliente.nombre", "type": "string", "description": ""},
                {"name": "cliente.nombre", "type": "number", "description": ""},
            ],
        },
    )

    assert response.status_code == 422
    assert "Field names must be unique within a document type" in response.text


def test_create_rejects_invalid_field_type(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    _auth_client(client, db_session)
    response = client.post(
        "/api/document-types",
        json={
            "name": "Broken Type",
            "description": None,
            "fields": [
                {"name": "cliente.nombre", "type": "image", "description": ""},
            ],
        },
    )

    assert response.status_code == 422


def test_create_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/document-types",
        json={
            "name": "No Auth",
            "description": None,
            "fields": [{"name": "cliente.nombre", "type": "string", "description": ""}],
        },
    )

    assert response.status_code == 401


def test_list_document_types(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    document_type = DocumentType(
        name="Policy",
        description="Policy doc",
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

    response = client.get("/api/document-types")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Policy"
    assert body[0]["field_count"] == 2
    assert body[0]["created_by_email"] == "doc-types@example.com"


def test_get_document_type_detail(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    document_type = DocumentType(
        name="Detail Policy",
        description="Detail doc",
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

    response = client.get(f"/api/document-types/{document_type.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Detail Policy"
    assert body["fields"][0]["name"] == "cliente.nombre"
    assert body["fields"][0]["type"] == "string"


def test_get_document_type_not_found(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)
    response = client.get("/api/document-types/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
