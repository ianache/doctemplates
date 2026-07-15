# Task 2 Review Package

## Git status
 M backend/app/services/content_validation.py
?? backend/tests/test_template_ai_proposals.py

## Diff
diff --git a/backend/app/services/content_validation.py b/backend/app/services/content_validation.py
index 3749148..7ab85be 100644
--- a/backend/app/services/content_validation.py
+++ b/backend/app/services/content_validation.py
@@ -5,6 +5,29 @@ from jinja2.visitor import NodeVisitor
 from fastapi import HTTPException
 
 TOKEN_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")
+JINJA_MARKER_PATTERN = re.compile(r"(\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\})")
+
+
+def normalize_jinja_marker(marker: str) -> str:
+    marker = " ".join(marker.strip().split())
+    if marker.startswith("{{") and marker.endswith("}}"):
+        inner = marker[2:-2].strip()
+        return f"{{{{ {inner} }}}}"
+    if marker.startswith("{%") and marker.endswith("%}"):
+        inner = marker[2:-2].strip()
+        return f"{{% {inner} %}}"
+    return marker
+
+
+def extract_jinja_markers(html: str) -> set[str]:
+    return {normalize_jinja_marker(match.group(0)) for match in JINJA_MARKER_PATTERN.finditer(html or "")}
+
+
+def validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]:
+    original_markers = extract_jinja_markers(original_html)
+    proposed_markers = extract_jinja_markers(proposed_html)
+    missing = sorted(original_markers - proposed_markers)
+    return [f"Missing preserved Jinja marker: {marker}" for marker in missing]
 
 
 def extract_template_tokens(html: str) -> list[str]:
@@ -288,4 +311,3 @@ def extract_template_tokens_ast_warnings(html: str, valid_ancestors: set[str]) -
             warnings.append(f"Token '{raw}' is not declared in schema")
 
     return sorted(list(set(warnings)))
-

## File: backend/tests/test_template_ai_proposals.py
`
import uuid

import pytest

from app.models.content_template import HtmlTemplate
from app.models.document_type import DocumentType
from app.models.template_ai_proposal import HtmlTemplateAiProposal
from app.models.user import User
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers


@pytest.fixture
def user(db_session):
    value = User(sub="template-ai-test", email="template-ai@example.com")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


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
`
