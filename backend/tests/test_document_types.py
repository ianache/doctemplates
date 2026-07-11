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


def test_create_document_type_invalid_paths(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)
    
    # 1. Invalid regex patterns (empty segments, double brackets)
    for bad_name in ["cliente..nombre", "cliente.contactos[][].nombre", "cliente.", ".nombre", "cliente.contactos[].nombre[]"]:
        response = client.post(
            "/api/document-types",
            json={
                "name": "Invalid Path Schema",
                "fields": [
                    {"name": bad_name, "type": "string"}
                ],
            },
        )
        assert response.status_code == 422

    # 2. Depth limit exceeded (> 5 levels)
    response = client.post(
        "/api/document-types",
        json={
            "name": "Deep Schema",
            "fields": [
                {"name": "a.b.c.d.e.f", "type": "string"}
            ],
        },
    )
    assert response.status_code == 422
    assert "Field path depth cannot exceed 5 levels" in response.text


def test_create_document_type_structural_conflicts(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)

    # Conflict: leaf/parent mismatch (cliente is both leaf and object parent)
    response = client.post(
        "/api/document-types",
        json={
            "name": "Leaf Parent Conflict Schema",
            "fields": [
                {"name": "cliente", "type": "string"},
                {"name": "cliente.nombre", "type": "string"}
            ],
        },
    )
    assert response.status_code == 422
    assert "declared as both an object and a non-object/leaf" in response.text

    # Conflict: list/object mismatch (contactos is object parent in one, list parent in another)
    response = client.post(
        "/api/document-types",
        json={
            "name": "List Object Conflict Schema",
            "fields": [
                {"name": "cliente.contactos.nombre", "type": "string"},
                {"name": "cliente.contactos[].nombre", "type": "string"}
            ],
        },
    )
    assert response.status_code == 422
    assert "declared as both a list and a non-list" in response.text

    # Conflict: duplicate names case-insensitively
    response = client.post(
        "/api/document-types",
        json={
            "name": "Case Duplication Conflict Schema",
            "fields": [
                {"name": "cliente.Nombre", "type": "string"},
                {"name": "cliente.nombre", "type": "string"}
            ],
        },
    )
    assert response.status_code == 422
    assert "Field names must be unique within a document type" in response.text


def test_create_document_type_valid_nested(client: TestClient, db_session: SQLAlchemySession) -> None:
    _auth_client(client, db_session)

    response = client.post(
        "/api/document-types",
        json={
            "name": "Valid Nested Schema",
            "fields": [
                {"name": "cliente.direccion.calle", "type": "string"},
                {"name": "cliente.contactos[].nombre", "type": "string"},
                {"name": "cliente.contactos[].edad", "type": "number"}
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert len(body["fields"]) == 3


def test_update_document_type(client: TestClient, db_session: SQLAlchemySession) -> None:
    user = _auth_client(client, db_session)
    
    # 1. Create a Document Type
    create_resp = client.post(
        "/api/document-types",
        json={
            "name": "Original Name",
            "description": "Original description",
            "fields": [
                {"name": "field1", "type": "string"},
            ],
            "metadata_definitions": [
                {"name": "meta1", "type": "text", "required": True}
            ]
        },
    )
    assert create_resp.status_code == 201
    dt_id = create_resp.json()["id"]
    
    # 2. Update it
    update_resp = client.put(
        f"/api/document-types/{dt_id}",
        json={
            "name": "Updated Name",
            "description": "Updated description",
            "fields": [
                {"name": "field2", "type": "number"},
                {"name": "field3", "type": "boolean"},
            ],
            "metadata_definitions": [
                {"name": "meta2", "type": "number", "required": False}
            ]
        }
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["name"] == "Updated Name"
    assert body["description"] == "Updated description"
    assert len(body["fields"]) == 2
    assert body["fields"][0]["name"] == "field2"
    assert body["fields"][0]["type"] == "number"
    assert len(body["metadata_definitions"]) == 1
    assert body["metadata_definitions"][0]["name"] == "meta2"
    assert body["metadata_definitions"][0]["type"] == "number"
    assert body["metadata_definitions"][0]["required"] is False
    
    # 3. Verify in DB
    dt = db_session.query(DocumentType).filter(DocumentType.id == dt_id).first()
    assert dt is not None
    assert dt.name == "Updated Name"
    assert len(dt.fields) == 2
    assert len(dt.metadata_definitions) == 1

