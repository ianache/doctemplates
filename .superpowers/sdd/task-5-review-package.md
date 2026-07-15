# Task 5 Review Package

## Report
# Task 5 Report

## Status

Complete.

## Files Changed

- `frontend/src/lib/content.ts`
  - Added the `TemplateAiProposal` response interface with the exact Task 4 API fields and types.
  - Added the `TemplateAiProposalCreatePayload` interface.
  - Added `createTemplateAiProposal`.
  - Added `listTemplateAiProposals`.
  - Added `markTemplateAiProposalApplied`.
- `.superpowers/sdd/task-5-report.md`
  - Added this report.

No UI components were modified.

## Tests Run / Results

- `rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"`: PASS. TypeScript build and Vite production build completed successfully.
- `rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run lint"`: PASS with five existing warnings in unrelated UI files.
- `rtk proxy powershell -NoProfile -Command "git diff --check -- frontend/src/lib/content.ts"`: PASS; no whitespace errors.

## Self-Review

- Confirmed all required response fields are present verbatim: `id`, `template_id`, `created_by_id`, `instruction`, `input_html`, `input_css`, `proposed_html`, `proposed_css`, `summary`, `provider`, `model`, `status`, `validation_errors`, `is_applyable`, `applied_at`, and `created_at`.
- Confirmed status is limited to `"valid" | "invalid" | "failed"` and nullable timestamps are typed as `string | null`.
- Confirmed endpoint paths, HTTP methods, JSON headers, payload serialization, and `jsonOrError` handling match the brief.
- Confirmed the change is limited to the requested frontend client file plus this report.

## Concerns

- The frontend lint command passes but reports five pre-existing warnings in unrelated UI components.
- No dedicated unit-test harness is configured in `frontend/package.json`; verification was performed with the required production build, lint, and diff checks.
- Git staging and commit were intentionally skipped because `.git` is read-only, per task instructions.

## Diff
diff --git a/frontend/src/lib/content.ts b/frontend/src/lib/content.ts
index bebc79b..686cdb2 100644
--- a/frontend/src/lib/content.ts
+++ b/frontend/src/lib/content.ts
@@ -143,3 +143,57 @@ export async function uploadStaticPdfAsset(
     }),
   );
 }
+
+export interface TemplateAiProposal {
+  id: string;
+  template_id: string;
+  created_by_id: string;
+  instruction: string;
+  input_html: string;
+  input_css: string;
+  proposed_html: string;
+  proposed_css: string;
+  summary: string;
+  provider: string;
+  model: string;
+  status: "valid" | "invalid" | "failed";
+  validation_errors: string[];
+  is_applyable: boolean;
+  applied_at: string | null;
+  created_at: string;
+}
+
+export interface TemplateAiProposalCreatePayload {
+  instruction: string;
+  current_html: string;
+  current_css?: string | null;
+  mock_data?: Record<string, unknown> | null;
+}
+
+export async function createTemplateAiProposal(
+  templateId: string,
+  payload: TemplateAiProposalCreatePayload,
+): Promise<TemplateAiProposal> {
+  return jsonOrError(
+    await apiFetch(`/api/content/templates/${templateId}/ai-proposals`, {
+      method: "POST",
+      headers: { "Content-Type": "application/json" },
+      body: JSON.stringify(payload),
+    }),
+  );
+}
+
+export async function listTemplateAiProposals(templateId: string): Promise<TemplateAiProposal[]> {
+  return jsonOrError(await apiFetch(`/api/content/templates/${templateId}/ai-proposals`));
+}
+
+export async function markTemplateAiProposalApplied(
+  templateId: string,
+  proposalId: string,
+): Promise<TemplateAiProposal> {
+  return jsonOrError(
+    await apiFetch(`/api/content/templates/${templateId}/ai-proposals/${proposalId}/apply`, {
+      method: "POST",
+    }),
+  );
+}

## File: frontend/src/lib/content.ts
`
import { apiFetch, jsonOrError } from "./api";

export interface HtmlTemplateListItem {
  id: string;
  name: string;
  document_type_id: string;
  document_type_name: string;
  token_count: number;
  created_by_email: string;
  created_at: string;
}

export interface HtmlTemplateDetail {
  id: string;
  name: string;
  document_type_id: string;
  document_type_name: string;
  html: string;
  css?: string | null;
  token_names: string[];
  mock_data?: Record<string, unknown> | null;
  created_by_email: string;
  created_at: string;
}

export interface HtmlTemplateCreatePayload {
  document_type_id: string;
  name: string;
  html: string;
  css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export interface StaticPdfAssetListItem {
  id: string;
  filename: string;
  page_count: number;
  document_type_id: string | null;
  document_type_name: string | null;
  created_by_email: string;
  created_at: string;
}

export interface StaticPdfAssetDetail {
  id: string;
  filename: string;
  stored_filename: string;
  stored_path: string;
  page_count: number;
  page_start: number | null;
  page_end: number | null;
  file_size: number;
  document_type_id: string | null;
  document_type_name: string | null;
  created_by_email: string;
  created_at: string;
  download_url: string;
}

export async function listHtmlTemplates(documentTypeId?: string): Promise<HtmlTemplateListItem[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/content/templates${query}`));
}

export async function getHtmlTemplate(id: string): Promise<HtmlTemplateDetail | null> {
  const res = await apiFetch(`/api/content/templates/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function createHtmlTemplate(
  payload: HtmlTemplateCreatePayload,
): Promise<HtmlTemplateDetail> {
  return jsonOrError(
    await apiFetch("/api/content/templates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function updateHtmlTemplate(
  id: string,
  payload: HtmlTemplateCreatePayload,
): Promise<HtmlTemplateDetail> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export interface HtmlTemplatePreviewPayload {
  html: string;
  css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export interface HtmlTemplatePreviewResponse {
  rendered_html: string;
}

export async function previewHtmlTemplate(
  payload: HtmlTemplatePreviewPayload,
): Promise<HtmlTemplatePreviewResponse> {
  return jsonOrError(
    await apiFetch("/api/content/templates/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function listStaticPdfAssets(documentTypeId?: string): Promise<StaticPdfAssetListItem[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/content/static-pdfs${query}`));
}

export async function getStaticPdfAsset(id: string): Promise<StaticPdfAssetDetail | null> {
  const res = await apiFetch(`/api/content/static-pdfs/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function uploadStaticPdfAsset(
  file: File,
  pageStart: number | null,
  pageEnd: number | null,
): Promise<StaticPdfAssetDetail> {
  const formData = new FormData();
  formData.append("file", file);
  if (pageStart !== null) formData.append("page_start", String(pageStart));
  if (pageEnd !== null) formData.append("page_end", String(pageEnd));

  return jsonOrError(
    await apiFetch("/api/content/static-pdfs", {
      method: "POST",
      body: formData,
    }),
  );
}

export interface TemplateAiProposal {
  id: string;
  template_id: string;
  created_by_id: string;
  instruction: string;
  input_html: string;
  input_css: string;
  proposed_html: string;
  proposed_css: string;
  summary: string;
  provider: string;
  model: string;
  status: "valid" | "invalid" | "failed";
  validation_errors: string[];
  is_applyable: boolean;
  applied_at: string | null;
  created_at: string;
}

export interface TemplateAiProposalCreatePayload {
  instruction: string;
  current_html: string;
  current_css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export async function createTemplateAiProposal(
  templateId: string,
  payload: TemplateAiProposalCreatePayload,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function listTemplateAiProposals(templateId: string): Promise<TemplateAiProposal[]> {
  return jsonOrError(await apiFetch(`/api/content/templates/${templateId}/ai-proposals`));
}

export async function markTemplateAiProposalApplied(
  templateId: string,
  proposalId: string,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals/${proposalId}/apply`, {
      method: "POST",
    }),
  );
}
`
