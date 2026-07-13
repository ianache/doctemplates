# Plan 14-04 Summary

The BFF proxy integration and frontend generated-documents library/detail views have been successfully updated to support async Celery jobs.

## Accomplished Work
- **BFF Proxy Tests**: Added test cases (`test_proxy_async_202_status_code` and `test_proxy_readiness_409_status_code`) verifying that the BFF propagates backend async status codes and error JSONs.
- **Frontend library types**: Updated `DocumentIssuanceStatus` and added Celery fields to `DocumentIssuanceListItem` in `lib/documentIssuances.ts`.
- **API helpers**: Added `generateDocumentDesign` in `lib/documentDesigns.ts` for type safety.
- **Library List view**: Added queued/processing labels and status select dropdown filters in `DocumentLibraryPage.tsx`. Implemented automatic adaptive list polling when active jobs are present.
- **Detail view**: Refactored `DocumentIssuanceDetailPage.tsx` to poll JSON for active jobs, conditionally render the PDF preview only when status is success, render a loading state when queued/processing, and display the error message when generation fails.
- **Properties panel**: Updated `IssuanceProperties.tsx` to render queued/started/completed timestamps, retry count, and task ID.
