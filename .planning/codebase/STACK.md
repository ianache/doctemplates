# Technology Stack

**Analysis Date:** 2026-07-05

## Languages

**Primary:**
- Python 3.12 - Main application language

## Runtime

**Environment:**
- Python 3.12+

**Package Manager:**
- uv (UV package manager)
- Lockfile: `uv.lock` (present, maintains deterministic dependency resolution)

## Frameworks

**Core:**
- headroom-ai 0.30.0 - Installed with `[all]` extras flag; primary framework providing AI/ML infrastructure
  - Provides CLI tools, code analysis capabilities, AST parsing via ast-grep-cli
  - Includes optional dependencies for multiple AI providers and deployment options

**Web (Optional - included via headroom-ai[all]):**
- FastAPI - Available for REST API development
- Uvicorn - Available ASGI server for running web applications
- HTTPx with HTTP/2 support - Available for HTTP client operations

**ML/AI (Optional - included via headroom-ai[all]):**
- Torch - Deep learning framework
- Transformers - HuggingFace transformers library
- sentence-transformers - For embedding generation
- scikit-learn - Machine learning utilities
- ONNX Runtime - Model inference
- rapidocr-onnxruntime - OCR capabilities

## Key Dependencies

**Critical:**
- headroom-ai >= 0.30.0 - Core framework with extensive AI/ML tooling
  - ast-grep-cli - Code analysis and AST parsing
  - click - CLI argument parsing
  - pydantic - Data validation and settings
  - rich - Terminal output formatting
  - tiktoken - Token counting for LLM usage
  - litellm (Python < 3.14) - LLM routing abstraction

**Infrastructure (Optional via headroom-ai[all]):**
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

**Environment:**
- No `.env` file present - configuration would need to be added for any external API keys
- `.python-version` present (3.12) - defines Python version constraint

**Build:**
- `pyproject.toml` - Project metadata and dependency specification
- `uv.lock` - Locked dependency versions for reproducible installs

## Platform Requirements

**Development:**
- Python 3.12+ required
- uv package manager for consistent dependency resolution
- Windows (project is on Windows 11), but platform-independent

**Production:**
- Python 3.12+ runtime
- Can deploy via uvicorn if FastAPI used
- OpenTelemetry exporters available for observability integration

---

*Stack analysis: 2026-07-05*
