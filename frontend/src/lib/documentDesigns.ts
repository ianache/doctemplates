import { apiFetch } from "./api";

export type DesignStatus = "draft" | "active";
export type DesignBlockType = "html_template" | "static_pdf";

export interface DocumentDesignPage {
  id: string;
  block_type: DesignBlockType;
  content_id: string;
  position: number;
  title: string | null;
  notes: string | null;
  config: Record<string, unknown>;
  snapshot: Record<string, unknown>;
  created_at: string;
}

export interface DocumentDesignListItem {
  id: string;
  name: string;
  description: string | null;
  status: DesignStatus;
  document_type_id: string;
  document_type_name: string;
  page_count: number;
  created_by_email: string;
  created_at: string;
}

export interface DocumentDesignDetail extends Omit<DocumentDesignListItem, "page_count"> {
  pages: DocumentDesignPage[];
}

export interface DocumentDesignCreatePayload {
  document_type_id: string;
  name: string;
  description: string | null;
}

export interface AddTemplatePagePayload {
  template_id: string;
  title?: string | null;
  notes?: string | null;
  config?: Record<string, unknown>;
}

export interface AddStaticPdfPagePayload {
  static_pdf_asset_id: string;
  title?: string | null;
  notes?: string | null;
  config?: Record<string, unknown>;
}

export interface UpdateDesignPagePayload {
  title?: string | null;
  notes?: string | null;
  config?: Record<string, unknown>;
}

function readErrorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
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

export async function listDocumentDesigns(): Promise<DocumentDesignListItem[]> {
  return jsonOrError(await apiFetch("/api/document-designs"));
}

export async function getDocumentDesign(id: string): Promise<DocumentDesignDetail | null> {
  const res = await apiFetch(`/api/document-designs/${id}`);
  if (res.status === 404) return null;
  return jsonOrError(res);
}

export async function createDocumentDesign(
  payload: DocumentDesignCreatePayload,
): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch("/api/document-designs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function addTemplateDesignPage(
  designId: string,
  payload: AddTemplatePagePayload,
): Promise<DocumentDesignPage> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/template`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function addStaticPdfDesignPage(
  designId: string,
  payload: AddStaticPdfPagePayload,
): Promise<DocumentDesignPage> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/static-pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function reorderDesignPages(
  designId: string,
  pageIds: string[],
): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/reorder`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_ids: pageIds }),
    }),
  );
}

export async function updateDesignPage(
  designId: string,
  pageId: string,
  payload: UpdateDesignPagePayload,
): Promise<DocumentDesignPage> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/pages/${pageId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function deleteDesignPage(designId: string, pageId: string): Promise<void> {
  const res = await apiFetch(`/api/document-designs/${designId}/pages/${pageId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
}

export async function activateDocumentDesign(id: string): Promise<DocumentDesignDetail> {
  return jsonOrError(await apiFetch(`/api/document-designs/${id}/activate`, { method: "POST" }));
}
