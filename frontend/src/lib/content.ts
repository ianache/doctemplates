import { apiFetch } from "./api";

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
  token_names: string[];
  created_by_email: string;
  created_at: string;
}

export interface HtmlTemplateCreatePayload {
  document_type_id: string;
  name: string;
  html: string;
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

function readErrorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item === "string" ? item : item?.msg ?? JSON.stringify(item)))
        .join("; ");
    }
  }
  return `Unexpected status ${status}`;
}

async function jsonOrError<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
  return res.json();
}

export async function listHtmlTemplates(): Promise<HtmlTemplateListItem[]> {
  return jsonOrError(await apiFetch("/api/content/templates"));
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
