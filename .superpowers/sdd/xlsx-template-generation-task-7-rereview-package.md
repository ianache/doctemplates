# Task 7 Re-Review Package
 M frontend/src/App.tsx
 M frontend/src/lib/documentDesigns.ts
 M frontend/src/lib/documentIssuances.ts
 M frontend/src/lib/documentTypes.ts
 M frontend/src/pages/AuthenticatedShell.tsx
 M frontend/src/pages/content/ContentLibraryPage.tsx
 M frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx
 M frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx
 M frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx
 M frontend/src/pages/document-types/DocumentTypeCreatePage.tsx
?? .superpowers/sdd/xlsx-template-generation-task-7-report.md
?? frontend/src/lib/xlsxTemplates.ts
?? frontend/src/pages/content/XlsxTemplateDetailPage.tsx
?? frontend/src/pages/content/XlsxTemplateUploadPage.tsx
?? frontend/src/pages/content/XlsxTemplatesPage.tsx
?? frontend/src/pages/content/components/XlsxPreviewGrid.tsx

## File: frontend/src/lib/xlsxTemplates.ts
```
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

```

## File: frontend/src/pages/content/XlsxTemplatesPage.tsx
```
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function XlsxTemplatesPage() {
  const [items, setItems] = useState<XlsxTemplateDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listXlsxTemplates()
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "We couldn't load XLSX templates.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Content Library" }, { label: "XLSX Templates" }]}
        title="XLSX Templates"
        actions={
          <Link to="/content/xlsx-templates/upload" className="rounded bg-primary px-md py-xs text-sm font-bold text-on-primary">
            Upload XLSX
          </Link>
        }
      />
      {error ? <p className="mb-md text-sm text-error">{error}</p> : null}
      <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-outline-variant bg-surface-container-low">
              <th className="px-md py-sm text-label-caps text-secondary">Name</th>
              <th className="px-md py-sm text-label-caps text-secondary">Document Type</th>
              <th className="px-md py-sm text-label-caps text-secondary">Tokens</th>
              <th className="px-md py-sm text-label-caps text-secondary">Warnings</th>
              <th className="px-md py-sm text-label-caps text-secondary">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant">
            {(items ?? []).map((item) => (
              <tr key={item.id} className="hover:bg-surface">
                <td className="px-md py-md">
                  <Link className="font-bold text-primary hover:underline" to={`/content/xlsx-templates/${item.id}`}>
                    {item.name}
                  </Link>
                </td>
                <td className="px-md py-md">{item.document_type_name}</td>
                <td className="px-md py-md">{item.detected_tokens.length}</td>
                <td className="px-md py-md">{item.validation_warnings.length}</td>
                <td className="px-md py-md">{new Date(item.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

```

## File: frontend/src/pages/content/XlsxTemplateUploadPage.tsx
```
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listDocumentTypes, type DocumentTypeListItem } from "../../lib/documentTypes";
import { uploadXlsxTemplate } from "../../lib/xlsxTemplates";

export default function XlsxTemplateUploadPage() {
  const navigate = useNavigate();
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listDocumentTypes()
      .then((rows) => {
        if (cancelled) return;
        setDocumentTypes(rows);
        setDocumentTypeId(rows[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load document types.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!file) {
      setError("Choose an XLSX file.");
      return;
    }
    try {
      const created = await uploadXlsxTemplate({
        documentTypeId,
        name,
        description: description || null,
        file,
      });
      navigate(`/content/xlsx-templates/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't upload this workbook.");
    }
  };

  return (
    <section className="rounded border border-outline-variant bg-surface-container-lowest p-lg">
      <h2 className="font-headings text-[18px] font-bold text-on-surface">Upload XLSX Template</h2>
      {error ? <p className="mt-md rounded border border-error/30 p-sm text-sm text-error">{error}</p> : null}
      <form onSubmit={handleSubmit} className="mt-md space-y-md">
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Document Type
          <select
            value={documentTypeId}
            onChange={(event) => setDocumentTypeId(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface"
          >
            {documentTypes.map((documentType) => (
              <option key={documentType.id} value={documentType.id}>
                {documentType.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Name
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface"
          />
        </label>
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface"
          />
        </label>
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          XLSX File
          <input
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-xs block w-full text-sm text-on-surface"
          />
        </label>
        <div className="flex justify-end">
          <button type="submit" className="rounded bg-primary px-lg py-sm text-sm font-bold text-white">
            Upload XLSX
          </button>
        </div>
      </form>
    </section>
  );
}

```

## File: frontend/src/pages/content/XlsxTemplateDetailPage.tsx
```
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import {
  getXlsxTemplate,
  previewXlsxTemplate,
  type XlsxPreviewResponse,
  type XlsxTemplateDetail,
} from "../../lib/xlsxTemplates";
import { XlsxPreviewGrid } from "./components/XlsxPreviewGrid";

export default function XlsxTemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [template, setTemplate] = useState<XlsxTemplateDetail | null>(null);
  const [preview, setPreview] = useState<XlsxPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getXlsxTemplate(id)
      .then((data) => {
        if (cancelled || !data) return;
        setTemplate(data);
        return previewXlsxTemplate(data.id, data.mock_data ?? {});
      })
      .then((data) => {
        if (!cancelled && data) setPreview(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "We couldn't load this template.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!template) {
    return <p className="text-sm text-on-surface-variant">{error ?? "Loading..."}</p>;
  }

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Content Library" }, { label: "XLSX Templates" }]}
        title={template.name}
        actions={
          <Link to="/content/xlsx-templates" className="rounded border border-outline px-md py-xs text-sm font-bold text-primary">
            Back
          </Link>
        }
      />
      {error ? <p className="mb-md text-sm text-error">{error}</p> : null}
      <div className="mb-lg grid gap-md md:grid-cols-3">
        <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <p className="text-label-caps text-secondary">Document Type</p>
          <p className="mt-xs font-bold text-on-surface">{template.document_type_name}</p>
        </div>
        <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <p className="text-label-caps text-secondary">Original File</p>
          <p className="mt-xs font-bold text-on-surface">{template.original_filename}</p>
        </div>
        <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <p className="text-label-caps text-secondary">Validation Warnings</p>
          <p className="mt-xs font-bold text-on-surface">{template.validation_warnings.length}</p>
        </div>
      </div>
      <div className="mb-lg rounded border border-outline-variant bg-surface-container-lowest p-md">
        <p className="mb-sm text-label-caps text-secondary">Detected Tokens</p>
        <div className="flex flex-wrap gap-xs">
          {template.detected_tokens.map((token) => (
            <span key={token} className="rounded bg-surface-container px-sm py-xs font-mono text-xs">
              {token}
            </span>
          ))}
        </div>
      </div>
      <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Preview</h2>
      {preview ? <XlsxPreviewGrid preview={preview} /> : <p className="text-sm text-on-surface-variant">Loading preview...</p>}
    </section>
  );
}

```

## File: frontend/src/pages/content/components/XlsxPreviewGrid.tsx
```
import type { XlsxPreviewResponse } from "../../../lib/xlsxTemplates";

function columnName(index: number): string {
  let value = "";
  let current = index;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    value = String.fromCharCode(65 + remainder) + value;
    current = Math.floor((current - 1) / 26);
  }
  return value;
}

export function XlsxPreviewGrid({ preview }: { preview: XlsxPreviewResponse }) {
  const sheet = preview.sheets[0];
  if (!sheet) {
    return <p className="text-sm text-on-surface-variant">No preview available.</p>;
  }

  const byAddress = new Map(sheet.cells.map((cell) => [cell.address, cell]));
  const columns = Array.from({ length: Math.min(sheet.max_column, 12) }, (_, index) => index + 1);
  const rows = Array.from({ length: Math.min(sheet.max_row, 40) }, (_, index) => index + 1);

  return (
    <div className="overflow-auto rounded border border-outline-variant bg-surface-container-lowest">
      <table className="min-w-full border-collapse text-xs">
        <thead>
          <tr>
            <th className="h-8 w-10 border border-outline-variant bg-surface-container-low" />
            {columns.map((column) => (
              <th
                key={column}
                className="h-8 min-w-24 border border-outline-variant bg-surface-container-low px-2 text-secondary"
              >
                {columnName(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row}>
              <th className="h-8 border border-outline-variant bg-surface-container-low px-2 text-secondary">
                {row}
              </th>
              {columns.map((column) => {
                const address = `${columnName(column)}${row}`;
                const cell = byAddress.get(address);
                return (
                  <td
                    key={column}
                    className="h-8 min-w-24 border border-outline-variant px-2 align-top text-on-surface"
                  >
                    {cell?.value == null ? "" : String(cell.value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

```

## File: frontend/src/App.tsx
```
import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthenticatedShell from "./pages/AuthenticatedShell";
import DocumentTypeListPage from "./pages/document-types/DocumentTypeListPage";
import DocumentTypeDetailPage from "./pages/document-types/DocumentTypeDetailPage";
import DocumentTypeCreatePage from "./pages/document-types/DocumentTypeCreatePage";
import TemplatesPage from "./pages/content/TemplatesPage";
import StaticPdfsPage from "./pages/content/StaticPdfsPage";
import HtmlTemplateCreatePage from "./pages/content/HtmlTemplateCreatePage";
import HtmlTemplateDetailPage from "./pages/content/HtmlTemplateDetailPage";
import StaticPdfUploadPage from "./pages/content/StaticPdfUploadPage";
import StaticPdfDetailPage from "./pages/content/StaticPdfDetailPage";
import XlsxTemplatesPage from "./pages/content/XlsxTemplatesPage";
import XlsxTemplateUploadPage from "./pages/content/XlsxTemplateUploadPage";
import XlsxTemplateDetailPage from "./pages/content/XlsxTemplateDetailPage";
import DocumentDesignListPage from "./pages/document-designs/DocumentDesignListPage";
import DocumentDesignCreatePage from "./pages/document-designs/DocumentDesignCreatePage";
import DocumentDesignDetailPage from "./pages/document-designs/DocumentDesignDetailPage";
import VersionHistoryPage from "./pages/document-designs/VersionHistoryPage";
import DocumentLibraryPage from "./pages/document-issuances/DocumentLibraryPage";
import DocumentIssuanceDetailPage from "./pages/document-issuances/DocumentIssuanceDetailPage";
import JobsMonitoringPage from "./pages/document-issuances/JobsMonitoringPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AuthenticatedShell />}>
        <Route index element={<Navigate to="/document-types" replace />} />
        <Route path="document-types" element={<DocumentTypeListPage />} />
        <Route path="document-types/new" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id/edit" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id" element={<DocumentTypeDetailPage />} />
        <Route path="document-designs" element={<DocumentDesignListPage />} />
        <Route path="document-designs/new" element={<DocumentDesignCreatePage />} />
        <Route path="document-designs/:id" element={<DocumentDesignDetailPage />} />
        <Route path="document-designs/:id/versions" element={<VersionHistoryPage />} />
        <Route path="document-issuances" element={<DocumentLibraryPage />} />
        <Route path="document-issuances/:id" element={<DocumentIssuanceDetailPage />} />
        <Route path="generation-jobs" element={<JobsMonitoringPage />} />
        <Route path="content/templates" element={<TemplatesPage />} />
        <Route path="content/templates/new" element={<HtmlTemplateCreatePage />} />
        <Route path="content/templates/:id" element={<HtmlTemplateDetailPage />} />
        <Route path="content/templates/:id/edit" element={<HtmlTemplateCreatePage />} />
        <Route path="content/static" element={<StaticPdfsPage />} />
        <Route path="content/static-pdfs/upload" element={<StaticPdfUploadPage />} />
        <Route path="content/static-pdfs/:id" element={<StaticPdfDetailPage />} />
        <Route path="content/xlsx-templates" element={<XlsxTemplatesPage />} />
        <Route path="content/xlsx-templates/upload" element={<XlsxTemplateUploadPage />} />
        <Route path="content/xlsx-templates/:id" element={<XlsxTemplateDetailPage />} />
      </Route>
    </Routes>
  );
}

export default App;

```

## File: frontend/src/pages/AuthenticatedShell.tsx
```
import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { type CurrentUser, fetchCurrentUser, logout } from "../lib/api";


const ROUTE_LABELS: Record<string, string> = {
  "document-types": "Document Types",
  "document-designs": "Document Designs",
  "document-issuances": "Documents Library",
  "generation-jobs": "Generation Jobs",
  content: "Content Library",
  new: "New",
  versions: "Version History",
  templates: "Templates",
  "static-pdfs": "Static PDFs",
  "xlsx-templates": "XLSX Templates",
  static: "Static PDFs",
  upload: "Upload",
};

function initialsFromEmail(email: string): string {
  if (!email) return "?";
  const [local] = email.split("@");
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return local.slice(0, 2).toUpperCase();
}

function buildBreadcrumbs(pathname: string): { label: string; to: string }[] {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return [];
  const crumbs: { label: string; to: string }[] = [];
  let acc = "";
  for (const seg of segments) {
    acc += `/${seg}`;
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(seg);
    const label = ROUTE_LABELS[seg] ?? (isUuid ? seg.slice(0, 8) + "…" : seg);
    crumbs.push({ label, to: acc });
  }
  return crumbs;
}

export default function AuthenticatedShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [hoverExpanded, setHoverExpanded] = useState(false);
  const [contentMenuOpen, setContentMenuOpen] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      try {
        const currentUser = await fetchCurrentUser();
        if (cancelled) return;
        if (currentUser === null) {
          navigate("/login?error=session_expired");
          return;
        }
        setUser(currentUser);
      } catch {
        if (!cancelled) navigate("/login?error=session_expired");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadUser();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const handleSignOut = async () => {
    await logout();
    navigate("/login");
  };

  const breadcrumbs = useMemo(() => buildBreadcrumbs(location.pathname), [location.pathname]);

  const sidebarExpanded = !collapsed || hoverExpanded;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-body text-body-md text-on-surface">
      <aside
        className={`flex h-full shrink-0 flex-col border-r border-outline-variant bg-surface-container-lowest py-md transition-all duration-200 ${
          sidebarExpanded ? "w-panel-width-side" : "w-[64px]"
        }`}
        onMouseEnter={() => collapsed && setHoverExpanded(true)}
        onMouseLeave={() => setHoverExpanded(false)}
      >
        <nav className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden px-sm">
          {/* Document Types */}
          <NavLink
            to="/document-types"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Document Types"
          >
            <span className="material-symbols-outlined shrink-0">schema</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Document Types
            </span>
          </NavLink>

          {/* Content Library (Dropdown/Submenu) */}
          <div className="space-y-1">
            <button
              onClick={() => sidebarExpanded && setContentMenuOpen(!contentMenuOpen)}
              className={`w-full flex items-center justify-between rounded px-sm py-sm text-secondary hover:bg-surface-container transition-colors`}
              title="Content Library"
              type="button"
            >
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined shrink-0">library_books</span>
                <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
                  Content Library
                </span>
              </div>
              {sidebarExpanded && (
                <span className="material-symbols-outlined text-sm transition-transform duration-200">
                  {contentMenuOpen ? "expand_less" : "expand_more"}
                </span>
              )}
            </button>

            {/* Submenu Items */}
            {sidebarExpanded && contentMenuOpen && (
              <div className="pl-6 space-y-1">
                <NavLink
                  to="/content/templates"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="Templates"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">description</span>
                  <span className="text-body-sm whitespace-nowrap">Templates</span>
                </NavLink>
                <NavLink
                  to="/content/static"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="Static PDFs"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">picture_as_pdf</span>
                  <span className="text-body-sm whitespace-nowrap">Static PDFs</span>
                </NavLink>
                <NavLink
                  to="/content/xlsx-templates"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                      isActive
                        ? "bg-surface-container font-bold text-primary"
                        : "text-secondary hover:bg-surface-container"
                    }`
                  }
                  title="XLSX Templates"
                >
                  <span className="material-symbols-outlined text-[18px] shrink-0">table</span>
                  <span className="text-body-sm whitespace-nowrap">XLSX Templates</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Document Designs */}
          <NavLink
            to="/document-designs"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Document Designs"
          >
            <span className="material-symbols-outlined shrink-0">dashboard_customize</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Document Designs
            </span>
          </NavLink>

          {/* Generation Jobs */}
          <NavLink
            to="/generation-jobs"
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Generation Jobs"
          >
            <span className="material-symbols-outlined shrink-0">list_alt</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Generation Jobs
            </span>
          </NavLink>

          {/* Documents Library */}
          <NavLink
            to="/document-issuances"
            end
            className={({ isActive }) =>
              `flex items-center gap-3 rounded px-sm py-sm transition-colors ${
                isActive
                  ? "bg-surface-container font-bold text-primary"
                  : "text-secondary hover:bg-surface-container"
              }`
            }
            title="Documents Library"
          >
            <span className="material-symbols-outlined shrink-0">folder_open</span>
            <span className={`whitespace-nowrap transition-opacity duration-200 ${sidebarExpanded ? "opacity-100" : "w-0 overflow-hidden opacity-0"}`}>
              Documents Library
            </span>
          </NavLink>
        </nav>

        <div className="space-y-1 border-t border-outline-variant px-sm pt-md">
          <span
            className="flex cursor-default items-center gap-3 rounded px-sm py-sm text-secondary"
            title="Support"
          >
            <span className="material-symbols-outlined shrink-0">help</span>
            <span className={`whitespace-nowrap text-body-sm ${sidebarExpanded ? "opacity-100" : "opacity-0"}`}>
              Support
            </span>
          </span>
          <span
            className="flex cursor-default items-center gap-3 rounded px-sm py-sm text-secondary"
            title="Logs"
          >
            <span className="material-symbols-outlined shrink-0">history</span>
            <span className={`whitespace-nowrap text-body-sm ${sidebarExpanded ? "opacity-100" : "opacity-0"}`}>
              Logs
            </span>
          </span>
        </div>
      </aside>

      {loading ? null : (
        <main className="flex h-screen flex-1 flex-col overflow-hidden">
          <header className="z-50 flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface px-lg">
            <div className="flex items-center gap-md">
              <button
                className="rounded p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                onClick={() => setCollapsed((v) => !v)}
                title={collapsed ? "Expand menu" : "Collapse menu"}
                type="button"
              >
                <span className="material-symbols-outlined">menu</span>
              </button>
              <Link
                to="/"
                className="rounded p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Home"
              >
                <span className="material-symbols-outlined">home</span>
              </Link>
              {breadcrumbs.length > 0 ? (
                <nav className="flex items-center gap-sm">
                  {breadcrumbs.map((crumb, idx) => (
                    <span key={crumb.to} className="flex items-center gap-sm">
                      {idx > 0 ? (
                        <span className="material-symbols-outlined text-sm text-secondary">chevron_right</span>
                      ) : null}
                      <Link
                        to={crumb.to}
                        className={`text-body-sm transition-colors ${
                          idx === breadcrumbs.length - 1
                            ? "font-bold text-on-surface"
                            : "text-secondary hover:text-primary"
                        }`}
                      >
                        {crumb.label}
                      </Link>
                    </span>
                  ))}
                </nav>
              ) : null}
            </div>

            <div className="flex items-center gap-md">
              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-3 text-body-sm text-secondary">
                  search
                </span>
                <input
                  className="w-64 rounded-full border border-outline bg-surface-container-low py-1.5 pl-10 pr-4 text-body-sm focus:border-primary focus:outline-none"
                  placeholder="Global search..."
                  type="text"
                />
              </div>
              <button
                className="rounded-full p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Notifications"
                type="button"
              >
                <span className="material-symbols-outlined">notifications</span>
              </button>
              <button
                className="rounded-full p-2 text-secondary transition-colors hover:bg-surface-container active:scale-95"
                title="Sync status"
                type="button"
              >
                <span className="material-symbols-outlined">cloud_done</span>
              </button>
              <div className="mx-1 h-8 w-px bg-outline-variant" />
              {user ? (
                <div className="flex items-center gap-sm">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-outline bg-primary text-label-caps font-bold text-on-primary">
                    {initialsFromEmail(user.email)}
                  </div>
                  <button
                    className="rounded border border-outline-variant px-md py-xs text-label-caps text-secondary transition-colors hover:border-outline hover:text-primary"
                    type="button"
                    onClick={handleSignOut}
                  >
                    Sign out
                  </button>
                </div>
              ) : null}
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-lg">
            <div className="w-full">
              <Outlet />
            </div>
          </div>
        </main>
      )}
    </div>
  );
}

```

## File: frontend/src/pages/content/ContentLibraryPage.tsx
```
import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import {
  listHtmlTemplates,
  listStaticPdfAssets,
  type HtmlTemplateListItem,
  type StaticPdfAssetListItem,
} from "../../lib/content";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function ContentLibraryPage() {
  const [templates, setTemplates] = useState<HtmlTemplateListItem[] | null>(null);
  const [pdfAssets, setPdfAssets] = useState<StaticPdfAssetListItem[] | null>(null);
  const [xlsxTemplates, setXlsxTemplates] = useState<XlsxTemplateDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([listHtmlTemplates(), listStaticPdfAssets(), listXlsxTemplates()])
      .then(([templateRows, pdfRows, xlsxRows]) => {
        if (cancelled) return;
        setTemplates(templateRows);
        setPdfAssets(pdfRows);
        setXlsxTemplates(xlsxRows);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load the content library. Please try again.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Admin" }, { label: "Content Library" }]}
        title="Content Library"
        actions={
          <>
            <Link
              to="/content/templates/new"
              className="rounded bg-primary px-md py-xs font-bold uppercase tracking-wide text-label-caps text-on-primary hover:opacity-90 active:scale-95"
            >
              Create Template
            </Link>
            <Link
              to="/content/static-pdfs/upload"
              className="rounded border border-primary px-md py-xs font-bold uppercase tracking-wide text-label-caps text-primary hover:bg-primary/10"
            >
              Upload PDF
            </Link>
            <Link
              to="/content/xlsx-templates/upload"
              className="rounded border border-primary px-md py-xs font-bold uppercase tracking-wide text-label-caps text-primary hover:bg-primary/10"
            >
              Upload XLSX
            </Link>
          </>
        }
      />

      {error ? <p className="text-sm text-error">{error}</p> : null}

      <div className="space-y-xl">
        {/* TEMPLATES */}
        <section id="templates">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h3 className="font-headings text-headline-md text-on-surface">Templates</h3>
            <Link to="/content/templates/new" className="text-sm font-bold text-primary hover:underline">
              New Template
            </Link>
          </div>

          {templates === null ? null : templates.length === 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No templates yet</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Name</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Document Type</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Tokens</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created By</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {templates.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-surface">
                      <td className="px-md py-md">
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-primary">description</span>
                          <Link to={`/content/templates/${item.id}`} className="font-bold text-primary hover:underline">
                            {item.name}
                          </Link>
                        </div>
                      </td>
                      <td className="px-md py-md text-on-surface">{item.document_type_name}</td>
                      <td className="px-md py-md text-on-surface">{item.token_count}</td>
                      <td className="px-md py-md text-on-surface">{item.created_by_email}</td>
                      <td className="px-md py-md text-on-surface">
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex items-center justify-between border-t border-outline-variant bg-surface-container-low p-md">
                <p className="text-body-sm text-secondary">
                  <span className="font-bold text-on-surface">{templates.length}</span> templates
                </p>
              </div>
            </div>
          )}
        </section>

        <section id="xlsx-templates">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h3 className="font-headings text-headline-md text-on-surface">XLSX Templates</h3>
            <Link to="/content/xlsx-templates/upload" className="text-sm font-bold text-primary hover:underline">
              Upload XLSX
            </Link>
          </div>

          {xlsxTemplates === null ? null : xlsxTemplates.length === 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No XLSX templates yet</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Name</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Document Type</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Tokens</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Warnings</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {xlsxTemplates.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-surface">
                      <td className="px-md py-md">
                        <Link to={`/content/xlsx-templates/${item.id}`} className="font-bold text-primary hover:underline">
                          {item.name}
                        </Link>
                      </td>
                      <td className="px-md py-md text-on-surface">{item.document_type_name}</td>
                      <td className="px-md py-md text-on-surface">{item.detected_tokens.length}</td>
                      <td className="px-md py-md text-on-surface">{item.validation_warnings.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* STATIC PDFs */}
        <section id="static-pdfs">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h3 className="font-headings text-headline-md text-on-surface">Static PDFs</h3>
            <Link to="/content/static-pdfs/upload" className="text-sm font-bold text-primary hover:underline">
              Upload PDF
            </Link>
          </div>

          {pdfAssets === null ? null : pdfAssets.length === 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No PDF assets yet</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-outline-variant bg-surface-container-low">
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Filename</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Pages</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created By</th>
                    <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant">
                  {pdfAssets.map((item) => (
                    <tr key={item.id} className="transition-colors hover:bg-surface">
                      <td className="px-md py-md">
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-primary">picture_as_pdf</span>
                          <Link to={`/content/static-pdfs/${item.id}`} className="font-bold text-primary hover:underline">
                            {item.filename}
                          </Link>
                        </div>
                      </td>
                      <td className="px-md py-md text-on-surface">{item.page_count}</td>
                      <td className="px-md py-md text-on-surface">{item.created_by_email}</td>
                      <td className="px-md py-md text-on-surface">
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex items-center justify-between border-t border-outline-variant bg-surface-container-low p-md">
                <p className="text-body-sm text-secondary">
                  <span className="font-bold text-on-surface">{pdfAssets.length}</span> PDF assets
                </p>
              </div>
            </div>
          )}
        </section>
      </div>

      <div className="mt-xl">
        <Outlet />
      </div>
    </section>
  );
}

```

## File: frontend/src/lib/documentTypes.ts
```
import { apiFetch } from "./api";

export type FieldType = "string" | "number" | "date" | "boolean";
export type MetadataType = "text" | "number" | "date" | "datetime" | "boolean";
export type OutputFormat = "pdf" | "xlsx";

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
  allowed_output_formats: OutputFormat[];
  created_by_email: string;
  created_at: string;
}

export interface DocumentTypeCreatePayload {
  name: string;
  description: string | null;
  fields: DocumentTypeFieldIn[];
  metadata_definitions: DocumentTypeMetadataIn[];
  allowed_output_formats: OutputFormat[];
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

```

## File: frontend/src/lib/documentDesigns.ts
```
import { apiFetch, jsonOrError, readErrorMessage } from "./api";
import type { OutputFormat } from "./documentTypes";

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
  output_format: OutputFormat;
  xlsx_template_id: string | null;
  status: DesignStatus | "superseded";
  version_group_id: string | null;
  version_number: number | null;
  document_type_id: string;
  document_type_name: string;
  page_count: number;
  created_by_email: string;
  created_at: string;
}

export interface DocumentDesignDetail extends Omit<DocumentDesignListItem, "page_count"> {
  pages: DocumentDesignPage[];
  mock_data?: Record<string, unknown> | null;
}

export interface DocumentDesignCreatePayload {
  document_type_id: string;
  name: string;
  description: string | null;
  output_format?: OutputFormat;
  xlsx_template_id?: string | null;
  mock_data?: Record<string, unknown> | null;
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

export async function forkDocumentDesignVersion(designId: string): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/versions`, {
      method: "POST",
    }),
  );
}

export async function listDocumentDesignVersions(designId: string): Promise<DocumentDesignListItem[]> {
  return jsonOrError(await apiFetch(`/api/document-designs/${designId}/versions`));
}

export async function discardDocumentDesignDraft(designId: string): Promise<void> {
  const res = await apiFetch(`/api/document-designs/${designId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
}

export async function previewDocumentDesign(
  designId: string,
  payload: Record<string, unknown>,
): Promise<Blob> {
  const res = await apiFetch(`/api/document-designs/${designId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(readErrorMessage(body, res.status));
  }
  return res.blob();
}

export interface DocumentDesignUpdatePayload {
  name: string;
  description: string | null;
  output_format?: OutputFormat;
  xlsx_template_id?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export async function updateDocumentDesign(
  id: string,
  payload: DocumentDesignUpdatePayload,
): Promise<DocumentDesignDetail> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function generateDocumentDesign(
  designId: string,
  payload: Record<string, unknown> = {},
): Promise<any> {
  return jsonOrError(
    await apiFetch(`/api/document-designs/${designId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

```

## File: frontend/src/lib/documentIssuances.ts
```
import { apiFetch, jsonOrError } from "./api";

export type DocumentIssuanceStatus = "queued" | "processing" | "success" | "failure";
export type DocumentTracelogType = "generation" | "download" | "share" | string;

export interface DocumentIssuanceFilters {
  design_name?: string;
  id?: string;
  status?: DocumentIssuanceStatus | "";
  created_from?: string;
  created_to?: string;
  metadata_key?: string;
  metadata_value?: string;
}

export interface DocumentIssuanceListItem {
  id: string;
  design_version_id: string;
  design_name: string;
  output_format: "pdf" | "xlsx";
  mime_type?: string | null;
  filename?: string | null;
  preview_storage_key?: string | null;
  status: DocumentIssuanceStatus;
  design_status: string;
  design_version_number: number | null;
  user_id: string;
  generated_by_email: string;
  input_data: Record<string, unknown>;
  metadata_values: Record<string, unknown> | null;
  created_at: string;
  preview_url: string;
  download_url: string;
  celery_task_id?: string | null;
  error_message?: string | null;
  queued_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  retry_count?: number;
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

```

## File: frontend/src/pages/document-types/DocumentTypeCreatePage.tsx
```
import { useEffect, useState, useMemo } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";

import { createDocumentType, getDocumentType, updateDocumentType, type DocumentTypeCreatePayload, type FieldType, type DocumentTypeMetadataIn, type OutputFormat } from "../../lib/documentTypes";
import { SchemaFieldEditor } from "./components/organisms/SchemaFieldEditor";
import { SchemaMetadataEditor } from "./components/organisms/SchemaMetadataEditor";
import { validateSchemaFields, normalizeSchemaFields } from "../../lib/schemaFields";

type FieldRow = {
  name: string;
  type: FieldType;
  description: string | null;
};

type FormValues = {
  name: string;
  description: string;
  fields: FieldRow[];
  metadata_definitions: DocumentTypeMetadataIn[];
  allowed_output_formats: OutputFormat[];
};

function generateMockPayload(fields: FieldRow[], metadata: DocumentTypeMetadataIn[]) {
  const data: Record<string, any> = {};
  fields.forEach(f => {
    if (!f.name) return;
    const parts = f.name.split(".");
    let current = data;
    parts.forEach((part, index) => {
      const isList = part.endsWith("[]");
      const cleanName = isList ? part.slice(0, -2) : part;
      
      if (index === parts.length - 1) {
        if (isList) {
          current[cleanName] = [f.type === "number" ? 123 : f.type === "boolean" ? true : f.type === "date" ? "2026-07-11" : "Sample"];
        } else {
          current[cleanName] = f.type === "number" ? 123 : f.type === "boolean" ? true : f.type === "date" ? "2026-07-11" : "Sample";
        }
      } else {
        if (isList) {
          if (!current[cleanName]) current[cleanName] = [{}];
          current = current[cleanName][0];
        } else {
          if (!current[cleanName]) current[cleanName] = {};
          current = current[cleanName];
        }
      }
    });
  });

  const meta: Record<string, any> = {};
  metadata.forEach(m => {
    if (!m.name) return;
    meta[m.name] = m.type === "number" ? 123.45 : m.type === "boolean" ? true : m.type === "date" ? "2026-07-11" : m.type === "datetime" ? "2026-07-11T20:00:00Z" : "Sample Text";
  });

  return { data, metadata: meta };
}

function getCurlCode(typeId: string, payload: any, firstMetaName: string): string {
  return `# 1. Generar Documento
curl -X POST "http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -d '${JSON.stringify(payload, null, 2)}'

# 2. Buscar por Metadatos
curl -X GET "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"`;
}

function getJSCode(typeId: string, payload: any, firstMetaName: string): string {
  return `// 1. Generar Documento
const generateDoc = async () => {
  const res = await fetch("http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer YOUR_ACCESS_TOKEN"
    },
    body: JSON.stringify(${JSON.stringify(payload, null, 2).replace(/\n/g, "\n      ")})
  });
  const data = await res.json();
  console.log(data);
};

// 2. Buscar por Metadatos
const searchDocs = async () => {
  const url = "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}";
  const res = await fetch(url, {
    headers: {
      "Authorization": "Bearer YOUR_ACCESS_TOKEN"
    }
  });
  const list = await res.json();
  console.log(list);
};`;
}

function getPythonCode(typeId: string, payload: any, firstMetaName: string): string {
  return `import requests

# 1. Generar Documento
url = "http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}
payload = ${JSON.stringify(payload, null, 4)}

response = requests.post(url, json=payload, headers=headers)
print("Creado:", response.json())

# 2. Buscar por Metadatos
search_url = "http://localhost:8000/api/issuances"
params = {
    "document_type_id": "${typeId}"${firstMetaName ? `,
    "metadata.${firstMetaName}": "Sample"` : ""}
}
response = requests.get(search_url, params=params, headers=headers)
print("Documentos:", response.json())`;
}

function getJavaCode(typeId: string, payload: any, firstMetaName: string): string {
  return `import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class DocGen {
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newHttpClient();

        // 1. Generar Documento
        String payload = """
${JSON.stringify(payload, null, 4)}
        """;

        HttpRequest reqGen = HttpRequest.newBuilder()
            .uri(URI.create("http://localhost:8000/api/document-designs/YOUR_DESIGN_ID/generate"))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer YOUR_ACCESS_TOKEN")
            .POST(HttpRequest.BodyPublishers.ofString(payload))
            .build();

        HttpResponse<String> resGen = client.send(reqGen, HttpResponse.BodyHandlers.ofString());
        System.out.println("Generado: " + resGen.body());

        // 2. Buscar por Metadatos
        String queryUrl = "http://localhost:8000/api/issuances?document_type_id=${typeId}${firstMetaName ? `&metadata.${firstMetaName}=Sample` : ""}";
        HttpRequest reqQuery = HttpRequest.newBuilder()
            .uri(URI.create(queryUrl))
            .header("Authorization", "Bearer YOUR_ACCESS_TOKEN")
            .GET()
            .build();

        HttpResponse<String> resQuery = client.send(reqQuery, HttpResponse.BodyHandlers.ofString());
        System.out.println("Busqueda: " + resQuery.body());
    }
}`;
}

export default function DocumentTypeCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [loading, setLoading] = useState(isEdit);
  const [activeLang, setActiveLang] = useState<"curl" | "js" | "py" | "java">("curl");
  
  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: "",
      description: "",
      fields: [{ name: "new_field", type: "string", description: "" }],
      metadata_definitions: [],
      allowed_output_formats: ["pdf"],
    },
  });

  const { append, remove, update } = useFieldArray({ control, name: "fields" });
  const { append: appendMeta, remove: removeMeta } = useFieldArray({ control, name: "metadata_definitions" });

  // Watch fields and metadata definitions dynamically
  const watchedFields = watch("fields") || [];
  const watchedMetadata = watch("metadata_definitions") || [];

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getDocumentType(id)
      .then((data) => {
        if (data) {
          reset({
            name: data.name,
            description: data.description || "",
            fields: data.fields.map((f) => ({
              name: f.name,
              type: f.type,
              description: f.description || "",
            })),
            metadata_definitions: data.metadata_definitions.map((m) => ({
              name: m.name,
              type: m.type,
              required: m.required,
            })),
            allowed_output_formats: data.allowed_output_formats ?? ["pdf"],
          });
        }
      })
      .catch((err) => {
        setSubmitError(err instanceof Error ? err.message : "Failed to load document type.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(null);

    const validationError = validateSchemaFields(values.fields);
    if (validationError) {
      setSubmitError(validationError);
      return;
    }

    const normalizedFields = normalizeSchemaFields(values.fields);
    const allowedOutputFormats = values.allowed_output_formats.filter(
      (format): format is OutputFormat => format === "pdf" || format === "xlsx",
    );

    try {
      const payload: DocumentTypeCreatePayload = {
        name: values.name,
        description: values.description || null,
        fields: normalizedFields,
        metadata_definitions: values.metadata_definitions,
        allowed_output_formats: allowedOutputFormats.length ? allowedOutputFormats : (["pdf"] as OutputFormat[]),
      };
      const saved = isEdit
        ? await updateDocumentType(id!, payload)
        : await createDocumentType(payload);
      navigate(`/document-types/${saved.id}`);
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "We couldn't save this document type. Check the fields below and try again."
      );
    }
  });

  // Calculate dynamic mock payload and snippets
  const mockPayload = useMemo(() => {
    return generateMockPayload(watchedFields, watchedMetadata);
  }, [watchedFields, watchedMetadata]);

  const firstMetaName = useMemo(() => {
    return watchedMetadata[0]?.name || "";
  }, [watchedMetadata]);

  const snippetCode = useMemo(() => {
    const typeId = id || "YOUR_DOCUMENT_TYPE_ID";
    if (activeLang === "curl") return getCurlCode(typeId, mockPayload, firstMetaName);
    if (activeLang === "js") return getJSCode(typeId, mockPayload, firstMetaName);
    if (activeLang === "py") return getPythonCode(typeId, mockPayload, firstMetaName);
    return getJavaCode(typeId, mockPayload, firstMetaName);
  }, [activeLang, id, mockPayload, firstMetaName]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
      </div>
    );
  }

  return (
    <section>
      <div className="flex items-center justify-between">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          {isEdit ? "Edit Document Type" : "New Document Type"}
        </h1>
        {isEdit && (
          <Link
            to={`/document-types/${id}`}
            className="text-sm font-bold text-primary hover:underline flex items-center gap-xs"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span> Cancel
          </Link>
        )}
      </div>

      <div className={isEdit ? "grid grid-cols-[1fr_400px] gap-lg items-start mt-xl" : "mt-xl"}>
        {/* Left Column: Form */}
        <form
          onSubmit={onSubmit}
          className="rounded-lg border border-outline-variant bg-surface-container-lowest p-lg shadow-sm"
        >
          {submitError ? (
            <div className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
              {submitError}
            </div>
          ) : null}

          <div className="space-y-md mb-lg">
            <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
              Name
              <input
                {...register("name", { required: "Name is required." })}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                placeholder="e.g. Invoice, Contract"
              />
            </label>
            {errors.name ? <p className="text-sm text-error">{errors.name.message}</p> : null}

            <label className="block text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
              Description
              <textarea
                {...register("description")}
                rows={3}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white"
                placeholder="Describe the purpose of this document type..."
              />
            </label>
          </div>

          <fieldset className="mb-lg rounded border border-outline-variant p-md">
            <legend className="px-xs text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Output Formats
            </legend>
            <div className="flex gap-md">
              <label className="flex items-center gap-xs text-sm text-on-surface">
                <input type="checkbox" value="pdf" {...register("allowed_output_formats")} />
                PDF
              </label>
              <label className="flex items-center gap-xs text-sm text-on-surface">
                <input type="checkbox" value="xlsx" {...register("allowed_output_formats")} />
                XLSX
              </label>
            </div>
          </fieldset>

          {/* Visual Schema Tree Builder */}
          <div className="mt-lg">
            <SchemaFieldEditor
              register={register}
              control={control}
              append={append}
              remove={remove}
              update={update}
            />
          </div>

          {/* Visual Metadata Builder */}
          <SchemaMetadataEditor
            register={register}
            control={control}
            append={appendMeta}
            remove={removeMeta}
          />

          <div className="mt-lg flex justify-end">
            <button
              type="submit"
              className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
            >
              {isEdit ? "Save Changes" : "Create Document Type"}
            </button>
          </div>
        </form>

        {/* Right Column: API Integration Panel (Only visible on Edit screen) */}
        {isEdit && (
          <aside className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md sticky top-4 max-h-[750px] overflow-y-auto flex flex-col gap-sm shadow-sm select-none">
            <div className="border-b border-outline-variant pb-xs">
              <h3 className="font-headings text-[14px] font-bold text-on-surface flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">api</span>
                INTEGRATION CODE EXAMPLES
              </h3>
              <p className="text-[11px] text-secondary mt-xs leading-relaxed">
                Connect your codebase to generate and query documents using this schema.
              </p>
            </div>

            {/* Language Selection Badges / Tabs */}
            <div className="flex flex-wrap gap-xs border border-outline-variant p-0.5 rounded-md bg-surface-container-low select-none">
              {(["curl", "js", "py", "java"] as const).map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => setActiveLang(lang)}
                  className={`flex-1 text-center py-1 rounded text-xs font-bold transition-all ${
                    activeLang === lang
                      ? "bg-white text-primary shadow-sm"
                      : "text-secondary hover:text-on-surface"
                  }`}
                >
                  {lang === "curl" ? "cURL" : lang === "js" ? "JS" : lang === "py" ? "Python" : "Java"}
                </button>
              ))}
            </div>

            {/* Code Workspace */}
            <div className="flex-1 min-h-0 relative">
              <pre className="w-full bg-slate-900 text-slate-100 p-sm rounded-lg font-mono text-[11px] leading-relaxed overflow-x-auto select-all max-h-[480px]">
                <code>{snippetCode}</code>
              </pre>
            </div>

            {/* Info badge */}
            <div className="rounded bg-surface-container p-xs border border-outline-variant text-[10px] leading-relaxed text-secondary">
              <div className="font-bold text-on-surface mb-0.5 flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] text-primary">key</span>
                Cookie Session Authentication
              </div>
              These endpoints require cookie authentication. Supply the session cookie <code className="bg-white px-0.5 border rounded font-mono">docmanagement_session</code> in your request headers.
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}

```

## File: frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx
```
import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createDocumentDesign } from "../../lib/documentDesigns";
import { getDocumentType, listDocumentTypes, type DocumentTypeDetail, type DocumentTypeListItem, type OutputFormat } from "../../lib/documentTypes";
import { listXlsxTemplates, type XlsxTemplateDetail } from "../../lib/xlsxTemplates";

export default function DocumentDesignCreatePage() {
  const navigate = useNavigate();
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [xlsxTemplates, setXlsxTemplates] = useState<XlsxTemplateDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("pdf");
  const [xlsxTemplateId, setXlsxTemplateId] = useState("");
  const [mockDataJson, setMockDataJson] = useState("");
  const [mockDataError, setMockDataError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listDocumentTypes()
      .then((rows) => {
        if (cancelled) return;
        setDocumentTypes(rows);
        setDocumentTypeId(rows[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setSubmitError("We couldn't load document types.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!documentTypeId) return;
    let cancelled = false;
    Promise.all([getDocumentType(documentTypeId), listXlsxTemplates(documentTypeId)])
      .then(([documentType, templates]) => {
        if (cancelled) return;
        setSelectedDocumentType(documentType);
        setXlsxTemplates(templates);
        const allowed = documentType?.allowed_output_formats ?? ["pdf"];
        if (!allowed.includes(outputFormat)) {
          setOutputFormat(allowed[0] ?? "pdf");
        }
        setXlsxTemplateId(templates[0]?.id ?? "");
      })
      .catch(() => {
        if (!cancelled) setSubmitError("We couldn't load format options.");
      });
    return () => {
      cancelled = true;
    };
  }, [documentTypeId, outputFormat]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!documentTypeId) {
      setSubmitError("Choose a document type.");
      return;
    }
    if (outputFormat === "xlsx" && !xlsxTemplateId) {
      setSubmitError("Choose an XLSX template before creating this design.");
      return;
    }

    let parsedMock: Record<string, unknown> | null = null;
    if (mockDataJson.trim()) {
      try {
        parsedMock = JSON.parse(mockDataJson);
        if (typeof parsedMock !== "object" || parsedMock === null || Array.isArray(parsedMock)) {
          setSubmitError("Mock Data JSON must be a valid JSON object.");
          return;
        }
      } catch (err) {
        setSubmitError(`Mock Data JSON has syntax errors: ${err instanceof Error ? err.message : "Error"}`);
        return;
      }
    }

    try {
      const created = await createDocumentDesign({
        document_type_id: documentTypeId,
        name,
        description: description || null,
        output_format: outputFormat,
        xlsx_template_id: outputFormat === "xlsx" ? xlsxTemplateId : null,
        mock_data: parsedMock,
      });
      navigate(`/document-designs/${created.id}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We couldn't save this design.");
    }
  };

  return (
    <section>
      <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
        New Document Design
      </h1>

      <form
        onSubmit={handleSubmit}
        className="mt-xl rounded border border-outline-variant bg-surface-container-lowest p-lg"
      >
        {submitError ? (
          <p className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
            {submitError}
          </p>
        ) : null}

        <div className="space-y-md">
          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Document Type
            <select
              value={documentTypeId}
              onChange={(event) => setDocumentTypeId(event.target.value)}
              disabled={loading}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {loading ? <option>Loading...</option> : null}
              {!loading && documentTypes.length === 0 ? (
                <option value="">No document types available</option>
              ) : null}
              {documentTypes.map((documentType) => (
                <option key={documentType.id} value={documentType.id}>
                  {documentType.name}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Output Format
            <select
              value={outputFormat}
              onChange={(event) => setOutputFormat(event.target.value as OutputFormat)}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {(selectedDocumentType?.allowed_output_formats ?? ["pdf"]).map((format) => (
                <option key={format} value={format}>
                  {format.toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          {outputFormat === "xlsx" ? (
            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              XLSX Template
              <select
                value={xlsxTemplateId}
                onChange={(event) => setXlsxTemplateId(event.target.value)}
                className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
              >
                {xlsxTemplates.length === 0 ? <option value="">No XLSX templates available</option> : null}
                {xlsxTemplates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Mock JSON Payload (Optional)
            <textarea
              value={mockDataJson}
              onChange={(event) => {
                setMockDataJson(event.target.value);
                try {
                  if (event.target.value.trim()) {
                    JSON.parse(event.target.value);
                    setMockDataError(null);
                  } else {
                    setMockDataError(null);
                  }
                } catch (err) {
                  setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
                }
              }}
              rows={6}
              placeholder={`{\n  "cliente": {\n    "nombre": "Juan Pérez",\n    "edad": 30\n  }\n}`}
              className={`mt-xs w-full rounded border font-mono text-xs px-sm py-xs bg-white focus:outline-none ${
                mockDataError ? "border-error focus:border-error" : "border-outline focus:border-primary"
              }`}
            />
            {mockDataError && (
              <p className="text-xs text-error mt-xs font-mono">{mockDataError}</p>
            )}
          </label>
        </div>

        <div className="mt-lg flex justify-end">
          <button
            type="submit"
            className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
          >
            Create Design
          </button>
        </div>
      </form>
    </section>
  );
}

```

## File: frontend/src/pages/document-designs/DocumentDesignDetailPage.tsx
```
import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import {
  activateDocumentDesign,
  addStaticPdfDesignPage,
  addTemplateDesignPage,
  deleteDesignPage,
  discardDocumentDesignDraft,
  forkDocumentDesignVersion,
  getDocumentDesign,
  listDocumentDesignVersions,
  reorderDesignPages,
  updateDesignPage,
  previewDocumentDesign,
  updateDocumentDesign,
  type DocumentDesignDetail,
  type DocumentDesignListItem,
  type DocumentDesignPage,
} from "../../lib/documentDesigns";
import { getDocumentType, type DocumentTypeField, type DocumentTypeMetadata } from "../../lib/documentTypes";
import { generateMockDataFromFields } from "../../lib/schemaFields";
import AddContentModal from "./components/organisms/AddContentModal";
import DesignPageCard from "./components/molecules/DesignPageCard";
import DesignPageInspector from "./components/organisms/DesignPageInspector";
import { MockDataPanel } from "./components/organisms/MockDataPanel";
import { PreviewFrame } from "./components/organisms/PreviewFrame";

function sortPages(pages: DocumentDesignPage[]) {
  return [...pages].sort((a, b) => a.position - b.position);
}

function pageLabel(page: DocumentDesignPage | null) {
  if (!page) return "No page selected";
  if (page.title) return page.title;
  if (page.block_type === "html_template") return String(page.snapshot.name ?? "HTML template");
  return String(page.snapshot.filename ?? "Static PDF");
}

function pageMetadata(page: DocumentDesignPage | null) {
  if (!page) return "Select a fragment from the stack";
  if (page.block_type === "html_template") {
    const tokens = Array.isArray(page.snapshot.token_names) ? page.snapshot.token_names : [];
    return tokens.length ? `${tokens.length} token${tokens.length === 1 ? "" : "s"}` : "No tokens";
  }

  const pageCount = Number(page.snapshot.page_count ?? 0);
  const pageStart = page.snapshot.page_start;
  const pageEnd = page.snapshot.page_end;
  const range = pageStart && pageEnd ? `, pages ${pageStart}-${pageEnd}` : "";
  return `${pageCount} page${pageCount === 1 ? "" : "s"}${range}`;
}

function statusLabel(status: string) {
  if (status === "active") return "Current";
  return status;
}

function mergeMockData(
  loaded: Record<string, any>,
  fields: DocumentTypeField[],
  metadata: DocumentTypeMetadata[]
): Record<string, any> {
  const freshData = generateMockDataFromFields(fields);
  const freshMetadata: Record<string, any> = {};
  metadata.forEach((m) => {
    if (m.type === "number") freshMetadata[m.name] = 123.45;
    else if (m.type === "boolean") freshMetadata[m.name] = true;
    else if (m.type === "date") freshMetadata[m.name] = new Date().toISOString().split("T")[0];
    else if (m.type === "datetime") freshMetadata[m.name] = new Date().toISOString();
    else freshMetadata[m.name] = "Sample Text";
  });

  const loadedIsStructured = loaded && typeof loaded.data === "object" && loaded.data !== null && !Array.isArray(loaded.data);
  const needsStructure = metadata.length > 0;

  if (needsStructure) {
    const targetData = loadedIsStructured ? { ...loaded.data } : { ...loaded };
    const targetMetadata = loadedIsStructured && typeof loaded.metadata === "object" && loaded.metadata !== null ? { ...loaded.metadata } : {};

    // Remove metadata keys from targetData if they accidentally leaked there
    metadata.forEach((m) => {
      delete targetData[m.name];
    });

    // Fill missing data keys
    Object.keys(freshData).forEach((key) => {
      if (targetData[key] === undefined) {
        targetData[key] = freshData[key];
      }
    });

    // Fill missing metadata keys
    Object.keys(freshMetadata).forEach((key) => {
      if (targetMetadata[key] === undefined) {
        targetMetadata[key] = freshMetadata[key];
      }
    });

    return { data: targetData, metadata: targetMetadata };
  } else {
    const targetData = loadedIsStructured ? { ...loaded.data } : { ...loaded };
    Object.keys(freshData).forEach((key) => {
      if (targetData[key] === undefined) {
        targetData[key] = freshData[key];
      }
    });
    return targetData;
  }
}

export default function DocumentDesignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [design, setDesign] = useState<DocumentDesignDetail | null | undefined>(undefined);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [modalMode, setModalMode] = useState<"template" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<DocumentDesignPage | null>(null);
  const [versions, setVersions] = useState<DocumentDesignListItem[]>([]);
  const [showDiscardModal, setShowDiscardModal] = useState(false);
  const [discarding, setDiscarding] = useState(false);

  const [docTypeFields, setDocTypeFields] = useState<DocumentTypeField[]>([]);
  const [metadataDefs, setMetadataDefs] = useState<DocumentTypeMetadata[]>([]);
  const [mockJsonText, setMockJsonText] = useState<string>("{}");
  const [parsedPayload, setParsedPayload] = useState<Record<string, unknown>>({});
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [isSavingMock, setIsSavingMock] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);
  const [previewMode, setPreviewMode] = useState<"fragment" | "pdf">("fragment");
  const [activeRightTab, setActiveRightTab] = useState<"inspector" | "mockData">("inspector");

  const [leftWidth, setLeftWidth] = useState(380);
  const [rightWidth, setRightWidth] = useState(330);
  const [isResizing, setIsResizing] = useState(false);

  const handleLeftMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = leftWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.max(260, Math.min(600, startWidth + deltaX));
      setLeftWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleRightMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = rightWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = startX - moveEvent.clientX;
      const newWidth = Math.max(260, Math.min(600, startWidth + deltaX));
      setRightWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleSetPreviewMode = (mode: "fragment" | "pdf") => {
    setPreviewMode(mode);
    setActiveRightTab(mode === "pdf" ? "mockData" : "inspector");
  };

  const handleSetActiveRightTab = (tab: "inspector" | "mockData") => {
    setActiveRightTab(tab);
    setPreviewMode(tab === "mockData" ? "pdf" : "fragment");
  };

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getDocumentDesign(id)
      .then((data) => {
        if (cancelled) return;
        setDesign(data);
        setSelectedPageId(data?.pages[0]?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load this design.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!design?.id) return;
    listDocumentDesignVersions(design.id)
      .then(setVersions)
      .catch(() => {});
  }, [design?.id]);

  useEffect(() => {
    if (location.state?.justForked && location.state?.sourceVersion !== undefined) {
      setNotice(
        `New draft created from version ${location.state.sourceVersion}. Changes here won't affect the current version until you activate this one.`,
      );
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    if (!design?.document_type_id) return;
    let cancelled = false;
    getDocumentType(design.document_type_id)
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setDocTypeFields(data.fields);
          setMetadataDefs(data.metadata_definitions || []);
          let loadedMock: Record<string, unknown> | null = null;
          if (design?.id) {
            try {
              const saved = localStorage.getItem(`mock_payload_${design.id}`);
              if (saved) {
                const parsed = JSON.parse(saved);
                if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
                  loadedMock = parsed as Record<string, unknown>;
                }
              } else if (design.mock_data) {
                loadedMock = design.mock_data;
              }
            } catch (err) {
              console.error("Failed to parse saved mock payload", err);
            }
          }

          let initialMock: Record<string, any>;
          if (loadedMock) {
            initialMock = mergeMockData(loadedMock, data.fields, data.metadata_definitions || []);
            // Save the merged mock back to localStorage to keep it up to date
            localStorage.setItem(`mock_payload_${design.id}`, JSON.stringify(initialMock));
          } else {
            const mockData = generateMockDataFromFields(data.fields);
            if (data.metadata_definitions && data.metadata_definitions.length > 0) {
              const mockMetadata: Record<string, any> = {};
              data.metadata_definitions.forEach((meta) => {
                if (meta.type === "number") mockMetadata[meta.name] = 123.45;
                else if (meta.type === "boolean") mockMetadata[meta.name] = true;
                else if (meta.type === "date") mockMetadata[meta.name] = new Date().toISOString().split("T")[0];
                else if (meta.type === "datetime") mockMetadata[meta.name] = new Date().toISOString();
                else mockMetadata[meta.name] = "Sample Text";
              });
              initialMock = { data: mockData, metadata: mockMetadata };
            } else {
              initialMock = mockData;
            }
          }

          const text = JSON.stringify(initialMock, null, 2);
          setMockJsonText(text);
          setParsedPayload(initialMock);
          setJsonError(null);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setPreviewError("Could not load schema fields for preview setup.");
      });
    return () => {
      cancelled = true;
    };
  }, [design?.document_type_id, design?.id]);

  const handleResetMockData = () => {
    const mockData = generateMockDataFromFields(docTypeFields);
    let initialMock: Record<string, any> = mockData;
    if (metadataDefs && metadataDefs.length > 0) {
      const mockMetadata: Record<string, any> = {};
      metadataDefs.forEach((meta) => {
        if (meta.type === "number") mockMetadata[meta.name] = 123.45;
        else if (meta.type === "boolean") mockMetadata[meta.name] = true;
        else if (meta.type === "date") mockMetadata[meta.name] = new Date().toISOString().split("T")[0];
        else if (meta.type === "datetime") mockMetadata[meta.name] = new Date().toISOString();
        else mockMetadata[meta.name] = "Sample Text";
      });
      initialMock = { data: mockData, metadata: mockMetadata };
    }

    const text = JSON.stringify(initialMock, null, 2);
    setMockJsonText(text);
    setParsedPayload(initialMock);
    setJsonError(null);
    if (design?.id) {
      localStorage.removeItem(`mock_payload_${design.id}`);
    }
  };

  const handleMockJsonChange = (text: string) => {
    setMockJsonText(text);
    try {
      if (!text.trim()) {
        setJsonError("JSON payload cannot be empty");
        return;
      }
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        setJsonError("JSON root must be an object");
      } else {
        setParsedPayload(parsed);
        setJsonError(null);
        if (design?.id) {
          localStorage.setItem(`mock_payload_${design.id}`, JSON.stringify(parsed));
        }
      }
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "Invalid JSON syntax");
    }
  };

  const handleTriggerPdfPreview = async () => {
    if (!design) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const blob = await previewDocumentDesign(design.id, parsedPayload);
      setPreviewBlob(blob);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to generate PDF preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveMockData = async () => {
    if (!design) return;
    setIsSavingMock(true);
    setPreviewError(null);
    try {
      const updated = await updateDocumentDesign(design.id, {
        name: design.name,
        description: design.description,
        output_format: design.output_format,
        xlsx_template_id: design.xlsx_template_id,
        mock_data: parsedPayload,
      });
      setDesign(updated);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to persist mock data to server.");
    } finally {
      setIsSavingMock(false);
    }
  };

  const pages = useMemo(() => sortPages(design?.pages ?? []), [design?.pages]);
  const selectedPage = pages.find((page) => page.id === selectedPageId) ?? null;
  const existingPdfIds = useMemo(
    () => pages.filter((page) => page.block_type === "static_pdf").map((page) => page.content_id),
    [pages],
  );
  const readOnly = design ? design.status !== "draft" : true;
  const activeVersion = useMemo(() => versions.find((v) => v.status === "active"), [versions]);

  const setPages = (nextPages: DocumentDesignPage[]) => {
    setDesign((current) =>
      current ? { ...current, pages: nextPages.map((page, index) => ({ ...page, position: index })) } : current,
    );
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    if (!design || event.over === null || event.active.id === event.over.id) return;

    const oldIndex = pages.findIndex((page) => page.id === event.active.id);
    const newIndex = pages.findIndex((page) => page.id === event.over?.id);
    if (oldIndex < 0 || newIndex < 0) return;

    const previousPages = pages;
    const nextPages = arrayMove(pages, oldIndex, newIndex).map((page, index) => ({
      ...page,
      position: index,
    }));
    setPages(nextPages);
    setError(null);
    try {
      const updated = await reorderDesignPages(design.id, nextPages.map((page) => page.id));
      setDesign(updated);
    } catch (err) {
      setPages(previousPages);
      setError(err instanceof Error ? err.message : "We couldn't save the page order.");
    }
  };

  const handleAddTemplate = async (templateId: string) => {
    if (!design) return;
    const page = await addTemplateDesignPage(design.id, { template_id: templateId });
    setDesign({ ...design, pages: [...pages, page] });
    setSelectedPageId(page.id);
    setNotice("Template page added.");
  };

  const handleAddPdf = async (assetId: string) => {
    if (!design) return;
    const page = await addStaticPdfDesignPage(design.id, { static_pdf_asset_id: assetId });
    setDesign({ ...design, pages: [...pages, page] });
    setSelectedPageId(page.id);
    setNotice("PDF page added.");
  };

  const handleSavePage = async (
    pageId: string,
    values: { title: string | null; notes: string | null; config: Record<string, unknown> },
  ) => {
    if (!design) return;
    const updatedPage = await updateDesignPage(design.id, pageId, values);
    setDesign({
      ...design,
      pages: pages.map((page) => (page.id === pageId ? updatedPage : page)),
    });
    setNotice("Page saved.");
  };

  const handleRemove = (page: DocumentDesignPage) => {
    setPendingRemove(page);
    setPages(pages.filter((candidate) => candidate.id !== page.id));
    if (selectedPageId === page.id) setSelectedPageId(null);
    setNotice("Page removed locally. Undo or confirm removal.");
  };

  const undoRemove = () => {
    if (!pendingRemove) return;
    setPages([...pages, pendingRemove].sort((a, b) => a.position - b.position));
    setSelectedPageId(pendingRemove.id);
    setPendingRemove(null);
    setNotice("Page restored.");
  };

  const confirmRemove = async () => {
    if (!design || !pendingRemove) return;
    try {
      await deleteDesignPage(design.id, pendingRemove.id);
      setPendingRemove(null);
      setNotice("Page removal saved.");
    } catch (err) {
      setPages([...pages, pendingRemove].sort((a, b) => a.position - b.position));
      setError(err instanceof Error ? err.message : "We couldn't remove this page.");
      setPendingRemove(null);
    }
  };

  const handleActivate = async () => {
    if (!design) return;
    setError(null);
    try {
      const updated = await activateDocumentDesign(design.id);
      setDesign(updated);
      if (updated.version_number && updated.version_number > 1) {
        setNotice(
          `Version ${updated.version_number} is now current. Version ${updated.version_number - 1} has been preserved in version history.`,
        );
      } else {
        setNotice("Design activated.");
      }
      const hist = await listDocumentDesignVersions(updated.id);
      setVersions(hist);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't activate this design.");
    }
  };

  const handleEditDesign = async () => {
    if (!design) return;
    setError(null);
    try {
      const draft = await forkDocumentDesignVersion(design.id);
      navigate(`/document-designs/${draft.id}`, {
        state: { justForked: true, sourceVersion: design.version_number },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't create a new version. Try again.");
    }
  };

  const handleDiscardDraft = async () => {
    if (!design) return;
    setDiscarding(true);
    setError(null);
    try {
      await discardDocumentDesignDraft(design.id);
      setShowDiscardModal(false);
      const groupId = design.version_group_id || design.id;
      navigate(`/document-designs/${groupId}/versions`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't discard this draft. Try again.");
    } finally {
      setDiscarding(false);
    }
  };

  if (error && design === undefined) return <p className="text-sm text-error">{error}</p>;
  if (design === undefined) return null;

  if (design === null) {
    return (
      <div className="text-center">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
          Document design not found.
        </h1>
        <Link
          to="/document-designs"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Designs
        </Link>
      </div>
    );
  }

  return (
    <section className="-m-lg flex min-h-[calc(100vh-4rem)] overflow-hidden bg-surface-container">
      <aside
        className="flex min-h-0 flex-col bg-surface-bright shrink-0"
        style={{ width: leftWidth }}
      >
        <div className="border-b border-outline-variant p-lg">
          <div className="flex items-start justify-between gap-md">
            <div className="min-w-0">
              <h1 className="truncate font-headings text-headline-lg font-bold text-on-surface">
                {design.name}
              </h1>
              <p className="mt-xs line-clamp-2 text-body-sm text-on-surface-variant">
                {design.description || "No description"}
              </p>
            </div>
            <span className="shrink-0 rounded bg-surface-container-high px-sm py-xs text-label-caps font-bold uppercase text-primary">
              {statusLabel(design.status)}
            </span>
          </div>

          <div className="mt-lg grid grid-cols-2 gap-md text-body-sm">
            <div>
              <p className="font-label-caps text-on-surface-variant">Document Type</p>
              <p className="mt-base font-bold text-on-surface">{design.document_type_name}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Created By</p>
              <p className="mt-base truncate text-on-surface">{design.created_by_email}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Created At</p>
              <p className="mt-base text-on-surface">{new Date(design.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Fragments</p>
              <p className="mt-base text-on-surface">{pages.length}</p>
            </div>
          </div>

          <div className="mt-lg flex flex-wrap gap-sm">
            {design.status === "draft" ? (
              <>
                <button
                  type="button"
                  className="rounded border border-error px-md py-xs text-body-sm font-bold text-error hover:bg-error/10"
                  onClick={() => setShowDiscardModal(true)}
                >
                  Discard
                </button>
                <button
                  type="button"
                  className="rounded bg-primary px-md py-xs text-body-sm font-bold text-white hover:bg-primary/90"
                  onClick={handleActivate}
                >
                  Activate
                </button>
              </>
            ) : null}
            {design.status === "active" ? (
              <button
                type="button"
                className="rounded bg-primary px-md py-xs text-body-sm font-bold text-white hover:bg-primary/90"
                onClick={handleEditDesign}
              >
                Edit Design
              </button>
            ) : null}
            <Link
              to={`/document-designs/${design.id}/versions`}
              className="rounded border border-primary px-md py-xs text-body-sm font-bold text-primary hover:bg-primary/10"
            >
              Version History
            </Link>
          </div>

          {design.status === "superseded" && activeVersion ? (
            <div className="mt-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-body-sm font-bold text-on-surface">
              Past version.{" "}
              <Link to={`/document-designs/${activeVersion.id}`} className="text-primary hover:underline">
                View current version
              </Link>
            </div>
          ) : null}

          {error ? <p className="mt-md rounded border border-error/30 p-sm text-body-sm text-error">{error}</p> : null}
          {notice ? (
            <div className="mt-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-body-sm text-on-surface">
              <div className="flex flex-wrap items-center justify-between gap-sm">
                <span>{notice}</span>
                {pendingRemove ? (
                  <span className="flex gap-sm">
                    <button type="button" className="font-bold text-primary" onClick={undoRemove}>
                      Undo
                    </button>
                    <button type="button" className="font-bold text-error" onClick={confirmRemove}>
                      Confirm
                    </button>
                  </span>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>

        <div className="flex min-h-0 flex-1 flex-col p-md">
          <div className="mb-md flex items-center justify-between gap-sm">
            <div>
              <h2 className="font-headings text-headline-md text-on-surface">Fragments</h2>
              <p className="text-body-sm text-on-surface-variant">Ordered document body</p>
            </div>
            {!readOnly ? (
              <div className="flex gap-xs">
                <button
                  type="button"
                  className="rounded bg-primary px-sm py-xs text-label-caps font-bold text-white hover:bg-primary/90"
                  onClick={() => setModalMode("template")}
                >
                  Template
                </button>
                <button
                  type="button"
                  className="rounded border border-primary px-sm py-xs text-label-caps font-bold text-primary hover:bg-primary/10"
                  onClick={() => setModalMode("pdf")}
                >
                  PDF
                </button>
              </div>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto pr-xs">
            {pages.length === 0 ? (
              <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
                <p className="font-headings text-headline-md font-bold text-on-surface">Empty fragment stack</p>
                <p className="mt-xs text-body-sm text-on-surface-variant">
                  Add a template or static PDF page to start composing this design.
                </p>
              </div>
            ) : readOnly ? (
              <div className="space-y-sm">
                {pages.map((page) => (
                  <DesignPageCard
                    key={page.id}
                    page={page}
                    selected={page.id === selectedPageId}
                    onSelect={setSelectedPageId}
                    onRemove={handleRemove}
                    readOnly={true}
                  />
                ))}
              </div>
            ) : (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={pages.map((page) => page.id)} strategy={verticalListSortingStrategy}>
                  <div className="space-y-sm">
                    {pages.map((page) => (
                      <DesignPageCard
                        key={page.id}
                        page={page}
                        selected={page.id === selectedPageId}
                        onSelect={setSelectedPageId}
                        onRemove={handleRemove}
                        readOnly={false}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            )}
          </div>
        </div>
      </aside>

      {/* Left Resize Handle */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-primary/45 active:bg-primary transition-colors h-full shrink-0 z-40 border-r border-outline-variant hover:border-transparent"
        onMouseDown={handleLeftMouseDown}
      />

      <main className="flex min-h-[640px] flex-1 flex-col overflow-hidden bg-surface-container">
        <div className="flex items-center justify-between gap-md border-b border-outline-variant bg-surface px-lg py-md">
          <div className="min-w-0">
            <p className="font-label-caps text-on-surface-variant">
              {previewMode === "pdf"
                ? "Generated PDF"
                : selectedPage
                ? `Page ${selectedPage.position + 1}`
                : "Preview"}
            </p>
            <h2 className="truncate font-headings text-headline-md text-on-surface">
              {previewMode === "pdf" ? "Document Previsualization" : pageLabel(selectedPage)}
            </h2>
          </div>
          <div className="flex items-center gap-md">
            <div className="flex border border-outline-variant rounded bg-surface-container-low p-[2px]">
              <button
                type="button"
                className={`rounded px-sm py-xs text-xs font-bold ${
                  previewMode === "fragment"
                    ? "bg-surface text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
                onClick={() => handleSetPreviewMode("fragment")}
              >
                Fragment Preview
              </button>
              <button
                type="button"
                className={`rounded px-sm py-xs text-xs font-bold ${
                  previewMode === "pdf"
                    ? "bg-surface text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
                onClick={() => handleSetPreviewMode("pdf")}
              >
                PDF Preview
              </button>
            </div>
            {previewMode === "fragment" && (
              <span className="rounded border border-outline-variant bg-surface-container-low px-sm py-xs text-label-caps text-on-surface-variant">
                {pageMetadata(selectedPage)}
              </span>
            )}
          </div>
        </div>

        <div className={`page-canvas-bg flex min-h-0 flex-1 items-start justify-center overflow-auto p-xl ${isResizing ? 'pointer-events-none' : ''}`}>
          {previewMode === "pdf" ? (
            <div className="w-full max-w-[800px] bg-surface-container-lowest p-md border border-outline-variant rounded-lg shadow-lg">
              <PreviewFrame blob={previewBlob} loading={previewLoading} error={previewError} />
            </div>
          ) : (
            <div className="flex min-h-[760px] w-full max-w-[595px] flex-col border border-outline-variant bg-white p-xl shadow-lg">
              {selectedPage ? (
                selectedPage.block_type === "html_template" && typeof selectedPage.snapshot.html === "string" ? (
                  <iframe
                    title={`Preview ${pageLabel(selectedPage)}`}
                    className="h-full min-h-[680px] w-full flex-1 border-0 bg-white"
                    srcDoc={`
                      <style>
                        body {
                          font-family: Helvetica, Arial, sans-serif;
                          font-size: 10pt;
                          line-height: 1.4;
                        }
                        ${selectedPage.snapshot.css || ""}
                      </style>
                      ${selectedPage.snapshot.html || ""}
                    `}
                  />
                ) : (
                  <div className="flex flex-1 flex-col items-center justify-center gap-md text-center">
                    <span className="material-symbols-outlined text-[56px] text-primary">picture_as_pdf</span>
                    <div>
                      <h3 className="font-headings text-headline-md text-on-surface">{pageLabel(selectedPage)}</h3>
                      <p className="mt-xs text-body-sm text-on-surface-variant">{pageMetadata(selectedPage)}</p>
                    </div>
                  </div>
                )
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center gap-md text-center">
                  <span className="material-symbols-outlined text-[56px] text-on-surface-variant">
                    dashboard_customize
                  </span>
                  <div>
                    <h3 className="font-headings text-headline-md text-on-surface">Select a fragment</h3>
                    <p className="mt-xs text-body-sm text-on-surface-variant">
                      The selected page preview appears here.
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-auto flex justify-between border-t border-outline-variant pt-md text-[10px] text-on-surface-variant">
                <span>Precision Archival</span>
                <span>{selectedPage ? `Page ${selectedPage.position + 1} of ${pages.length}` : `${pages.length} pages`}</span>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Right Resize Handle */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-primary/45 active:bg-primary transition-colors h-full shrink-0 z-40 border-l border-outline-variant hover:border-transparent"
        onMouseDown={handleRightMouseDown}
      />

      <aside
        className="min-h-0 overflow-y-auto bg-surface p-md flex flex-col gap-md shrink-0"
        style={{ width: rightWidth }}
      >
        <div className="flex border border-outline-variant rounded bg-surface-container-low p-[2px] shrink-0">
          <button
            type="button"
            className={`flex-1 rounded py-xs text-xs font-bold text-center ${
              activeRightTab === "inspector"
                ? "bg-surface text-primary shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => handleSetActiveRightTab("inspector")}
          >
            Page Inspector
          </button>
          <button
            type="button"
            className={`flex-1 rounded py-xs text-xs font-bold text-center ${
              activeRightTab === "mockData"
                ? "bg-surface text-primary shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => handleSetActiveRightTab("mockData")}
          >
            Mock Data Preview
          </button>
        </div>

        <div className="flex-1 min-h-0">
          {activeRightTab === "inspector" ? (
            <DesignPageInspector page={selectedPage} onSave={handleSavePage} readOnly={readOnly} />
          ) : (
            <>
              {previewError ? (
                <div className="mb-sm text-xs text-error bg-error/5 border border-error/20 p-xs rounded font-mono">
                  {previewError}
                </div>
              ) : null}
              <MockDataPanel
                value={mockJsonText}
                onChange={handleMockJsonChange}
                onReset={handleResetMockData}
                onPreview={handleTriggerPdfPreview}
                onSave={handleSaveMockData}
                isValidJson={!jsonError}
                parseError={jsonError}
                loadingPreview={previewLoading}
                isSavingMock={isSavingMock}
              />
            </>
          )}
        </div>
      </aside>

      {modalMode ? (
        <AddContentModal
          mode={modalMode}
          documentTypeId={design.document_type_id}
          existingPdfIds={existingPdfIds}
          onClose={() => setModalMode(null)}
          onAddTemplate={handleAddTemplate}
          onAddPdf={handleAddPdf}
        />
      ) : null}

      {showDiscardModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-md">
          <div className="w-full max-w-xl rounded border border-outline-variant bg-surface-container-lowest p-lg shadow-xl">
            <div className="flex items-center justify-between gap-md">
              <h2 className="font-headings text-[14px] font-bold text-on-surface">
                Discard this draft?
              </h2>
              <button
                type="button"
                className="text-sm font-bold text-primary"
                onClick={() => setShowDiscardModal(false)}
                disabled={discarding}
              >
                Close
              </button>
            </div>

            <p className="mt-md text-sm text-on-surface">
              Changes since version {design.version_number ? design.version_number - 1 : 1} will be lost. Version{" "}
              {design.version_number ? design.version_number - 1 : 1} itself stays intact and remains the current
              version.
            </p>

            {error ? <p className="mt-md text-sm text-error">{error}</p> : null}

            <div className="mt-lg flex justify-end gap-sm">
              <button
                type="button"
                className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface"
                onClick={() => setShowDiscardModal(false)}
                disabled={discarding}
              >
                Keep Editing
              </button>
              <button
                type="button"
                disabled={discarding}
                className="rounded bg-error px-md py-xs text-sm font-bold text-white hover:bg-error/90 disabled:opacity-50"
                onClick={handleDiscardDraft}
              >
                {discarding ? "Discarding..." : "Discard Draft"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

```

## File: frontend/src/pages/document-issuances/DocumentIssuanceDetailPage.tsx
```
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import IssuanceProperties from "../../components/molecules/IssuanceProperties";
import { API_BASE_URL, apiFetch } from "../../lib/api";
import {
  getDocumentIssuance,
  getDocumentTracelogs,
  shareDocumentIssuance,
  type DocumentIssuanceDetail,
  type DocumentTracelog,
} from "../../lib/documentIssuances";

const EVENT_LABELS: Record<string, string> = {
  generation: "Generated",
  download: "Downloaded",
  share: "Shared",
};

function clipboardUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  if (API_BASE_URL) return `${API_BASE_URL}${path}`;
  return `${window.location.origin}${path}`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function metadataValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export default function DocumentIssuanceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<DocumentIssuanceDetail | null | undefined>(undefined);
  const [tracelogs, setTracelogs] = useState<DocumentTracelog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    let timeoutId: any = null;
    let pollCount = 0;

    const fetchStatus = () => {
      Promise.all([getDocumentIssuance(id), getDocumentTracelogs(id)])
        .then(([issuance, logs]) => {
          if (cancelled) return;
          setDetail(issuance);
          setTracelogs(logs);

          if (issuance && (issuance.status === "queued" || issuance.status === "processing")) {
            pollCount++;
            const delay = pollCount <= 30 ? 2000 : 5000;
            timeoutId = setTimeout(fetchStatus, delay);
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : "We couldn't load this document issuance.");
          }
        });
    };

    fetchStatus();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [id]);

  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!detail || detail.status !== "success" || detail.output_format !== "pdf") {
      setBlobUrl(null);
      setPreviewError(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setBlobUrl(null);
    setPreviewError(null);
    apiFetch(detail.preview_url)
      .then((res) => {
        if (!res.ok) throw new Error(`Preview failed (${res.status})`);
        return res.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) {
          setPreviewError(err instanceof Error ? err.message : "Failed to load PDF preview.");
        }
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [detail]);

  const handleDownload = async () => {
    if (!detail) return;
    setDownloading(true);
    setError(null);
    try {
      const res = await apiFetch(detail.download_url);
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = detail.filename ?? `${detail.design_name}.${detail.output_format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      const logs = await getDocumentTracelogs(detail.id);
      setTracelogs(logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't download this document.");
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = async () => {
    if (!detail) return;
    setSharing(true);
    setError(null);
    setNotice(null);
    try {
      const response = await shareDocumentIssuance(detail.id);
      const url = clipboardUrl(response.public_url);
      await navigator.clipboard.writeText(url);
      setNotice("Public share URL copied.");
      const logs = await getDocumentTracelogs(detail.id);
      setTracelogs(logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't create or copy the share URL.");
    } finally {
      setSharing(false);
    }
  };

  if (error && detail === undefined) return <p className="text-sm text-error">{error}</p>;
  if (detail === undefined) return null;

  if (detail === null) {
    return (
      <div className="text-center">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
          Document issuance not found.
        </h1>
        <Link
          to="/document-issuances"
          className="mt-lg inline-block rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          Back to Documents Library
        </Link>
      </div>
    );
  }

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Operations" }, { label: "Documents Library", to: "/document-issuances" }, { label: detail.design_name }]}
        title={detail.design_name}
        actions={
          <>
            <button
              type="button"
              className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50"
              onClick={handleDownload}
              disabled={downloading || detail.status !== "success"}
            >
              {downloading ? "Downloading..." : `Download ${detail.output_format.toUpperCase()}`}
            </button>
            <button
              type="button"
              className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10 disabled:opacity-50"
              onClick={handleShare}
              disabled={sharing || detail.status !== "success"}
            >
              {sharing ? "Sharing..." : "Share"}
            </button>
          </>
        }
      />

      {error ? <p className="mb-md rounded border border-error/30 p-sm text-sm text-error">{error}</p> : null}
      {notice ? (
        <p className="mb-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-sm text-on-surface">
          {notice}
        </p>
      ) : null}

      <div className="grid gap-lg lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-lg">
          <div>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">
              {detail.output_format === "pdf" ? "PDF Preview" : "Generated Workbook"}
            </h2>
            {detail.status === "failure" ? (
              <div className="rounded-lg border border-error bg-surface-container-low p-lg text-center">
                <span className="material-symbols-outlined text-[48px] text-error mb-2">error</span>
                <h3 className="font-headings text-[18px] font-bold text-on-surface mb-2">Generation Failed</h3>
                <p className="text-sm text-error max-w-lg mx-auto font-mono bg-surface-container-lowest p-md rounded border border-outline-variant">
                  {detail.error_message || "An unknown error occurred during document generation."}
                </p>
              </div>
            ) : previewError ? (
              <p className="rounded border border-error/30 p-md text-sm text-error">{previewError}</p>
            ) : detail.output_format !== "pdf" && detail.status === "success" ? (
              <div className="flex h-[320px] w-full flex-col items-center justify-center gap-md rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined text-[40px] text-primary">table</span>
                <p className="text-sm font-bold text-secondary">Preview is available after download.</p>
              </div>
            ) : blobUrl ? (
              <iframe
                title={`PDF preview for ${detail.design_name}`}
                src={blobUrl}
                className="h-[720px] w-full rounded border border-outline-variant bg-surface-container-lowest"
              />
            ) : detail.status === "queued" || detail.status === "processing" ? (
              <div className="flex h-[720px] w-full flex-col items-center justify-center gap-md rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined animate-spin text-[32px] text-primary">progress_activity</span>
                <p className="text-sm font-bold text-secondary">
                  {detail.status === "queued" ? "Waiting in queue..." : `Generating ${detail.output_format.toUpperCase()} document...`}
                </p>
              </div>
            ) : (
              <div className="flex h-[720px] w-full items-center justify-center rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-lg">
          <IssuanceProperties detail={detail} />
          {detail.metadata_values && Object.keys(detail.metadata_values).length > 0 && (
            <section>
              <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Document Metadata</h2>
              <div className="rounded border border-outline-variant bg-surface-container-lowest p-md text-sm text-on-surface">
                <dl className="divide-y divide-outline-variant/40">
                  {Object.entries(detail.metadata_values).map(([key, value]) => (
                    <div key={key} className="py-xs flex justify-between gap-md">
                      <dt className="font-mono text-xs text-on-surface-variant font-semibold">{key}</dt>
                      <dd className="text-on-surface text-right font-semibold">
                        {typeof value === "boolean" ? (value ? "True" : "False") : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Input Data</h2>
            <pre className="max-h-80 overflow-auto rounded border border-outline-variant bg-surface-container-lowest p-md text-xs leading-5 text-on-surface">
              {JSON.stringify(detail.input_data, null, 2)}
            </pre>
          </section>

          <section>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Audit Timeline</h2>
            {tracelogs.length === 0 ? (
              <p className="rounded border border-outline-variant bg-surface-container-lowest p-md text-sm text-on-surface-variant">
                No tracelog events recorded.
              </p>
            ) : (
              <ol className="space-y-sm">
                {tracelogs.map((log) => (
                  <li key={log.id} className="border-l-2 border-outline-variant pl-md">
                    <div className="flex items-start justify-between gap-sm">
                      <div>
                        <div className="font-bold text-on-surface">
                          {EVENT_LABELS[log.event_type] ?? log.event_type}
                        </div>
                        <div className="text-xs text-on-surface-variant">{formatDate(log.created_at)}</div>
                      </div>
                      <span className="rounded bg-surface-container px-sm py-xs text-[11px] font-bold uppercase text-secondary">
                        {log.user_id ? "User" : "Anonymous"}
                      </span>
                    </div>
                    {log.user_id ? (
                      <div className="mt-xs break-all font-mono text-xs text-on-surface-variant">
                        {log.user_id}
                      </div>
                    ) : null}
                    {Object.keys(log.metadata).length > 0 ? (
                      <dl className="mt-sm space-y-xs text-xs">
                        {Object.entries(log.metadata).map(([key, value]) => (
                          <div key={key} className="grid grid-cols-[88px_minmax(0,1fr)] gap-sm">
                            <dt className="text-on-surface-variant">{key}</dt>
                            <dd className="break-words text-on-surface">{metadataValue(value)}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}

```

## File: .superpowers/sdd/xlsx-template-generation-task-7-report.md
```
# XLSX Template Generation Task 7 Report

## Status

Implemented frontend XLSX template management and basic output-format controls.

## Changed Files

- `frontend/src/lib/xlsxTemplates.ts`
- `frontend/src/pages/content/XlsxTemplatesPage.tsx`
- `frontend/src/pages/content/XlsxTemplateUploadPage.tsx`
- `frontend/src/pages/content/XlsxTemplateDetailPage.tsx`
- `frontend/src/pages/content/components/XlsxPreviewGrid.tsx`
- `frontend/src/App.tsx`
- `frontend/src/pages/AuthenticatedShell.tsx`
- `frontend/src/pages/content/ContentLibraryPage.tsx`
- `frontend/src/lib/documentTypes.ts`
- `frontend/src/lib/documentDesigns.ts`
- `frontend/src/lib/documentIssuances.ts`
- `frontend/src/pages/document-types/DocumentTypeCreatePage.tsx`
- `frontend/src/pages/document-designs/DocumentDesignCreatePage.tsx`

## Verification

- `rtk npm --prefix frontend run build`: passed. Vite emitted the pre-existing large chunk warning.
- After review fixes, `rtk npm --prefix frontend run build`: passed. Vite emitted the large chunk warning.

## Notes

- Document issuance list typing now includes format metadata; the table display was left mostly unchanged to avoid risky edits in a large existing file.
- No commit created because the repository index is not writable in this session and the worktree contains unrelated dirty files.

---

## Review Fix Report

Fixed Task 7 review findings:

- `DocumentDesignDetailPage` preserves `output_format` and `xlsx_template_id` when saving mock data.
- `DocumentIssuanceDetailPage` only loads iframe previews for PDF issuances and downloads using `detail.filename` or a format-aware fallback.
- XLSX issuances show a workbook download state instead of a PDF iframe.
- `DocumentDesignCreatePage` now blocks local submit when XLSX is selected without a template.

```
