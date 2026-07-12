import io
import os
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession
from pypdf import PdfWriter, PdfReader

from app.auth.session_service import create_session
from app.config import settings
from app.models.user import User
from app.models.document_type import DocumentType, DocumentTypeField, DocumentTypeMetadataDefinition
from app.models.document_design import DocumentDesign, DocumentDesignPage
from app.models.content_template import HtmlTemplate
from app.models.static_pdf_asset import StaticPdfAsset
from app.models.document_issuance import DocumentIssuance


def _auth_client(client: TestClient, db_session: SQLAlchemySession) -> User:
    user = User(sub="test-gen-sub", email="test-gen@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)
    return user


def _create_document_type(
    db_session: SQLAlchemySession,
    user: User,
    name: str = "TestDocType",
) -> DocumentType:
    document_type = DocumentType(
        name=name,
        description=f"{name} document type",
        created_by=user,
        fields=[
            DocumentTypeField(name="cliente.nombre", type="string", position=0),
            DocumentTypeField(name="cliente.edad", type="number", position=1),
            DocumentTypeField(name="fecha", type="date", position=2),
            DocumentTypeField(name="activo", type="boolean", position=3),
        ],
    )
    db_session.add(document_type)
    db_session.commit()
    db_session.refresh(document_type)
    return document_type


def _create_design(
    db_session: SQLAlchemySession,
    user: User,
    document_type: DocumentType,
    status: str = "active",
) -> DocumentDesign:
    design = DocumentDesign(
        document_type=document_type,
        name="Test Design",
        description="A design for testing generation",
        status=status,
        created_by=user,
        version_number=1,
        version_group_id=uuid.uuid4(),
    )
    db_session.add(design)
    db_session.commit()
    db_session.refresh(design)
    return design


def _create_template_page(
    db_session: SQLAlchemySession,
    user: User,
    design: DocumentDesign,
    html: str = "<h1>Hello {{ cliente.nombre }}</h1><p>Age: {{ cliente.edad }}</p><p>Date: {{ fecha | date_format }}</p>",
) -> HtmlTemplate:
    template = HtmlTemplate(
        document_type=design.document_type,
        name="Test Template",
        html=html,
        token_names=["cliente.nombre", "cliente.edad", "fecha"],
        created_by=user,
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    page = DocumentDesignPage(
        design=design,
        block_type="html_template",
        content_id=template.id,
        position=0,
        title="HTML Page",
        config={},
        snapshot={"name": template.name, "html": template.html, "token_names": template.token_names},
    )
    db_session.add(page)
    db_session.commit()
    return template


def _create_static_pdf_page(
    db_session: SQLAlchemySession,
    user: User,
    design: DocumentDesign,
    tmp_path: Path,
) -> StaticPdfAsset:
    pdf_file_path = tmp_path / "dummy_static.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)  # letter size
    with open(pdf_file_path, "wb") as f:
        writer.write(f)

    asset = StaticPdfAsset(
        original_filename="dummy_static.pdf",
        stored_filename="dummy_static.pdf",
        stored_path=str(pdf_file_path),
        page_count=1,
        file_size=pdf_file_path.stat().st_size,
        document_type=design.document_type,
        created_by=user,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    page = DocumentDesignPage(
        design=design,
        block_type="static_pdf",
        content_id=asset.id,
        position=1,
        title="Static PDF Page",
        config={},
        snapshot={"filename": asset.original_filename, "stored_path": asset.stored_path},
    )
    db_session.add(page)
    db_session.commit()
    return asset


def test_generate(client: TestClient, db_session: SQLAlchemySession, tmp_path: Path):
    user = _auth_client(client, db_session)
    doc_type = _create_document_type(db_session, user)
    design = _create_design(db_session, user, doc_type, status="active")
    _create_template_page(db_session, user, design)
    _create_static_pdf_page(db_session, user, design, tmp_path)

    payload = {
        "cliente.nombre": "John Doe",
        "cliente.edad": 42,
        "fecha": "2026-07-08",
        "activo": "true",
    }

    # Generate
    response = client.post(f"/api/document-designs/{design.id}/generate", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["design_version_id"] == str(design.id)
    assert data["user_id"] == str(user.id)
    assert data["input_data"] == payload
    assert "file_path" in data

    # Verify file exists on disk
    saved_path = Path(data["file_path"])
    assert saved_path.exists()
    assert saved_path.stat().st_size > 0

    # Read and verify PDF pages
    reader = PdfReader(saved_path)
    # 1 template page + 1 static pdf page = 2 pages total
    assert len(reader.pages) == 2

    # Verify database entry
    issuance = db_session.query(DocumentIssuance).filter(DocumentIssuance.id == data["id"]).first()
    assert issuance is not None
    assert issuance.design_version_id == design.id
    assert issuance.user_id == user.id

    # Clean up generated file
    if saved_path.exists():
        saved_path.unlink()


def test_generate_validation(client: TestClient, db_session: SQLAlchemySession, tmp_path: Path):
    user = _auth_client(client, db_session)
    doc_type = _create_document_type(db_session, user)

    # 1. Generate from a valid new draft design by activating it first
    draft_design = _create_design(db_session, user, doc_type, status="draft")
    draft_design.version_group_id = None
    draft_design.version_number = None
    db_session.commit()
    _create_template_page(db_session, user, draft_design)
    draft_payload = {
        "cliente.nombre": "Draft Doe",
        "cliente.edad": 29,
        "fecha": "2026-07-08",
        "activo": True,
    }
    response = client.post(f"/api/document-designs/{draft_design.id}/generate", json=draft_payload)
    assert response.status_code == 201
    db_session.refresh(draft_design)
    assert draft_design.status == "active"
    assert draft_design.version_group_id == draft_design.id
    assert draft_design.version_number == 1
    saved_path = Path(response.json()["file_path"])
    if saved_path.exists():
        saved_path.unlink()

    # Still reject drafts that cannot be activated
    empty_draft = _create_design(db_session, user, doc_type, status="draft")
    empty_draft.version_group_id = None
    empty_draft.version_number = None
    db_session.commit()
    response = client.post(f"/api/document-designs/{empty_draft.id}/generate", json=draft_payload)
    assert response.status_code == 400
    assert "at least one page" in response.json()["detail"]

    # 2. Allow active and superseded designs
    superseded_design = _create_design(db_session, user, doc_type, status="superseded")
    _create_template_page(db_session, user, superseded_design)

    payload = {
        "cliente.nombre": "Jane Doe",
        "cliente.edad": "30",
        "fecha": "2026-07-08",
        "activo": False,
    }

    # Superseded should generate successfully
    response = client.post(f"/api/document-designs/{superseded_design.id}/generate", json=payload)
    assert response.status_code == 201
    saved_path = Path(response.json()["file_path"])
    if saved_path.exists():
        saved_path.unlink()

    # 3. Missing fields in active generation (D-05) -> 400
    active_design = _create_design(db_session, user, doc_type, status="active")
    _create_template_page(db_session, user, active_design)
    
    bad_payload = {
        "cliente.nombre": "Jane Doe",
    }
    response = client.post(f"/api/document-designs/{active_design.id}/generate", json=bad_payload)
    assert response.status_code == 400
    assert "Missing required field" in response.json()["detail"]

    # 4. Bad format parsing / coercion errors (D-07, D-08) -> 400
    invalid_payload = {
        "cliente.nombre": "Jane Doe",
        "cliente.edad": "not-a-number",
        "fecha": "2026/07/08",
        "activo": "not-a-bool",
    }
    response = client.post(f"/api/document-designs/{active_design.id}/generate", json=invalid_payload)
    assert response.status_code == 400

    # 5. Extra fields in payload are strictly rejected (D-06) -> 400
    extra_payload = {
        "cliente.nombre": "Jane Doe",
        "cliente.edad": 35,
        "fecha": "2026-07-08",
        "activo": True,
        "ignored_extra_field": "some_value"
    }
    response = client.post(f"/api/document-designs/{active_design.id}/generate", json=extra_payload)
    assert response.status_code == 400
    assert "Unknown property" in response.text


def test_preview(client: TestClient, db_session: SQLAlchemySession):
    user = _auth_client(client, db_session)
    doc_type = _create_document_type(db_session, user)

    # 1. Preview draft design with missing fields (mock fallback checks)
    draft_design = _create_design(db_session, user, doc_type, status="draft")
    _create_template_page(db_session, user, draft_design)

    # Ensure empty storage folder or list existing files
    storage_root = Path(settings.issuance_storage_root)
    initial_files_count = 0
    if storage_root.exists():
        initial_files_count = len(list(storage_root.iterdir()))

    response = client.post(f"/api/document-designs/{draft_design.id}/preview", json={})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

    # Ensure no database records were created for issuance
    assert db_session.query(DocumentIssuance).count() == 0

    # Ensure no files were written to storage
    if storage_root.exists():
        assert len(list(storage_root.iterdir())) == initial_files_count

    # 2. Preview active design
    active_design = _create_design(db_session, user, doc_type, status="active")
    _create_template_page(db_session, user, active_design)
    response = client.post(f"/api/document-designs/{active_design.id}/preview", json={"cliente.nombre": "Preview Name"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

    # 3. Preview superseded design -> 400 Bad Request
    superseded_design = _create_design(db_session, user, doc_type, status="superseded")
    _create_template_page(db_session, user, superseded_design)
    response = client.post(f"/api/document-designs/{superseded_design.id}/preview", json={})
    assert response.status_code == 400
    assert "Preview only allowed for draft or active designs" in response.json()["detail"]


def test_download(client: TestClient, db_session: SQLAlchemySession, tmp_path: Path):
    user = _auth_client(client, db_session)
    doc_type = _create_document_type(db_session, user)
    design = _create_design(db_session, user, doc_type, status="active")
    _create_template_page(db_session, user, design)

    # 1. Generate an issuance
    payload = {
        "cliente.nombre": "Jane Download",
        "cliente.edad": 28,
        "fecha": "2026-07-08",
        "activo": True,
    }
    gen_response = client.post(f"/api/document-designs/{design.id}/generate", json=payload)
    assert gen_response.status_code == 201
    issuance_data = gen_response.json()
    issuance_id = issuance_data["id"]
    file_path = Path(issuance_data["file_path"])

    # 2. Download successfully
    download_response = client.get(f"/api/issuances/{issuance_id}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.content.startswith(b"%PDF")

    # 3. Download returns 404 for invalid/missing UUIDs
    missing_id = uuid.uuid4()
    bad_download = client.get(f"/api/issuances/{missing_id}/download")
    assert bad_download.status_code == 404

    # 4. Download returns 404 if file is deleted from disk
    if file_path.exists():
        file_path.unlink()
    
    missing_file_download = client.get(f"/api/issuances/{issuance_id}/download")
    assert missing_file_download.status_code == 404


def test_auth_gates(client: TestClient, db_session: SQLAlchemySession):
    design_id = uuid.uuid4()
    
    # 1. Generate without auth -> 401
    resp = client.post(f"/api/document-designs/{design_id}/generate", json={})
    assert resp.status_code == 401

    # 2. Preview without auth -> 401
    resp = client.post(f"/api/document-designs/{design_id}/preview", json={})
    assert resp.status_code == 401

    # 3. Download without auth -> 401
    issuance_id = uuid.uuid4()
    resp = client.get(f"/api/issuances/{issuance_id}/download")
    assert resp.status_code == 401


def test_metadata_validation_and_search(client: TestClient, db_session: SQLAlchemySession, tmp_path: Path):
    user = _auth_client(client, db_session)
    
    # Create DocumentType with metadata definitions
    doc_type = DocumentType(
        name="MetadataDocType",
        description="With metadata",
        created_by=user,
        fields=[
            DocumentTypeField(name="cliente.nombre", type="string", position=0),
            DocumentTypeField(name="cliente.edad", type="number", position=1),
            DocumentTypeField(name="fecha", type="date", position=2),
            DocumentTypeField(name="activo", type="boolean", position=3),
        ],
        metadata_definitions=[
            DocumentTypeMetadataDefinition(name="department", type="text", required=True),
            DocumentTypeMetadataDefinition(name="due_date", type="date", required=True),
            DocumentTypeMetadataDefinition(name="amount", type="number", required=False),
        ]
    )
    db_session.add(doc_type)
    db_session.commit()
    db_session.refresh(doc_type)
    
    design = _create_design(db_session, user, doc_type, status="active")
    _create_template_page(db_session, user, design)
    
    # 1. Valid generation
    payload = {
        "data": {
            "cliente.nombre": "Alice Test",
            "cliente.edad": 30,
            "fecha": "2026-07-08",
            "activo": True,
        },
        "metadata": {
            "department": "sales",
            "due_date": "2026-07-15",
            "amount": "123.45",
        }
    }
    
    response = client.post(f"/api/document-designs/{design.id}/generate", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "metadata_values" in data
    assert data["metadata_values"] == {
        "department": "sales",
        "due_date": "2026-07-15",
        "amount": 123.45,
    }
    
    saved_path = Path(data["file_path"])
    if saved_path.exists():
        saved_path.unlink()
        
    # 2. Missing required metadata field (department)
    invalid_payload_1 = {
        "data": payload["data"],
        "metadata": {
            "due_date": "2026-07-15"
        }
    }
    response = client.post(f"/api/document-designs/{design.id}/generate", json=invalid_payload_1)
    assert response.status_code == 400
    assert "Required metadata field 'department' is missing." in response.json()["detail"]
    
    # 3. Invalid metadata type (amount must be a number)
    invalid_payload_2 = {
        "data": payload["data"],
        "metadata": {
            "department": "sales",
            "due_date": "2026-07-15",
            "amount": "not-a-number"
        }
    }
    response = client.post(f"/api/document-designs/{design.id}/generate", json=invalid_payload_2)
    assert response.status_code == 400
    assert "Metadata field 'amount' must be a number." in response.json()["detail"]
    
    # 4. Search by metadata (valid department query)
    search_response = client.get("/api/issuances?metadata_key=department&metadata_value=sales")
    assert search_response.status_code == 200
    results = search_response.json()
    assert len(results) > 0
    assert results[0]["metadata_values"]["department"] == "sales"
    
    # 5. Search by metadata (non-matching query)
    search_response = client.get("/api/issuances?metadata_key=department&metadata_value=marketing")
    assert search_response.status_code == 200
    results = search_response.json()
    assert len(results) == 0
