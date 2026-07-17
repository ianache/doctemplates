import { apiFetch, jsonOrError } from "./api";

export interface XlsxTemplateDetail {
  id: string;
  document_type_id: string;
  document_type_name: string;
  name: string;
  description?: string | null;
  original_filename: string;
  detected_sheets: Array<Record<string, unknown>>;
  detected_tokens: string[];
  image_slots: Array<Record<string, unknown>>;
  validation_warnings: Array<Record<string, unknown>>;
  mock_data?: Record<string, unknown> | null;
  created_by_email: string;
  created_at: string;
}

export interface XlsxPreviewResponse {
  sheets: Array<{
    name: string;
    max_row: number;
    max_column: number;
    merged_ranges: string[];
    cells: Array<{
      address: string;
      value: string | number | boolean | null;
      style: Record<string, unknown>;
    }>;
  }>;
  warnings: Array<Record<string, unknown>>;
}

export async function listXlsxTemplates(documentTypeId?: string): Promise<XlsxTemplateDetail[]> {
  const query = documentTypeId ? `?document_type_id=${encodeURIComponent(documentTypeId)}` : "";
  return jsonOrError(await apiFetch(`/api/xlsx-templates${query}`));
}

export async function getXlsxTemplate(id: string): Promise<XlsxTemplateDetail | null> {
  const res = await apiFetch(`/api/xlsx-templates/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function uploadXlsxTemplate(payload: {
  documentTypeId: string;
  name: string;
  description?: string | null;
  file: File;
}): Promise<XlsxTemplateDetail> {
  const formData = new FormData();
  formData.append("document_type_id", payload.documentTypeId);
  formData.append("name", payload.name);
  if (payload.description) formData.append("description", payload.description);
  formData.append("file", payload.file);
  return jsonOrError(await apiFetch("/api/xlsx-templates", { method: "POST", body: formData }));
}

export async function previewXlsxTemplate(
  id: string,
  mockData?: Record<string, unknown>,
): Promise<XlsxPreviewResponse> {
  return jsonOrError(
    await apiFetch(`/api/xlsx-templates/${id}/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mock_data: mockData ?? null }),
    }),
  );
}
