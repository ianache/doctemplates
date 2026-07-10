# Phase 08 Plan 01 - Summary of Changes

This plan implements dynamic AST-based template static validation for Jinja2 templates, incorporating scope-aware local variable tracking and case-insensitive matching. It secures designs against undeclared variables, returning warning response structures for drafts while enforcing a strict gate for active design templates.

## Changes

### 1. Services
- **`backend/app/services/content_validation.py`**:
  - Implemented the `JinjaTokenExtractor` (subclass of `NodeVisitor`) that maintains a scope stack and extracts the outermost resolved paths for variable references.
  - Implemented the helper `get_ancestor_paths` splitting dot-notation paths and creating progressive/wildcard variants.
  - Rewrote `validate_template_tokens` using AST-based parsing and validating referenced tokens case-insensitively against allowed ancestors and env globals/standard context keys (e.g. `range`, `loop`).
  - Added `extract_template_tokens_ast_warnings` collecting token validation warnings instead of throwing HTTPException.
- **`backend/app/services/design_validation.py`**:
  - Implemented `get_design_warnings` dynamically extracting template tokens for HTML pages and checking them against document type schemas.
  - Updated `validate_design_activation` to perform strict AST-based checks and raise HTTPException on unrecognized tokens.

### 2. API & Schemas
- **`backend/app/schemas/document_design.py`**:
  - Added `warnings: list[str] = []` to `DocumentDesignDetail` to carry warnings in responses.
- **`backend/app/api/document_designs.py`**:
  - Updated `_detail` to dynamically compute design warnings for drafts using `get_design_warnings` and propagate `db` sessions across endpoints.

### 3. Tests
- **`backend/tests/test_template_ast_validation.py`**:
  - Created a comprehensive test suite covering AST parsing, local scoping, globals bypass, and integration/activation gates.
- **`backend/tests/test_content_templates.py`**:
  - Updated legacy test assertions to align with the new AST-based token outputs.

## Verification
- Fully passed all new AST tests: `uv run --directory backend pytest tests/test_template_ast_validation.py`
- Fully passed all backend tests without regression: `uv run --directory backend pytest`
