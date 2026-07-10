import pytest
import jinja2
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.services.content_validation import (
    JinjaTokenExtractor,
    get_ancestor_paths,
    validate_template_tokens,
    extract_template_tokens_ast_warnings,
)
from app.services.design_validation import get_design_warnings
from app.models.user import User
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.content_template import HtmlTemplate
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.auth.session_service import create_session


def test_jinja_token_extractor_loops_and_nesting():
    env = jinja2.Environment()
    
    # Loop destructuring and nesting
    html = "{% for key, val in dict.items() %}{{ val.name }}{% endfor %}"
    parsed = env.parse(html)
    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)
    # val is bound to None (local variable), so val.name resolves to None and isn't extracted
    assert "val.name" not in extractor.extracted_tokens

    # Standard loop mapping to schema
    html = "{% for item in cliente.contactos %}{{ item.nombre }} and {{ item.telefono }}{% endfor %}"
    parsed = env.parse(html)
    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)
    assert "cliente.contactos" in extractor.extracted_tokens
    assert "cliente.contactos[].nombre" in extractor.extracted_tokens
    assert "cliente.contactos[].telefono" in extractor.extracted_tokens
    assert "cliente" not in extractor.extracted_tokens
    assert "cliente.contactos[]" not in extractor.extracted_tokens

    # Local assignments (set)
    html = "{% set alias = cliente %}{{ alias.nombre }}"
    parsed = env.parse(html)
    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)
    assert "cliente" in extractor.extracted_tokens
    assert "cliente.nombre" in extractor.extracted_tokens
    assert "alias" not in extractor.extracted_tokens
    assert "alias.nombre" not in extractor.extracted_tokens

    # Attribute method calls vs variable access
    html = "{{ cliente.nombre.upper() }} and {{ cliente.edad.strftime('%Y') }}"
    parsed = env.parse(html)
    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)
    assert "cliente.nombre" in extractor.extracted_tokens
    assert "cliente.edad" in extractor.extracted_tokens
    assert "cliente.nombre.upper" not in extractor.extracted_tokens
    assert "cliente.edad.strftime" not in extractor.extracted_tokens

    # Getitem normalization
    html = "{{ contacts[0] }} and {{ contacts['first'] }}"
    parsed = env.parse(html)
    extractor = JinjaTokenExtractor()
    extractor.visit(parsed)
    assert "contacts[]" in extractor.extracted_tokens
    assert "contacts.first" in extractor.extracted_tokens


def test_case_insensitive_globals_bypass():
    allowed = ["cliente.nombre"]
    
    # range(10) is standard global, should bypass validation
    res1 = validate_template_tokens("{{ range(10) }} {{ cliente.nombre }}", allowed)
    assert "cliente.nombre" in res1

    # RANGE(10) is case-insensitive match for global range, should bypass validation
    res2 = validate_template_tokens("{{ RANGE(10) }} {{ cliente.nombre }}", allowed)
    assert "cliente.nombre" in res2


def test_ancestor_paths_helper():
    paths = get_ancestor_paths("cliente.contactos[].nombre")
    expected = {
        "cliente",
        "cliente[]",
        "cliente.contactos",
        "cliente.contactos[]",
        "cliente.contactos[].nombre",
        "cliente.contactos[].nombre[]",
    }
    assert paths == expected


def _setup_test_data(db_session: SQLAlchemySession, client: TestClient):
    user = User(sub="test-sub", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)

    doc_type = DocumentType(
        name="Invoice",
        description="Invoice type",
        created_by=user,
        fields=[
            DocumentTypeField(name="cliente.nombre", type="string", description="Name", position=0),
            DocumentTypeField(name="cliente.contactos[].nombre", type="string", description="Contact Name", position=1),
            DocumentTypeField(name="cliente.contactos[].telefono", type="string", description="Contact Phone", position=2),
        ]
    )
    db_session.add(doc_type)
    db_session.commit()
    db_session.refresh(doc_type)

    return user, doc_type


def test_draft_design_warnings(db_session: SQLAlchemySession, client: TestClient):
    user, doc_type = _setup_test_data(db_session, client)

    # Create design
    design_resp = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(doc_type.id),
            "name": "Draft Design with Warnings",
            "description": "A draft design test"
        }
    )
    assert design_resp.status_code == 201
    design_data = design_resp.json()
    design_id = design_data["id"]
    assert "warnings" in design_data
    assert design_data["warnings"] == []

    # Create template with undeclared token/field bypassing api
    template = HtmlTemplate(
        document_type=doc_type,
        name="Bad Template",
        html="<p>{{ cliente.invalid_field }}</p>",
        token_names=["cliente.invalid_field"],
        created_by=user
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    # Add page to design via endpoint
    page_resp = client.post(
        f"/api/document-designs/{design_id}/pages/template",
        json={
            "template_id": str(template.id),
            "title": "Page with Warning",
        }
    )
    assert page_resp.status_code == 201

    # Get design detail: it should return the warnings
    detail_resp = client.get(f"/api/document-designs/{design_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["warnings"]) > 0
    assert "Token 'cliente.invalid_field' is not declared in schema" in detail_data["warnings"]


def test_design_activation_gates(db_session: SQLAlchemySession, client: TestClient):
    user, doc_type = _setup_test_data(db_session, client)

    # Create a template that is valid (contains valid nested loop wildcard variables)
    valid_html = """
    <h1>Invoice</h1>
    <p>{{ cliente.nombre }}</p>
    {% for c in cliente.contactos %}
      <p>{{ c.nombre }} - {{ c.telefono }}</p>
    {% endfor %}
    """
    valid_template = HtmlTemplate(
        document_type=doc_type,
        name="Valid Template",
        html=valid_html,
        token_names=["cliente.nombre", "cliente.contactos[].nombre", "cliente.contactos[].telefono"],
        created_by=user
    )
    db_session.add(valid_template)
    db_session.commit()

    # Create design
    design_resp = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(doc_type.id),
            "name": "Valid Design",
        }
    )
    assert design_resp.status_code == 201
    design_id = design_resp.json()["id"]

    # Add the valid page to it
    page_resp = client.post(
        f"/api/document-designs/{design_id}/pages/template",
        json={"template_id": str(valid_template.id)}
    )
    assert page_resp.status_code == 201

    # Activating this design should succeed
    activate_resp = client.post(f"/api/document-designs/{design_id}/activate")
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "active"

    # Create a template that is invalid
    invalid_template = HtmlTemplate(
        document_type=doc_type,
        name="Invalid Template",
        html="<p>{{ cliente.invalid_field }}</p>",
        token_names=["cliente.invalid_field"],
        created_by=user
    )
    db_session.add(invalid_template)
    db_session.commit()

    # Create another design
    design_resp2 = client.post(
        "/api/document-designs",
        json={
            "document_type_id": str(doc_type.id),
            "name": "Invalid Design",
        }
    )
    design_id2 = design_resp2.json()["id"]

    # Add the invalid page
    client.post(
        f"/api/document-designs/{design_id2}/pages/template",
        json={"template_id": str(invalid_template.id)}
    )

    # Activating this design should fail strictly with 400 Bad Request
    activate_resp2 = client.post(f"/api/document-designs/{design_id2}/activate")
    assert activate_resp2.status_code == 400
    assert "Invalid template tokens: cliente.invalid_field" in activate_resp2.json()["detail"]
