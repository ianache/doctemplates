# Phase 3 Validation

## Automated Checks

- Backend content-template tests
- Backend static-PDF tests
- Full backend suite
- Frontend build

## Manual-Only Verifications

1. Create a valid HTML template against an existing document type and confirm it saves.
2. Attempt to save a template with at least one unknown token and confirm the save is rejected with a clear error.
3. Upload a static PDF and confirm the asset appears in the library with the expected page count and metadata.
4. Upload a PDF with a page range and confirm the stored asset reflects the extracted subset.
5. Open a stored asset from the browser and confirm the download/view path works.

