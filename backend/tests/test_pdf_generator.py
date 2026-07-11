import pytest
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.user import User
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.models.content_template import HtmlTemplate
from app.models.static_pdf_asset import StaticPdfAsset
from app.services.pdf_generator import (
    coerce_value,
    validate_and_coerce_payload,
    expand_flat_dict,
    render_html_page_to_pdf,
    generate_composed_pdf,
)


def test_coerce_value():
    # String coercion
    assert coerce_value("hello", "string", "test") == "hello"
    assert coerce_value(123, "string", "test") == "123"
    assert coerce_value(True, "string", "test") == "True"
    with pytest.raises(ValueError):
        coerce_value({"a": 1}, "string", "test")

    # Number coercion
    assert coerce_value(123, "number", "test") == 123
    assert coerce_value(12.34, "number", "test") == 12.34
    assert coerce_value("123.45", "number", "test") == 123.45
    assert coerce_value("100", "number", "test") == 100
    with pytest.raises(ValueError):
        coerce_value("abc", "number", "test")

    # Boolean coercion
    assert coerce_value(True, "boolean", "test") is True
    assert coerce_value(False, "boolean", "test") is False
    assert coerce_value(1, "boolean", "test") is True
    assert coerce_value(0, "boolean", "test") is False
    assert coerce_value("true", "boolean", "test") is True
    assert coerce_value("no", "boolean", "test") is False
    with pytest.raises(ValueError):
        coerce_value("maybe", "boolean", "test")

    # Date coercion
    assert coerce_value("2026-07-08", "date", "test") == "2026-07-08"
    with pytest.raises(ValueError):
        coerce_value("2026/07/08", "date", "test")
    with pytest.raises(ValueError):
        coerce_value(12345, "date", "test")


def test_expand_flat_dict():
    flat = {
        "cliente.nombre": "Juan",
        "cliente.detalles.edad": 30,
        "config.es_activo": True,
        "simple": "value",
    }
    expanded = expand_flat_dict(flat)
    assert expanded == {
        "cliente": {
            "nombre": "Juan",
            "detalles": {"edad": 30},
        },
        "config": {
            "es_activo": True,
        },
        "simple": "value",
    }


def test_validate_and_coerce_payload():
    fields = [
        DocumentTypeField(name="cliente.nombre", type="string", position=0),
        DocumentTypeField(name="cliente.edad", type="number", position=1),
        DocumentTypeField(name="es_premium", type="boolean", position=2),
        DocumentTypeField(name="fecha_registro", type="date", position=3),
    ]

    # Valid payload
    payload = {
        "cliente.nombre": "Alice",
        "cliente.edad": "25.5",
        "es_premium": "yes",
        "fecha_registro": "2026-01-01",
    }
    res = validate_and_coerce_payload(payload, fields, mock_fallback=False)
    assert res == {
        "cliente": {
            "nombre": "Alice",
            "edad": 25.5,
        },
        "es_premium": True,
        "fecha_registro": "2026-01-01",
    }

    # Unknown property rejection (D-06)
    bad_payload_extra = {
        "cliente.nombre": "Alice",
        "cliente.edad": "25.5",
        "es_premium": "yes",
        "fecha_registro": "2026-01-01",
        "extra_field": "ignore me",
    }
    with pytest.raises(HTTPException) as exc_info:
        validate_and_coerce_payload(bad_payload_extra, fields, mock_fallback=False)
    assert exc_info.value.status_code == 400
    assert "Unknown property" in str(exc_info.value.detail)

    # Missing fields without fallback -> 400
    bad_payload = {
        "cliente.nombre": "Alice",
    }
    with pytest.raises(HTTPException) as exc_info:
        validate_and_coerce_payload(bad_payload, fields, mock_fallback=False)
    assert exc_info.value.status_code == 400

    # Missing fields with fallback -> mock values generated
    mock_res = validate_and_coerce_payload(bad_payload, fields, mock_fallback=True)
    assert mock_res["cliente"]["nombre"] == "Alice"
    assert mock_res["cliente"]["edad"] == 123.45
    assert mock_res["es_premium"] is True
    assert len(mock_res["fecha_registro"]) == 10  # YYYY-MM-DD

    # Case-insensitive key collisions (D-03/D-04)
    collision_payload = {
        "invoice": {
            "Num": "123",
            "num": "456"
        }
    }
    collision_fields = [
        DocumentTypeField(name="invoice.num", type="string", position=0)
    ]
    with pytest.raises(HTTPException) as exc_info:
        validate_and_coerce_payload(collision_payload, collision_fields, mock_fallback=False)
    assert exc_info.value.status_code == 400
    details = exc_info.value.detail
    assert isinstance(details, list)
    assert details[0]["type"] == "casing_collision"
    assert details[0]["loc"] == ["invoice", "Num"]

    # Permissive lists (D-05) - list field is defined in schema but omitted from payload
    list_fields = [
        DocumentTypeField(name="cliente.contactos[].nombre", type="string", position=0)
    ]
    list_payload = {
        "cliente": {}
    }
    res_list = validate_and_coerce_payload(list_payload, list_fields, mock_fallback=False)
    assert res_list == {
        "cliente": {
            "contactos": []
        }
    }


def test_render_html_page_to_pdf():
    html_content = "<h1>Hello {{ user.name }}</h1><p>Date: {{ date_val | date_format }}</p>"
    context = {
        "user": {"name": "Charlie"},
        "date_val": "2026-07-08",
    }
    pdf_bytes = render_html_page_to_pdf(html_content, context)
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_composed_pdf(db_session: SQLAlchemySession):
    # Setup test models in DB
    user = User(sub="gen-sub", email="gen@example.com")
    db_session.add(user)
    db_session.commit()

    doc_type = DocumentType(name="Invoices", created_by_id=user.id)
    db_session.add(doc_type)
    db_session.commit()

    f1 = DocumentTypeField(document_type_id=doc_type.id, name="invoice.num", type="string", position=0)
    f2 = DocumentTypeField(document_type_id=doc_type.id, name="invoice.date", type="date", position=1)
    db_session.add_all([f1, f2])
    db_session.commit()

    design = DocumentDesign(
        document_type_id=doc_type.id,
        name="Invoice Template",
        created_by_id=user.id,
        status="active",
    )
    db_session.add(design)
    db_session.commit()

    template = HtmlTemplate(
        name="Invoice Template",
        html="<h1>Invoice #{{ invoice.num }}</h1><p>Date: {{ invoice.date | date_format }}</p>",
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

    payload = {
        "invoice.num": "INV-100",
        "invoice.date": "2026-07-08",
    }

    pdf_bytes = generate_composed_pdf(design, payload, db_session)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_html_page_with_css():
    html_content = "<h1 class='styled-title'>Hello</h1>"
    context = {}
    css_content = ".styled-title { color: red; font-size: 24pt; }"
    pdf_bytes = render_html_page_to_pdf(html_content, context, css_content)
    assert pdf_bytes.startswith(b"%PDF")
