# Testing Patterns

**Analysis Date:** 2026-07-05

## Status

This codebase has **no testing framework or test files configured**. Testing infrastructure has not been established.

## Test Framework

**Runner:**
- Not configured
- No pytest, unittest, or other test runner in dependencies
- Recommended for this project: `pytest` (Python standard for modern projects)

**Assertion Library:**
- None installed

**Run Commands:**
- Not applicable yet

## Test File Organization

**Location:**
- Not established
- No test files found in project
- Common patterns for Python:
  - `tests/` directory at project root (preferred modern structure)
  - Or `src/tests/` alongside source code

**Naming:**
- Not established
- Standard Python pattern: `test_*.py` or `*_test.py`

**Structure:**
- No test structure in place

## Test Structure

**Suite Organization:**
- None yet

**Patterns:**
- Not established

## Mocking

**Framework:** 
- Not configured
- Recommended for this project: `unittest.mock` (stdlib, included) or `pytest-mock` (if using pytest)

**Patterns:**
- Not established

**What to Mock:**
- Not yet determined
- Anticipated mocking needs (based on PRD.md):
  - PDF rendering services (Puppeteer/Weasyprint equivalent)
  - Template engines (Handlebars/Mustache)
  - Static file storage I/O
  - Data provider APIs

**What NOT to Mock:**
- Not yet determined

## Fixtures and Factories

**Test Data:**
- No fixtures or factories present

**Location:**
- Not established
- Python pattern: `tests/fixtures/` or `conftest.py` at test root

## Coverage

**Requirements:** 
- Not enforced (no configuration present)
- Recommended tool: `pytest-cov`

**View Coverage:**
- Not configured

## Test Types

**Unit Tests:**
- Not implemented

**Integration Tests:**
- Not implemented
- Anticipated need: Testing API endpoint composition (BFF layer)
- Anticipated need: Testing PDF generation pipeline (Step 1-4 in PRD.md)

**E2E Tests:**
- Not configured

## Anticipated Testing Needs

Based on PRD.md requirements, future test coverage should address:

1. **Variable Interpolation (Paso 1):**
   - Template token replacement with mock data
   - Service-type filtering (Básico vs. Flota marker restrictions)

2. **HTML to PDF Conversion (Paso 2):**
   - Headless renderer integration (mocked in unit tests)
   - HTML template rendering with variables

3. **PDF Segmentation (Paso 3):**
   - Static PDF page extraction
   - File path resolution and I/O handling

4. **PDF Merge (Paso 4):**
   - Page ordering and sequential insertion
   - Binary buffer concatenation

5. **BFF Endpoints:**
   - Configuration endpoint response format
   - Marker filtering by service type
   - Validation: rejection of advanced fleet variables in Básico service

6. **Business Rules:**
   - Canal + Servicio exclusivity constraint
   - Marker authorization by service tier
   - Error 400 handling for invalid marker injection

## Current Development Setup

**Environment:**
- Python 3.12 (from `.python-version`)
- `uv` package manager

**Dependencies not yet added:**
- Test runner (pytest)
- HTTP framework (likely FastAPI or Flask for BFF)
- PDF processing libraries (pypdf, reportlab, weasyprint, etc.)
- Template engine (jinja2 for Handlebars-like functionality)
- Mocking libraries

---

*Testing analysis: 2026-07-05*

**RECOMMENDATION:** Establish testing infrastructure early:
1. Add `pytest` and `pytest-cov` to dev dependencies in `pyproject.toml`
2. Create `tests/` directory structure
3. Add `conftest.py` for shared fixtures
4. Begin with unit tests for template variable interpolation (lowest complexity, highest ROI)
