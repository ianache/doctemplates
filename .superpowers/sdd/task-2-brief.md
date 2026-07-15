## Task 2: Validation Helpers for AI Proposals

**Files:**

- Modify: `backend/app/services/content_validation.py`
- Test: `backend/tests/test_template_ai_proposals.py`

**Interfaces:**

- Produces `extract_jinja_markers(html: str) -> set[str]`.
- Produces `validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]`.
- Later service task uses these helpers to enforce token and statement preservation.

- [ ] **Step 1: Write failing validation helper tests**

Append to `backend/tests/test_template_ai_proposals.py`:

```python
from app.services.content_validation import extract_jinja_markers, validate_preserved_jinja_markers


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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_extract_jinja_markers_includes_expressions_and_statements tests/test_template_ai_proposals.py::test_validate_preserved_jinja_markers_reports_removed_marker -v"
```

Expected: FAIL with import error for the new helper functions.

- [ ] **Step 3: Implement marker helpers**

Add near the top of `backend/app/services/content_validation.py`:

```python
JINJA_MARKER_PATTERN = re.compile(r"(\{\{[\s\S]*?\}\}|\{%[\s\S]*?%\})")


def normalize_jinja_marker(marker: str) -> str:
    marker = " ".join(marker.strip().split())
    if marker.startswith("{{") and marker.endswith("}}"):
        inner = marker[2:-2].strip()
        return f"{{{{ {inner} }}}}"
    if marker.startswith("{%") and marker.endswith("%}"):
        inner = marker[2:-2].strip()
        return f"{{% {inner} %}}"
    return marker


def extract_jinja_markers(html: str) -> set[str]:
    return {normalize_jinja_marker(match.group(0)) for match in JINJA_MARKER_PATTERN.finditer(html or "")}


def validate_preserved_jinja_markers(original_html: str, proposed_html: str) -> list[str]:
    original_markers = extract_jinja_markers(original_html)
    proposed_markers = extract_jinja_markers(proposed_html)
    missing = sorted(original_markers - proposed_markers)
    return [f"Missing preserved Jinja marker: {marker}" for marker in missing]
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py::test_extract_jinja_markers_includes_expressions_and_statements tests/test_template_ai_proposals.py::test_validate_preserved_jinja_markers_reports_removed_marker -v"
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
rtk git add backend/app/services/content_validation.py backend/tests/test_template_ai_proposals.py
rtk git commit -m "feat: validate preserved jinja markers"
```

