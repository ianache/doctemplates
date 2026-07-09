import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession
from fastapi import HTTPException

from app.auth.session_service import create_session
from app.models.user import User
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.models.content_template import HtmlTemplate
from app.models.document_issuance import DocumentIssuance
from app.services.pdf_generator import (
    validate_and_coerce_payload,
    generate_composed_pdf,
    RecursiveCaseInsensitiveDict,
    RecursiveCaseInsensitiveList,
)


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="nested-sub", email="nested@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def test_nested_case_insensitive_pdf_generation(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)

    # 1. Create DocumentType with nested & list structure
    doc_type = DocumentType(name="Nested Invoice", created_by_id=user.id)
    db_session.add(doc_type)
    db_session.commit()

    f1 = DocumentTypeField(document_type_id=doc_type.id, name="cliente.direccion.calle", type="string", position=0)
    f2 = DocumentTypeField(document_type_id=doc_type.id, name="cliente.contactos[].nombre", type="string", position=1)
    f3 = DocumentTypeField(document_type_id=doc_type.id, name="cliente.contactos[].edad", type="number", position=2)
    db_session.add_all([f1, f2, f3])
    db_session.commit()

    # 2. Create design
    design = DocumentDesign(
        document_type_id=doc_type.id,
        name="Invoice Design",
        created_by_id=user.id,
        status="active",
    )
    db_session.add(design)
    db_session.commit()

    # 3. Create template referencing fields case-insensitively and fallback
    html = """
    Calle: {{ CLIENTE.direccion.Calle }}
    Contactos:
    {% for c in Cliente.Contactos %}
      - {{ c.Nombre }} ({{ c.Edad }})
    {% endfor %}
    """
    template = HtmlTemplate(
        name="Nested Template",
        html=html,
        document_type_id=doc_type.id,
        created_by_id=user.id,
    )
    db_session.add(template)
    db_session.commit()

    page = DocumentDesignPage(
        design_id=design.id,
        block_type="html_template",
        content_id=template.id,
        position=0,
    )
    db_session.add(page)
    db_session.commit()

    # 4. Generate composed PDF with mixed casing in payload keys
    payload = {
        "CLIENTE": {
            "direccion": {
                "Calle": "Avenida 1"
            },
            "Contactos": [
                {"Nombre": "Juan", "Edad": "35"},
                {"nombre": "Maria", "edad": 28}
            ]
        }
    }

    # Verify generate succeeds and preserves exact casing in database record input_data
    response = client.post(
        f"/api/document-designs/{design.id}/generate",
        json=payload
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None

    # Load issuance from database and verify raw payload casing is preserved exactly
    issuance = db_session.query(DocumentIssuance).filter(DocumentIssuance.id == body["id"]).one()
    assert issuance.input_data == payload
    # Verify exact casing keys are present
    assert "CLIENTE" in issuance.input_data
    assert "Calle" in issuance.input_data["CLIENTE"]["direccion"]
    assert "Nombre" in issuance.input_data["CLIENTE"]["Contactos"][0]

    # Verify rendering completes without errors (generating composed pdf from helper directly)
    pdf_bytes = generate_composed_pdf(design, payload, db_session)
    assert pdf_bytes.startswith(b"%PDF")


def test_private_attribute_protection() -> None:
    # Verify proxy dictionary blocks access to private attributes (T-02)
    d = RecursiveCaseInsensitiveDict({"a": 1, "nested": {"b": 2}})
    
    with pytest.raises(AttributeError):
        _ = d.__class__
        
    with pytest.raises(AttributeError):
        _ = d.__dict__

    with pytest.raises(KeyError):
        _ = d["__class__"]

    # Verify proxy list blocks access to private attributes
    l = RecursiveCaseInsensitiveList([1, 2, {"c": 3}])
    
    with pytest.raises(AttributeError):
        _ = l.__class__

    with pytest.raises(AttributeError):
        _ = l.__dict__
