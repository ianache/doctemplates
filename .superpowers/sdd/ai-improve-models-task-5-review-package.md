# Task 5 Review Package

## frontend/src/lib/content.ts
```ts
import { apiFetch, jsonOrError } from "./api";

export interface AiModelOption {
  id: string;
  provider: string;
  label: string;
  requires: string;
}

export interface AiModelCatalog {
  enabled: boolean;
  default_model: string;
  models: AiModelOption[];
}

export async function getAiModels(): Promise<AiModelCatalog> {
  return jsonOrError(await apiFetch("/api/content/ai-models"));
}

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
  model?: string | null;
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
```
