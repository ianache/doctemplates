# Architecture

**Analysis Date:** 2026-07-05

## Pattern Overview

**Overall:** No architecture patterns currently implemented

**Current State:**
- Codebase is in initial stage with only project scaffolding
- Main entry point (`main.py`) contains stub implementation
- No layers, modules, or abstractions yet defined
- PRD.md describes intended product (document template designer) but no code implementation exists

**Intended Architecture (from PRD):**
Based on PRD.md, the future system is planned as a BFF (Backend for Frontend) API with:
- Configuration endpoints for template parameters
- Marker filtering logic based on service type (Basic vs. Fleet)
- PDF composition and merging logic
- Document template persistence layer

## Current Codebase State

**Files:**
- `main.py` - Stub entry point (5 lines, prints hello message)
- `pyproject.toml` - Project metadata and dependencies
- `PRD.md` - Product requirements document (not code)

**Dependencies:**
- `headroom-ai[all]>=0.30.0` - Only declared dependency

## Entry Points

**Current:**
- Location: `main.py`
- Triggers: Command-line invocation
- Responsibilities: None (stub implementation only)

## Intended Endpoints (from PRD)

The PRD.md describes these future API endpoints but none are implemented:

- `GET /api/bff/maquetas/configuracion-inicial` - Initial configuration
- `GET /api/bff/maquetas/marcadores` - Fetch authorized markers by service type
- `POST /api/bff/maquetas` - Persist template structure
- `POST /api/bff/maquetas/previsualizar` - Generate preview PDF

## Critical Business Rules (from PRD)

These rules will guide future architecture but are not yet implemented:

1. **Strict Association:** Each template belongs to exactly one combination of sales channel + specific service
2. **Dynamic Marker Filtering:** 
   - Basic service (B2C): Only location, safe parking, unit blocking
   - Fleet service (B2B): Advanced markers including convoy management, geo-fences, routes, temperature controls
3. **PDF Composition:** Combine static PDFs with dynamic HTML templates containing token replacements
4. **Page-Level Extraction:** Support extracting specific pages from static PDFs to reduce resource usage

## Error Handling

**Strategy:** Not yet defined

## Cross-Cutting Concerns

**Logging:** Not implemented
**Validation:** Not implemented
**Authentication:** Not mentioned in current PRD
**PDF Manipulation:** Listed as required (PyPDF2 suggested in PRD for Python)

---

*Architecture analysis: 2026-07-05*
