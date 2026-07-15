import uuid
from datetime import datetime
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLAlchemySession

from app.auth.session_service import create_session
from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers


# Keep collection independent of LiteLLM's Windows OpenSSL import path.
litellm_stub = ModuleType("litellm")
litellm_stub.completion = lambda **kwargs: None
sys.modules["litellm"] = litellm_stub

from app.services.template_ai_agent import TemplateAiAgent, TemplateAiProposalResult


@pytest.fixture
def user(db_session):
    value = User(sub="template-ai-test", email="template-ai@example.com")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


def _auth_client(client: TestClient, db_session: SQLAlchemySession, user: User) -> None:
    session = create_session(db_session, user)
    client.cookies.set("docmanagement_session", session.id)


def test_template_ai_proposal_persists_full_history(db_session, user):
    document_type = DocumentType(name="Invoice", description="Invoice document", created_by=user)
    template = HtmlTemplate(
        document_type=document_type,
        name="Invoice base",
        html="<p>{{ customer.name }}</p>",
        css="p { color: black; }",
        token_names=["customer.name"],
        created_by=user,
        mock_data={"customer": {"name": "Ada"}},
    )
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it more formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Added a section wrapper and spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )

    db_session.add(proposal)
    db_session.commit()

    saved = db_session.get(HtmlTemplateAiProposal, proposal.id)
    assert saved is not None
    assert isinstance(saved.id, uuid.UUID)
    assert saved.template_id == template.id
    assert saved.created_by_id == user.id
    assert saved.status == "valid"
    assert saved.validation_errors == []
    assert saved.is_applyable is True
    assert saved.applied_at is None


def test_extract_jinja_markers_includes_expressions_and_statements():
    html = """
    <h1>{{ customer.name }}</h1>
    {% for item in items %}
      <p>{{ item.total | date_format }}</p>
    {% endfor %}
    """

    markers = extract_jinja_markers(html)

    assert "{{ customer.name }}" in markers
    assert "{% for item in items %}" in markers
    assert "{{ item.total | date_format }}" in markers
    assert "{% endfor %}" in markers


def test_validate_preserved_jinja_markers_reports_removed_marker():
    original = "<p>{{ customer.name }}</p>{% for item in items %}{{ item.total }}{% endfor %}"
    proposed = "<p>{{ customer.name }}</p>"

    errors = validate_preserved_jinja_markers(original, proposed)

    assert "Missing preserved Jinja marker: {% for item in items %}" in errors
    assert "Missing preserved Jinja marker: {{ item.total }}" in errors
    assert "Missing preserved Jinja marker: {% endfor %}" in errors


def test_template_ai_agent_returns_applyable_result_for_valid_response(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<section><p>{{ customer.name }}</p></section>","css":"section { padding: 24px; }","summary":"Improved spacing."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Make it more formal",
        current_html="<p>{{ customer.name }}</p>",
        current_css="p { color: black; }",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "valid"
    assert result.is_applyable is True
    assert result.validation_errors == []
    assert result.proposed_html == "<section><p>{{ customer.name }}</p></section>"
    assert result.proposed_css == "section { padding: 24px; }"


def test_template_ai_agent_blocks_removed_existing_token(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<section>No token</section>","css":"","summary":"Removed token."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert "Missing preserved Jinja marker: {{ customer.name }}" in result.validation_errors


def test_template_ai_agent_blocks_script_tags(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<script>alert(1)</script><p>{{ customer.name }}</p>","css":"","summary":"Unsafe."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert "Generated HTML cannot include <script> tags." in result.validation_errors


def test_template_ai_agent_reports_failed_invalid_json(monkeypatch):
    def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "not json"}}]}

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent(
        model="gpt-4o-mini",
        enabled=True,
        timeout_seconds=30,
        max_input_chars=20000,
        max_output_tokens=2000,
    )

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert any("valid JSON" in error for error in result.validation_errors)


def test_template_ai_agent_blocks_removed_duplicate_jinja_marker(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<p>{{ customer.name }}</p>","css":"","summary":"Removed one marker."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p><p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert any("{{ customer.name }}" in error for error in result.validation_errors)


def test_template_ai_agent_blocks_jinja_marker_spacing_rewrite(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<p>{{customer.name}}</p>","css":"","summary":"Changed spacing."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert any("{{ customer.name }}" in error for error in result.validation_errors)


def test_template_ai_agent_blocks_jinja_marker_rewrite_with_closing_delimiter_in_string(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"<p>{{ \'}}\' | upper }}</p>","css":"","summary":"Changed expression."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ '}}' }}</p>",
        current_css="",
        document_fields=[],
        mock_data={},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert "Missing preserved Jinja marker: {{ '}}' }}" in result.validation_errors


def test_template_ai_agent_fails_when_provider_returns_json_array(monkeypatch):
    def fake_completion(**kwargs):
        return {"choices": [{"message": {"content": "[]"}}]}

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert result.validation_errors


def test_template_ai_agent_fails_when_provider_returns_null_html(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {"message": {"content": '{"html":null,"css":"","summary":""}'}}
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "failed"
    assert result.is_applyable is False
    assert result.proposed_html == ""
    assert "None" not in result.proposed_html


def test_template_ai_agent_blocks_jinja_marker_hidden_in_comment(monkeypatch):
    def fake_completion(**kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"html":"{# {{ customer.name }} #}<p>removed</p>","css":"","summary":"Removed token."}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.template_ai_agent.completion", fake_completion)
    agent = TemplateAiAgent("gpt-4o-mini", True, 30, 20000, 2000)

    result = agent.create_proposal(
        instruction="Improve layout",
        current_html="<p>{{ customer.name }}</p>",
        current_css="",
        document_fields=["customer.name"],
        mock_data={"customer": {"name": "Ada"}},
    )

    assert result.status == "invalid"
    assert result.is_applyable is False
    assert "Missing preserved Jinja marker: {{ customer.name }}" in result.validation_errors


def test_template_ai_agent_scanner_skips_jinja_markers_in_raw_blocks():
    markers = TemplateAiAgent._extract_jinja_markers(
        "{% raw %}<p>{{ customer.name }}</p>{% endraw %}{{ document.number }}"
    )

    assert markers == ["{% raw %}", "{% endraw %}", "{{ document.number }}"]


def create_template_fixture(db_session, user):
    document_type = DocumentType(name="Invoice", description="Invoice document", created_by=user)
    template = HtmlTemplate(
        document_type=document_type,
        name="Invoice base",
        html="<p>{{ customer.name }}</p>",
        css="p { color: black; }",
        token_names=["customer.name"],
        created_by=user,
        mock_data={"customer": {"name": "Ada"}},
    )
    db_session.add(template)
    db_session.commit()
    return template


def test_create_ai_proposal_persists_and_returns_applyable(client, db_session, user, monkeypatch):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)

    def fake_create_proposal(self, **kwargs):
        return TemplateAiProposalResult(
            proposed_html="<section><p>{{ customer.name }}</p></section>",
            proposed_css="section { padding: 24px; }",
            summary="Improved spacing.",
            status="valid",
            validation_errors=[],
            is_applyable=True,
            provider="litellm",
            model="gpt-4o-mini",
        )

    monkeypatch.setattr("app.services.template_ai_agent.TemplateAiAgent.create_proposal", fake_create_proposal)
    monkeypatch.setattr("app.api.template_ai_proposals.settings.ai_requests_enabled", True)

    response = client.post(
        f"/api/content/templates/{template.id}/ai-proposals",
        json={
            "instruction": "Make it formal",
            "current_html": template.html,
            "current_css": template.css,
            "mock_data": template.mock_data,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["template_id"] == str(template.id)
    assert body["proposed_html"] == "<section><p>{{ customer.name }}</p></section>"
    assert body["is_applyable"] is True
    assert body["status"] == "valid"


def test_apply_ai_proposal_marks_applied_without_mutating_template(client, db_session, user):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Improved spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )
    db_session.add(proposal)
    db_session.commit()

    response = client.post(f"/api/content/templates/{template.id}/ai-proposals/{proposal.id}/apply")

    assert response.status_code == 200
    body = response.json()
    assert body["applied_at"] is not None
    db_session.refresh(template)
    assert template.html == "<p>{{ customer.name }}</p>"


def test_list_ai_proposals_returns_template_proposals(client, db_session, user):
    _auth_client(client, db_session, user)
    template = create_template_fixture(db_session, user)
    proposal = HtmlTemplateAiProposal(
        template=template,
        created_by=user,
        instruction="Make it formal",
        input_html=template.html,
        input_css=template.css,
        proposed_html="<section><p>{{ customer.name }}</p></section>",
        proposed_css="section { padding: 24px; }",
        summary="Improved spacing.",
        provider="litellm",
        model="gpt-4o-mini",
        status="valid",
        validation_errors=[],
        is_applyable=True,
    )
    db_session.add(proposal)
    db_session.commit()

    response = client.get(f"/api/content/templates/{template.id}/ai-proposals")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(proposal.id)
    assert body[0]["template_id"] == str(template.id)
