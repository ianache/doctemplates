# Plan 13-03 Summary: Service and API Refactor for Decoupled Storage

## Work Done
1. **Refactored Services**:
   - Updated `save_static_pdf_asset` in `backend/app/services/content_storage.py` to accept the injected `StorageProvider` and save via its abstraction.
   - Refactored `generate_composed_pdf` in `backend/app/services/pdf_generator.py` to retrieve static PDFs using the `StorageProvider` stream reader.
2. **Refactored Routers**:
   - In `backend/app/api/static_pdfs.py`, injected the storage provider dependency and routed uploads and downloads through the provider's `save` and `get_download_response` methods.
   - In `backend/app/api/issuances.py`, redirected public download, preview, and standard download routes to use `StorageProvider.get_download_response`.
   - In `backend/app/api/document_designs.py`, modified design preview and issuance generation to use `StorageProvider`.
3. **Database Model Properties**:
   - Added backward-compatible properties with getters/setters for `stored_path` in `StaticPdfAsset` and `file_path` in `DocumentIssuance` to dynamically resolve paths under local storage when legacy/test code calls them.

## Verification Result
- Verified that all router compilation checks succeed.
- Ran backend test suite and all 88 unit and integration tests passed successfully.
