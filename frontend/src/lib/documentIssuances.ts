import { apiFetch, jsonOrError } from "./api";

export type DocumentIssuanceStatus = "success" | "failure";
export type DocumentTracelogType = "generation" | "download" | "share" | string;

export interface DocumentIssuanceFilters {
  design_name?: string;
  id?: string;
  status?: DocumentIssuanceStatus | "";
  created_from?: string;
  created_to?: string;
}

export interface DocumentIssuanceListItem {
  id: string;
  design_version_id: string;
  design_name: string;
  status: DocumentIssuanceStatus;
  design_status: string;
  design_version_number: number | null;
  user_id: string;
  generated_by_email: string;
  input_data: Record<string, unknown>;
  created_at: string;
  preview_url: string;
  download_url: string;
}

export type DocumentIssuanceDetail = DocumentIssuanceListItem;

export interface DocumentTracelog {
  id: string;
  issuance_id: string;
  event_type: DocumentTracelogType;
  user_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ShareDocumentResponse {
  public_url: string;
}

function buildQuery(filters: DocumentIssuanceFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listDocumentIssuances(
  filters: DocumentIssuanceFilters = {},
): Promise<DocumentIssuanceListItem[]> {
  return jsonOrError(await apiFetch(`/api/issuances${buildQuery(filters)}`));
}

export async function getDocumentIssuance(id: string): Promise<DocumentIssuanceDetail | null> {
  const res = await apiFetch(`/api/issuances/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function getDocumentTracelogs(id: string): Promise<DocumentTracelog[]> {
  return jsonOrError(await apiFetch(`/api/issuances/${id}/tracelogs`));
}

export async function shareDocumentIssuance(id: string): Promise<ShareDocumentResponse> {
  return jsonOrError(await apiFetch(`/api/issuances/${id}/share`, { method: "POST" }));
}
