# Phase 13: implementar-la-propuesta-de-separacion-de-almacenamiento - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning
**Source:** Storage Decoupling Proposal (.design/storage_decoupling_proposal.md)

<domain>
## Phase Boundary

This phase delivers the complete decoupling of the backend file storage system. It abstracts all local filesystem storage operations for static PDF assets and generated document issuances into a unified `StorageProvider` interface. It provides two concrete implementations: a local filesystem provider (for backwards compatibility and local testing) and an S3-compatible provider (supporting AWS S3, MinIO, and Oracle Cloud Object Storage).

The phase is complete when:
1. The abstract `StorageProvider` is defined.
2. `LocalStorageProvider` and `S3StorageProvider` are implemented.
3. Database schemas are migrated to store `storage_key` instead of absolute file system paths.
4. All storage and retrieval operations in services (`content_storage.py`, `pdf_generator.py`) and API routers (`static_pdfs.py`, `issuances.py`, `document_designs.py`) are refactored to use the dependency-injected storage provider.
5. All backend tests pass successfully.
</domain>

<decisions>
## Implementation Decisions

### Storage Abstraction (`StorageProvider`)
- Define an abstract base class `StorageProvider` containing abstract methods:
  - `save(key: str, content: bytes, category: str) -> str`
  - `get(key: str, category: str) -> bytes`
  - `get_stream(key: str, category: str) -> io.BytesIO`
  - `delete(key: str, category: str) -> None`
  - `get_download_response(key: str, filename: str, category: str) -> Response`
- Support two logical file categories: `static_pdfs` (assets) and `issuances` (generated documents).

### Storage Providers
- **`LocalStorageProvider`**: Uses the local filesystem (`os`, `pathlib`) under configured directories. It should handle directory creation automatically on write.
- **`S3StorageProvider`**: Uses `boto3` client to interact with S3-compatible endpoints. It must use the v4 signature configuration. The `get_download_response` method will stream bytes directly from S3 using FastAPI's `StreamingResponse` (to avoid exposing direct bucket URLs).

### Database Schema Migration
- Generate an Alembic migration script to:
  - Rename `stored_path` in `static_pdf_assets` to `storage_key`.
  - Rename `file_path` in `document_issuances` to `storage_key`.
  - Write data migrations to extract the base filename (e.g., `abc-123.pdf`) from absolute paths for existing records so that they function as keys.

### Configuration & Dependency Injection
- Update Pydantic config schemas in `app/config.py` to include:
  - `storage_provider_type` (`local` or `s3`, defaults to `local`).
  - `storage_s3_endpoint_url` (optional string, e.g. for MinIO).
  - `storage_s3_access_key` (optional string).
  - `storage_s3_secret_key` (optional string).
  - `storage_s3_region` (optional string).
  - `storage_s3_bucket_static_pdfs` (string).
  - `storage_s3_bucket_issuances` (string).
- Expose a cached `get_storage_provider()` helper function in `app/core/dependencies.py` or similar to return the singleton active provider.

### Refactoring of Existing Logic
- **`pdf_generator.py`**: Fetch the file stream from the storage provider using `get_stream(key, "static_pdfs")` and pass it to `PdfReader` instead of using absolute paths.
- **`static_pdfs.py` router**: Update the upload path to call the storage provider's `save` method and download path to call `get_download_response`.
- **`issuances.py` router**: Update download path to call `get_download_response`.
- **`document_designs.py` router**: Update PDF generation and activation to call `save` on the storage provider.

### the agent's Discretion
- Choice of specific exception handling when bucket operations fail.
- Structure of the unit tests to mock `boto3` calls (using `moto` or manual mocking).
- Setup of MinIO credentials inside development compose environment.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design Proposal
- [.design/storage_decoupling_proposal.md](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/.design/storage_decoupling_proposal.md) — The core architectural guide.

### Backend Code to Modify
- [backend/app/config.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/config.py) — Config definitions.
- [backend/app/models/document_design.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/models/document_design.py) — Table models for design.
- [backend/app/models/document_issuance.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/models/document_issuance.py) — Table models for issuance.
- [backend/app/services/content_storage.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/services/content_storage.py) — Current filesystem service.
- [backend/app/services/pdf_generator.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/services/pdf_generator.py) — Composed PDF generation logic.
- [backend/app/api/static_pdfs.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/api/static_pdfs.py) — API endpoints for static assets.
- [backend/app/api/issuances.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/api/issuances.py) — API endpoints for issuances.
- [backend/app/api/document_designs.py](file:///D:/02-PERSONAL/01-PROJECTS/29-DocManagemet/backend/app/api/document_designs.py) — Composed PDF generation endpoint.
</canonical_refs>

<specifics>
## Specific Ideas
- Integrate MinIO as a mock service in tests if possible, or use standard unit test mocks.
</specifics>

<deferred>
## Deferred Ideas
- Automatic sync tool to move production filesystem PDFs to S3 (this is deferred to an ops script outside backend core).
</deferred>

---

*Phase: 13-implementar-la-propuesta-de-separacion-de-almacenamiento*
*Context gathered: 2026-07-12 via proposal analysis*
