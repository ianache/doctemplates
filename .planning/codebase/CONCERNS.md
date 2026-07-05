# Codebase Concerns

**Analysis Date:** 2026-07-05

## Status: Early-Stage Project

This is a **pre-alpha, pre-implementation codebase** with a comprehensive PRD but only a hello-world `main.py` (93 bytes). Concerns below are based on the gap between the planned DocManagement system and current implementation state, plus risks that must be addressed before development begins.

---

## Critical Implementation Gaps

**Missing Core Dependencies:**
- **Issue:** PRD requires PDF composition/merging (step 4 in section 4), but no PDF library is configured
  - `PyPDF2` or `pypdf` not in `pyproject.toml`
  - Required for: extracting specific pages from static PDFs, merging ordered pages
- Files: `pyproject.toml`
- Impact: Cannot implement the document preview or final PDF generation endpoints without adding these dependencies
- Fix approach: Add PDF libraries to `pyproject.toml` and establish version constraints; evaluate `pypdf` (modern, maintained) vs `PyPDF2` (legacy) based on Python 3.12+ compatibility needs

**Missing Web Framework:**
- **Issue:** PRD specifies 4 REST endpoints (GET /api/bff/maquetas/configuracion-inicial, GET /api/bff/maquetas/marcadores, POST /api/bff/maquetas, POST /api/bff/maquetas/previsualizar) but no web framework configured
  - No Flask, FastAPI, Django, or similar in dependencies
  - Only dependency is `headroom-ai[all]>=0.30.0` (which is a token-saving tool, not an API framework)
- Files: `pyproject.toml`, `main.py`
- Impact: Cannot implement BFF endpoints until a web framework is chosen and integrated
- Fix approach: Select framework (FastAPI recommended for async PDF processing); add to dependencies; create new entry point (not `main()`)

**Missing Data Persistence Layer:**
- **Issue:** PRD assumes persistent storage of maquetas (templates) with fields: nombre_maqueta, canal_venta_id, servicio_id, paginas array
  - No database driver configured (no sqlalchemy, psycopg2, motor, etc.)
  - No ORM setup
  - No schema definition for: Maquetas, Canales, Servicios, Páginas entities
- Files: `pyproject.toml`
- Impact: POST endpoints cannot persist data; no way to retrieve stored templates
- Fix approach: Choose database (PostgreSQL recommended for structured data); add ORM/driver; create migration system

**Missing File Storage Integration:**
- **Issue:** PRD references `pdf_estatico_path` like "storage/repositorio/terminos_legales.pdf" but no file storage configured
  - No S3/GCS client libraries
  - No local file handler validation
  - Unclear how static PDF files will be managed, versioned, or accessed
- Files: PRD.md line 64
- Impact: Cannot locate or load static PDF assets referenced in maquetas
- Fix approach: Define file storage strategy (local filesystem for dev, S3/GCS for prod); add appropriate client library; create storage validation layer

---

## Security Concerns

**Token Injection Risk in HTML Templates:**
- **Issue:** PRD allows users to write HTML with placeholder tokens (e.g., `{{cliente.nombre}}`) that are replaced with data; no escaping mechanism documented
  - Templates stored directly as `html_contenido` in payload (section 3, page 1)
  - Replacement logic not yet implemented, but risk is evident
  - No mention of HTML sanitization or XSS protection
- Files: PRD.md (section 3, template composition), will affect: API handler, template processing logic
- Impact: **High** - User-supplied templates could inject malicious HTML/JS into PDFs if replacement is done naively
- Current mitigation: None yet (code doesn't exist)
- Recommendations:
  - Implement strict allowlist of replaceable tokens (only from documented schema, never free-form)
  - Use HTML templating engine (Jinja2) with autoescaping enabled, not string replace
  - Validate token names against Canales and Servicios schema before template storage
  - Add pre-generation HTML sanitization (bleach library) if permitting user-authored HTML

**Missing API Authentication:**
- **Issue:** PRD endpoints have no authentication or authorization mentioned; no mention of user identity or role-based access
  - No JTW, API key, or session handling documented
  - Endpoints could be publicly accessible by default
- Files: PRD.md (section 3, all endpoints)
- Impact: **High** - Unauthorized users could create/modify/preview document templates
- Current mitigation: None yet
- Recommendations:
  - Require API authentication (bearer token or API key) for all BFF endpoints
  - Implement role-based access (operativo vs admin)
  - Validate canal_venta_id and servicio_id ownership before allowing template creation
  - Add rate limiting to prevent PDF generation abuse

**Data Validation Gaps:**
- **Issue:** PRD specifies strict business rules (e.g., "servicio_id SERV-SAT-BASICO must not include advanced fleet markers") but enforcement mechanism not documented
  - No input validation schema for POST payloads
  - No mention of rejecting invalid canal_venta_id or servicio_id values
  - Token filtering is BFF responsibility, but no validation of whether rejected tokens are present in HTML
- Files: PRD.md (section 2, critical rules), will affect: POST /api/bff/maquetas handler
- Impact: **Medium** - Data integrity violations; bypass of business rules if implementation is incomplete
- Current mitigation: None yet
- Recommendations:
  - Create pydantic or similar schema validators for all payloads
  - Implement strict enum validation for service types and channels
  - Add server-side check: if servicio_id=SERV-SAT-BASICO and html_contenido contains "unidad.sensor_temperatura", reject with 400 Bad Request
  - Document exact error response format for invalid tokens

---

## Performance & Scalability Concerns

**PDF Processing Memory Usage:**
- **Issue:** PRD step 3 specifies extracting specific pages from PDFs; step 4 merges multiple pages together
  - Large PDFs (e.g., multi-page T&Cs) loaded fully into memory for page extraction
  - No discussion of buffering, streaming, or memory limits
  - Multiple PDF merges could accumulate in memory
- Files: Will affect: PDF processing utility module (not yet created)
- Impact: **Medium** - Memory spikes under load; potential DoS if large PDFs generated repeatedly
- Scaling limit: Likely failure if generating 100+ complex multi-page PDFs concurrently
- Scaling path:
  - Implement streaming PDF processing (if library supports)
  - Add async/background job queue (Celery + Redis) for PDF generation
  - Cache frequently-generated PDFs (Redis) with TTL
  - Set max file size limits for uploaded PDFs

**No Caching Layer:**
- **Issue:** GET /api/bff/maquetas/configuracion-inicial returns static list of channels and services; re-fetched on every UI load
  - No caching mentioned; likely database queries on every request
  - No TTL strategy for cached data if channels/services change infrequently
- Files: PRD.md (section 3.1)
- Impact: **Low** - Unnecessary database hits; poor UX if service is slow
- Improvement path: Add Redis caching with 1-hour TTL for configuration; invalidate on admin updates

**No Pagination for Large Lists:**
- **Issue:** GET /api/bff/maquetas/marcadores response structure shows arrays of marker fields; if 100+ fields, response size explodes
  - No mention of filtering or pagination
  - No discussion of how frontend handles large marker lists
- Files: PRD.md (section 3.2), example response
- Impact: **Low** - Oversized responses; slow frontend rendering
- Improvement path: Document expected marker count per service; add filtering if lists exceed 50 items

---

## Fragile & Risky Areas

**Maqueta Validation & Business Rule Enforcement:**
- **Issue:** Service type filtering (Basic vs Fleet markers) is described as BFF responsibility, but enforcement across the entire flow is unclear
  - GET endpoint returns filtered markers based on service_id
  - POST endpoint accepts template with html_contenido (step 1) and pages array (step 2)
  - No documented validation ensuring POST payload doesn't include filtered-out markers
  - What if someone manually crafts a POST request with "unidad.bloqueo_puertas" for SERV-SAT-BASICO?
  - PRD says "retornar error 400 Bad Request" (section 5.3) but no validation code exists
- Files: Will affect: POST /api/bff/maquetas handler, template validator
- Why fragile: Easy to miss validation in one code path; business rules live in multiple places (BFF filtering + validation logic)
- Safe modification approach:
  - Extract business rules to central config/enum definitions
  - Create reusable validator function: `validate_markers(html_contenido, servicio_id, marker_whitelist)` → returns error list
  - Use in both GET filtering AND POST validation
  - Add test for each service type boundary case
- Test coverage gaps: No test suite exists yet; will need marker validation tests for both services

**PDF Path Resolution & File Access:**
- **Issue:** Step 3 in PRD says "Localizar los archivos del almacenamiento indicados en pdf_estatico_path"
  - But storage strategy undefined
  - Path format undefined (relative vs absolute; local filesystem vs S3 URI)
  - No error handling if file doesn't exist
  - No access control (can user specify any path, even outside repository?)
  - Page extraction (`pagina_origen_especifica`) could fail silently if page doesn't exist
- Files: Will affect: PDF composition module
- Why fragile: Risk of broken previews/generation if storage setup is unclear; path traversal vulnerability if not sanitized
- Safe modification approach:
  - Document exact storage strategy before implementation
  - Validate pdf_estatico_path against allowlist/whitelist (e.g., only files in `storage/repositorio/`)
  - Test that ../../../etc/passwd is rejected
  - Implement explicit error responses for file not found, invalid page number
- Test coverage gaps: File access, path validation, error cases not yet defined

**Template Composition Order Dependency:**
- **Issue:** PRD section 4 says "Insertar ordenadamente las páginas respetando la propiedad secuencial de la llave 'orden'"
  - Array can be manually reordered in frontend; if `orden` field is not validated, mismatched indices could cause silent bugs
  - Example: User has pages with orden=[1, 3, 5] (missing 2, 4); what happens? PDF generated with gaps?
  - No validation that orden is contiguous and unique
- Files: Will affect: Template model, POST /api/bff/maquetas handler
- Why fragile: Silent data inconsistencies; hard to debug if order field is not strictly validated
- Safe modification approach:
  - Validate: all orden values are unique integers
  - Validate: orden range is 1..N with no gaps
  - Re-assign orden sequentially on POST (don't trust frontend)
  - Add test: orden=[1, 1, 3] rejected; orden=[1, 2, 2] rejected

---

## Known Technical Debt

**No Type Safety:**
- **Issue:** Python 3.12+ is required, but no type hints or mypy configuration present
  - Single function `main()` has no parameter or return type annotations
  - Planned API handlers will have dozens of parameters (maqueta schema) with no type checking
  - Risk of passing wrong data type to PDF processor, database layer, etc.
- Files: `main.py`, `pyproject.toml`
- Impact: **Medium** - Runtime type errors; poor IDE autocomplete for future developers
- Fix approach: Enable mypy in CI; add `mypy = "^1.0"` to dev dependencies; annotate all new code

**No Testing Framework:**
- **Issue:** No test runner, no test dependencies, no test directory
  - pytest or unittest not in dependencies
  - No fixtures for test data (maquetas, PDFs, markers)
  - No CI configuration to run tests
- Files: `pyproject.toml`, missing `tests/` directory
- Impact: **High** - No automated validation of business rules, endpoints, or PDF composition
- Fix approach:
  - Add `pytest>=7.0` to dev dependencies
  - Create `tests/` directory with structure: `tests/{unit,integration,fixtures}/`
  - Add at least 1 test per endpoint before merging to main
  - Configure pytest in `pyproject.toml`
  - Add GitHub Actions or similar CI

**No Logging or Observability:**
- **Issue:** `main.py` uses bare `print()`; no logging framework configured
  - Planned API and PDF processing code will be hard to debug without logs
  - No structured logging (JSON) for monitoring
  - No error tracking (Sentry, etc.)
- Files: `main.py`, `pyproject.toml`
- Impact: **Low** during development; **High** in production
- Fix approach:
  - Add `python-json-logger` or `structlog` to dependencies
  - Configure logging with file rotation for PDF composition (long-running operations)
  - Add request ID tracking for API handlers
  - Integrate Sentry (or similar) for error tracking in production config

**Empty README:**
- **Issue:** README.md is empty; no setup instructions for developers
  - No guidance on dependencies, Python version, environment setup
  - No overview of planned architecture
- Files: `README.md`
- Impact: **Low** - Onboarding friction; unclear project state
- Fix approach: Add sections: Overview, Quick Start (uv venv, uv sync), Project Structure, Running Tests, API docs link

---

## Missing Critical Features (Not Yet Started)

**BFF API Implementation:**
- What's missing: All 4 REST endpoints from PRD section 3
- Blocks: Users cannot configure documents, preview them, or generate final PDFs
- Estimated scope: 100+ lines of code; requires database, PDF library integration

**Document Preview Generation:**
- What's missing: POST /api/bff/maquetas/previsualizar endpoint logic (step 1-4 of PDF composition)
- Blocks: Users cannot preview templates before saving
- Estimated scope: 50+ lines; requires PDF library expertise

**Database Layer:**
- What's missing: Models for Maquetas, Canales, Servicios, Páginas; migrations; queries
- Blocks: No persistent data storage
- Estimated scope: 200+ lines; requires ORM/database design

**File Storage Handler:**
- What's missing: Strategy and implementation for storing/retrieving static PDFs and generated documents
- Blocks: Cannot reference or load static PDF assets
- Estimated scope: 50+ lines (if local FS); 100+ lines (if S3)

**Marker Validation & Service Type Filtering:**
- What's missing: Logic to filter markers by service type; validation of marker names in templates
- Blocks: Cannot enforce business rules (Basic vs Fleet distinction)
- Estimated scope: 30+ lines; critical for correctness

---

## Dependencies at Risk

**Only Production Dependency: `headroom-ai[all]>=0.30.0`**
- Risk: This is a code exploration/analysis tool, not a framework for building the application
  - May be used for documentation or development tasks, but not for runtime
  - Project will require additional frameworks/libraries that don't exist yet
- Impact: **Low** - headroom-ai itself is stable; risk is that essential dependencies are missing
- Mitigation: Lock version to `>=0.30.0,<1.0.0` once development begins; evaluate if headroom-ai is needed at runtime or just during development

**No Development Dependencies:**
- Risk: No testing, linting, formatting, or type-checking tools configured
  - Future developers have no guardrails
  - No consistent code style
- Impact: **Medium** - Increased bug risk; onboarding friction
- Mitigation: Add dev dependencies immediately: pytest, black/ruff, mypy, pre-commit hooks

---

## Security Recommendations Summary

**Before first production deployment:**
1. Implement API authentication (bearer token or API key)
2. Add role-based access control (who can create/modify templates)
3. Validate all input payloads (pydantic schemas)
4. Implement token allowlist validation (no user-supplied tokens)
5. Use HTML templating engine with autoescaping (Jinja2), not string replace
6. Sanitize PDF content before generation (bleach library)
7. Validate file paths (no path traversal)
8. Add rate limiting to prevent PDF generation abuse
9. Log all template modifications (audit trail)
10. Set file size limits for uploaded PDFs

---

*Concerns audit: 2026-07-05*

**Key Takeaway:** This project is at the PRD stage and requires foundational implementation before concerns become operational issues. The main risks today are architectural decisions not yet made (web framework, database, file storage) and security gaps that must be designed in from the start (validation, authentication, token escaping).
