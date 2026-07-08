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

    # Deleting a page on an active design must be blocked (returns 400)
    delete_response = client.delete(f"/api/document-designs/{design['id']}/pages/{page['id']}")
    assert delete_response.status_code == 400

    # Verify we can delete a page on a draft design (returns 204)
    draft_page_response = client.post(
        f"/api/document-designs/{empty_design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    assert draft_page_response.status_code == 201
    draft_page = draft_page_response.json()
    delete_response = client.delete(f"/api/document-designs/{empty_design['id']}/pages/{draft_page['id']}")
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


def test_first_activation_becomes_version_1(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    design = _create_design(client, document_type)

    # Add a page so it can be activated
    page_response = client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    assert page_response.status_code == 201

    # First activation
    activate_response = client.post(f"/api/document-designs/{design['id']}/activate")
    assert activate_response.status_code == 200
    activated = activate_response.json()
    assert activated["status"] == "active"
    assert activated["version_group_id"] == design["id"]
    assert activated["version_number"] == 1


def test_fork_clones_pages_without_mutating_current(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    design = _create_design(client, document_type)

    client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id), "title": "Original Page"},
    )
    client.post(f"/api/document-designs/{design['id']}/activate")

    # Fork a new draft from the active design
    fork_response = client.post(f"/api/document-designs/{design['id']}/versions")
    assert fork_response.status_code == 201
    draft = fork_response.json()
    assert draft["status"] == "draft"
    assert draft["version_group_id"] == design["id"]
    assert draft["version_number"] == 2
    assert len(draft["pages"]) == 1
    assert draft["pages"][0]["title"] == "Original Page"

    # Modify the draft page (should work since it's draft)
    draft_page_id = draft["pages"][0]["id"]
    update_response = client.patch(
        f"/api/document-designs/{draft['id']}/pages/{draft_page_id}",
        json={"title": "Modified Page"},
    )
    assert update_response.status_code == 200

    # Current/Active version page must remain untouched
    current = client.get(f"/api/document-designs/{design['id']}").json()
    assert current["pages"][0]["title"] == "Original Page"
    
    # Try modifying current version page (should be blocked)
    current_page_id = current["pages"][0]["id"]
    blocked_update = client.patch(
        f"/api/document-designs/{design['id']}/pages/{current_page_id}",
        json={"title": "Mutated Current Page"},
    )
    assert blocked_update.status_code == 400


def test_activate_draft_supersedes_old_current(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    design = _create_design(client, document_type)

    client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    client.post(f"/api/document-designs/{design['id']}/activate")

    # Fork
    fork_response = client.post(f"/api/document-designs/{design['id']}/versions")
    draft = fork_response.json()

    # Activate draft
    activate_response = client.post(f"/api/document-designs/{draft['id']}/activate")
    assert activate_response.status_code == 200
    new_active = activate_response.json()
    assert new_active["status"] == "active"
    assert new_active["version_number"] == 2

    # Check that original is now superseded
    original = client.get(f"/api/document-designs/{design['id']}").json()
    assert original["status"] == "superseded"


def test_fork_resumes_existing_draft(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    design = _create_design(client, document_type)

    client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    client.post(f"/api/document-designs/{design['id']}/activate")

    # Fork once
    fork_1 = client.post(f"/api/document-designs/{design['id']}/versions").json()
    # Fork again (should return same draft instead of creating a new one)
    fork_2 = client.post(f"/api/document-designs/{design['id']}/versions").json()
    assert fork_1["id"] == fork_2["id"]


def test_version_history_newest_first_includes_draft(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    design = _create_design(client, document_type)

    client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    client.post(f"/api/document-designs/{design['id']}/activate")

    # Version 2
    v2_draft = client.post(f"/api/document-designs/{design['id']}/versions").json()
    client.post(f"/api/document-designs/{v2_draft['id']}/activate")

    # Version 3 Draft (forked from the current active version)
    v3_draft = client.post(f"/api/document-designs/{v2_draft['id']}/versions").json()

    # Get history
    history_response = client.get(f"/api/document-designs/{design['id']}/versions")
    assert history_response.status_code == 200
    history = history_response.json()
    
    # 3 versions: v3 draft (draft), v2 active (active), v1 original (superseded)
    assert len(history) == 3
    assert history[0]["id"] == v3_draft["id"]
    assert history[0]["status"] == "draft"
    assert history[0]["version_number"] == 3

    assert history[1]["id"] == v2_draft["id"]
    assert history[1]["status"] == "active"
    assert history[1]["version_number"] == 2

    assert history[2]["id"] == design["id"]
    assert history[2]["status"] == "superseded"
    assert history[2]["version_number"] == 1


def test_discard_draft_leaves_current_intact(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    template = _create_template(db_session, user, document_type)
    design = _create_design(client, document_type)

    client.post(
        f"/api/document-designs/{design['id']}/pages/template",
        json={"template_id": str(template.id)},
    )
    client.post(f"/api/document-designs/{design['id']}/activate")

    # Create draft
    draft = client.post(f"/api/document-designs/{design['id']}/versions").json()

    # Discard draft
    discard_response = client.delete(f"/api/document-designs/{draft['id']}")
    assert discard_response.status_code == 204

    # Verify draft is gone (should return 404)
    get_draft = client.get(f"/api/document-designs/{draft['id']}")
    assert get_draft.status_code == 404

    # Current remains active and intact
    current = client.get(f"/api/document-designs/{design['id']}").json()
    assert current["status"] == "active"
    assert len(current["pages"]) == 1


def test_migration_backfill_d05(
    client: TestClient, db_session: SQLAlchemySession
) -> None:
    import sqlalchemy as sa
    user = _auth_client(client, db_session)
    document_type = _create_document_type(db_session, user)
    
    # We will manually construct designs in pre-Phase-5 states in DB
    from app.models.document_design import DocumentDesign

    # 1. An active design with NULL versioning info (pre-Phase-5)
    legacy_active = DocumentDesign(
        document_type_id=document_type.id,
        name="Legacy Active",
        status="active",
        created_by_id=user.id,
        version_group_id=None,
        version_number=None,
    )
    # 2. A draft design with NULL versioning info (pre-Phase-5)
    legacy_draft = DocumentDesign(
        document_type_id=document_type.id,
        name="Legacy Draft",
        status="draft",
        created_by_id=user.id,
        version_group_id=None,
        version_number=None,
    )
    db_session.add_all([legacy_active, legacy_draft])
    db_session.commit()

    # Let's run the backfill logic manually (same as migration)
    db_session.execute(
        sa.text(
            "UPDATE document_designs SET version_group_id = id, version_number = 1 "
            "WHERE status = 'active' AND version_group_id IS NULL"
        )
    )
    db_session.commit()
    db_session.refresh(legacy_active)
    db_session.refresh(legacy_draft)

    # Legacy active must become Version 1
    assert legacy_active.version_group_id == legacy_active.id
    assert legacy_active.version_number == 1

    # Legacy draft remains version-less (NULL)
    assert legacy_draft.version_group_id is None
    assert legacy_draft.version_number is None
