import { apiFetch } from "./api";

export type FieldType = "string" | "number" | "date" | "boolean";
export type MetadataType = "text" | "number" | "date" | "datetime" | "boolean";

export interface DocumentTypeFieldIn {
  name: string;
  type: FieldType;
  description: string | null;
}

export interface DocumentTypeField extends DocumentTypeFieldIn {
  id: string;
}

export interface DocumentTypeMetadataIn {
  name: string;
  type: MetadataType;
  required: boolean;
}

export interface DocumentTypeMetadata extends DocumentTypeMetadataIn {
  id: string;
}

export interface DocumentTypeListItem {
  id: string;
  name: string;
  description: string | null;
  field_count: number;
  created_by_email: string;
  created_at: string;
}

export interface DocumentTypeDetail {
  id: string;
  name: string;
  description: string | null;
  fields: DocumentTypeField[];
  metadata_definitions: DocumentTypeMetadata[];
  created_by_email: string;
  created_at: string;
}

export interface DocumentTypeCreatePayload {
  name: string;
  description: string | null;
  fields: DocumentTypeFieldIn[];
  metadata_definitions: DocumentTypeMetadataIn[];
}

export async function listDocumentTypes(): Promise<DocumentTypeListItem[]> {
  const res = await apiFetch("/api/document-types");
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json();
}

export async function getDocumentType(id: string): Promise<DocumentTypeDetail | null> {
  const res = await apiFetch(`/api/document-types/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json();
}

export async function createDocumentType(
  payload: DocumentTypeCreatePayload,
): Promise<DocumentTypeDetail> {
  const res = await apiFetch("/api/document-types", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? JSON.stringify(body.detail) : `Unexpected status ${res.status}`);
  }
  return res.json();
}

export async function updateDocumentType(
  id: string,
  payload: DocumentTypeCreatePayload,
): Promise<DocumentTypeDetail> {
  const res = await apiFetch(`/api/document-types/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? JSON.stringify(body.detail) : `Unexpected status ${res.status}`);
  }
  return res.json();
}
