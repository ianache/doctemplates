# Phase 3: Content Building Blocks - Research

**Researched:** 2026-07-07
**Domain:** document-content library on top of the existing FastAPI + SQLAlchemy + Postgres backend, with a React 19 frontend for authoring and upload flows
**Confidence:** HIGH

## Summary

Phase 3 should be treated as a content-library phase, not a rendering phase. The platform needs to persist two reusable content primitives:

1. HTML templates scoped to a document type, with token validation against the current allowed schema.
2. Static PDF assets uploaded through the UI and stored locally on disk, optionally with page-range extraction.

The phase should not attempt to render HTML to PDF yet. That belongs to Phase 6, when preview and generation become explicit requirements. Here, the goal is to store content blocks safely and make them browsable for later design composition.

The cleanest backend shape is two first-class resource types rather than a polymorphic blob table:
- `HtmlTemplate` / `DocumentTemplate` for schema-scoped HTML
- `StaticPdfAsset` for local-file PDF storage and page-range extraction

This keeps the API and UI simple, preserves future referenceability, and avoids JSON blob storage that would make later composition and validation harder.

## Recommended Architecture

### HTML templates
- Persist the raw HTML string and the associated `document_type_id`.
- Extract `{{...}}` tokens server-side when saving.
- Compare tokens to the live document-type field names.
- Reject unknown tokens with a clear 400-style error that names the invalid tokens.
- Keep the validation logic centralized in a helper so both create and future edit flows can reuse it.

### Static PDF assets
- Accept uploads via multipart form data.
- Store files on the local filesystem under a configurable content root such as `storage/repositorio/`.
- Save metadata in the database: original filename, stored path, page count, extracted page range, uploader, timestamps.
- Use `pypdf` to count pages and extract page ranges.
- Make assets referenceable by returning stable IDs and download URLs.

### Frontend
- Reuse nested routes under `AuthenticatedShell`.
- Present a content-library surface with two buckets: Templates and Static PDFs.
- Use plain textarea/file-input forms; no rich editor or designer yet.
- Reuse the document-type list to populate template scope selectors.

## Dependency Direction

- `python-multipart` is needed for file uploads.
- `pypdf` is needed for page counting and range extraction.
- No new rendering libraries are required yet.
- The existing `react-hook-form` dependency from Phase 2 can be reused for the template authoring form.

## Key Decisions

- Token validation happens on the backend, not just in the browser.
- Document types remain editable; validation always uses the current schema at save time.
- Static PDFs are stored locally, not in the database.
- Upload page ranges are 1-indexed and inclusive.
- Rendering and page composition are explicitly deferred to Phase 4/6.

## Risks / Notes

- The phase should avoid overbuilding a designer UI. The next phase owns canvas composition.
- If page-range extraction becomes awkward in the upload API, keep the storage model explicit so later design composition can still reference the extracted asset deterministically.

