<!-- GSD:project-start source:PROJECT.md -->
## Project

**DocManagement Platform**

A general-purpose document management platform where operational users visually design document mockups — composing pages from dynamic HTML templates (token-based, e.g. `{{cliente.nombre}}`) and uploaded static PDF pages (e.g. legal terms) — and generate final PDF documents via an API by supplying the data to fill those tokens. Each document design belongs to a **document type**, an admin-configurable concept that defines its own allowed data schema (tokens/fields). The "Sales Channel + Service" scenario from the original PRD (with Básico/Flota token filtering) is just one example document type this platform must support generally — not a hardcoded rule.

**Core Value:** Operational users can visually compose a document design (templates + fixed content, in order) and reliably generate a correct final PDF from it via API, without engineering involvement per document type.

### Constraints

- **Tech stack**: No hard constraints — free to choose a modern, sensible stack (backend language/framework, PDF/HTML-to-PDF library, template engine, frontend framework)
- **Timeline**: No hard deadline stated
- **Auth**: Must integrate an external OAuth2/OIDC identity provider (generic — not a named provider yet); platform does not own user credentials
- **Output format**: PDF only for MVP1
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - Main application language
## Runtime
- Python 3.12+
- uv (UV package manager)
- Lockfile: `uv.lock` (present, maintains deterministic dependency resolution)
## Frameworks
- headroom-ai 0.30.0 - Installed with `[all]` extras flag; primary framework providing AI/ML infrastructure
- FastAPI - Available for REST API development
- Uvicorn - Available ASGI server for running web applications
- HTTPx with HTTP/2 support - Available for HTTP client operations
- Torch - Deep learning framework
- Transformers - HuggingFace transformers library
- sentence-transformers - For embedding generation
- scikit-learn - Machine learning utilities
- ONNX Runtime - Model inference
- rapidocr-onnxruntime - OCR capabilities
## Key Dependencies
- headroom-ai >= 0.30.0 - Core framework with extensive AI/ML tooling
- sqlite-vec - Vector storage and similarity search
- OpenTelemetry (API, SDK, HTTP exporter) - Observability and tracing
- HuggingFace Hub - Model downloading and management
- Datasets - Data loading utilities
- Magika - File type detection
- Trafilatura - Web content extraction
- Jinja2 - Template rendering
- Pillow - Image processing
- openpyxl - Excel file handling
- xlrd - Legacy Excel support
- watchdog - File system event monitoring
- websockets - WebSocket support
- zstandard - Compression
- MCP (Model Context Protocol) - Available for tool integration
## Configuration
- No `.env` file present - configuration would need to be added for any external API keys
- `.python-version` present (3.12) - defines Python version constraint
- `pyproject.toml` - Project metadata and dependency specification
- `uv.lock` - Locked dependency versions for reproducible installs
## Platform Requirements
- Python 3.12+ required
- uv package manager for consistent dependency resolution
- Windows (project is on Windows 11), but platform-independent
- Python 3.12+ runtime
- Can deploy via uvicorn if FastAPI used
- OpenTelemetry exporters available for observability integration
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Status
## Naming Patterns
- All lowercase with hyphens (project name: `29-docmanagemet`)
- Python modules: lowercase with underscores (e.g., `main.py`)
- Not yet established for package/module organization
- Snake case (e.g., `main()`)
- Following PEP 8 conventions (inferred from `main.py`)
- Not yet established (minimal existing code)
- No type hints present in current code
- Python 3.12+ available but not yet utilized
## Code Style
- No formatter configured (black, ruff, or others not in dependencies)
- Default Python indentation (4 spaces, inferred from `main.py`)
- No linter configured (flake8, pylint, ruff not in dependencies)
- No `.pylintrc`, `setup.cfg`, or similar files present
## Import Organization
- Not yet established
- Python 3.12 and later (with modern import features available)
- Not used in current code
## Error Handling
- Not yet established
- No error handling present in `main.py`
## Logging
- Not configured
- `print()` used in `main.py` (basic console output)
- None established yet
## Comments
- Not yet established
- Current code has no comments
- Not applicable (Python, not TypeScript)
- No docstrings present in current code
## Function Design
- Not yet established
- Single function `main()` takes no parameters
- Single function `main()` returns `None` (implicit)
## Module Design
- Entry point: `main()` called via standard `if __name__ == "__main__":` pattern
- Not applicable to current structure
## Dependencies
- `headroom-ai[all]>=0.30.0` (only production dependency)
- Type hints (Python 3.12 supports modern type syntax)
- Error handling framework (for BFF API endpoints)
- API response serialization patterns
- Logging configuration (for PDF processing pipeline)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Codebase is in initial stage with only project scaffolding
- Main entry point (`main.py`) contains stub implementation
- No layers, modules, or abstractions yet defined
- PRD.md describes intended product (document template designer) but no code implementation exists
- Configuration endpoints for template parameters
- Marker filtering logic based on service type (Basic vs. Fleet)
- PDF composition and merging logic
- Document template persistence layer
## Current Codebase State
- `main.py` - Stub entry point (5 lines, prints hello message)
- `pyproject.toml` - Project metadata and dependencies
- `PRD.md` - Product requirements document (not code)
- `headroom-ai[all]>=0.30.0` - Only declared dependency
## Entry Points
- Location: `main.py`
- Triggers: Command-line invocation
- Responsibilities: None (stub implementation only)
## Intended Endpoints (from PRD)
- `GET /api/bff/maquetas/configuracion-inicial` - Initial configuration
- `GET /api/bff/maquetas/marcadores` - Fetch authorized markers by service type
- `POST /api/bff/maquetas` - Persist template structure
- `POST /api/bff/maquetas/previsualizar` - Generate preview PDF
## Critical Business Rules (from PRD)
## Error Handling
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
