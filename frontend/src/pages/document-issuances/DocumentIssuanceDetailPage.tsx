import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import IssuanceProperties from "../../components/molecules/IssuanceProperties";
import PagedTable from "../../components/organisms/PagedTable";
import type { Column } from "../../components/organisms/PagedTable";
import { API_BASE_URL, apiFetch } from "../../lib/api";
import {
  getDocumentIssuance,
  getDocumentTracelogs,
  shareDocumentIssuance,
  type DocumentIssuanceDetail,
  type DocumentTracelog,
} from "../../lib/documentIssuances";
import {
  DEFAULT_DATA_EXPORT_SELECTION,
  downloadIssuanceDataExport,
  selectedDataExportSections,
  type DataExportSection,
  type DataExportSelection,
} from "../../lib/issuanceDataExport";

const EVENT_LABELS: Record<string, string> = {
  generation: "Generated",
  download: "Downloaded",
  share: "Shared",
};

const DATA_EXPORT_LABELS: Record<DataExportSection, string> = {
  input_data: "Input data",
  metadata_values: "Metadata values",
  tracelogs: "Audit tracelogs",
};

const AUDIT_PAGE_SIZE_OPTIONS = [5, 10, 20, 50];

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
  const [showDataExportModal, setShowDataExportModal] = useState(false);
  const [dataExportSelection, setDataExportSelection] = useState<DataExportSelection>(DEFAULT_DATA_EXPORT_SELECTION);
  const [dataExportError, setDataExportError] = useState<string | null>(null);
  const [exportingData, setExportingData] = useState(false);
  const [auditPage, setAuditPage] = useState(1);
  const [auditPageSize, setAuditPageSize] = useState(5);

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

  useEffect(() => {
    setAuditPage(1);
  }, [tracelogs.length, auditPageSize]);

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

  const openDataExportModal = () => {
    setDataExportSelection(DEFAULT_DATA_EXPORT_SELECTION);
    setDataExportError(null);
    setShowDataExportModal(true);
  };

  const toggleDataExportSection = (section: DataExportSection) => {
    setDataExportSelection((current) => ({ ...current, [section]: !current[section] }));
    setDataExportError(null);
  };

  const handleDownloadData = async () => {
    if (!detail) return;
    setExportingData(true);
    setDataExportError(null);
    try {
      await downloadIssuanceDataExport(detail, tracelogs, dataExportSelection);
      setShowDataExportModal(false);
    } catch (err) {
      setDataExportError(err instanceof Error ? err.message : "We couldn't export this data.");
    } finally {
      setExportingData(false);
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

  const auditRows = tracelogs.slice((auditPage - 1) * auditPageSize, auditPage * auditPageSize);

  const handleAuditPageSizeChange = (nextSize: number) => {
    setAuditPageSize(nextSize);
    setAuditPage(1);
  };

  const auditColumns: Column<DocumentTracelog>[] = [
    {
      key: "event",
      header: "Event",
      render: (log) => <span className="font-bold">{EVENT_LABELS[log.event_type] ?? log.event_type}</span>,
    },
    {
      key: "date",
      header: "Date",
      render: (log) => formatDate(log.created_at),
    },
    {
      key: "actor",
      header: "Actor",
      render: (log) => (log.user_id ? "User" : "Anonymous"),
    },
    {
      key: "user_id",
      header: "User ID",
      render: (log) =>
        log.user_id ? (
          <span className="block max-w-[220px] truncate font-mono text-xs" title={log.user_id}>
            {log.user_id}
          </span>
        ) : (
          "None"
        ),
    },
    {
      key: "metadata",
      header: "Metadata",
      render: (log) => {
        const entries = Object.entries(log.metadata);
        if (entries.length === 0) return "None";
        return <span className="text-xs">{entries.map(([key, value]) => `${key}: ${metadataValue(value)}`).join("; ")}</span>;
      },
    },
  ];

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
              onClick={openDataExportModal}
              disabled={detail.status !== "success"}
            >
              Download Data
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
        </aside>
      </div>

      <section className="mt-lg">
        <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">Audit Timeline</h2>
        <PagedTable
          columns={auditColumns}
          rows={auditRows}
          rowKey={(log) => log.id}
          page={auditPage}
          pageSize={auditPageSize}
          total={tracelogs.length}
          itemName="audit events"
          onChangePage={setAuditPage}
          pageSizeOptions={AUDIT_PAGE_SIZE_OPTIONS}
          onChangePageSize={handleAuditPageSizeChange}
          emptyState={<p className="p-md text-sm text-on-surface-variant">No tracelog events recorded.</p>}
        />
      </section>

      {showDataExportModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-md">
          <div className="w-full max-w-lg rounded border border-outline-variant bg-surface-container-lowest p-lg shadow-xl">
            <div className="flex items-center justify-between gap-md">
              <h2 className="font-headings text-[18px] font-bold text-on-surface">Download data</h2>
              <button
                type="button"
                className="text-sm font-bold text-primary disabled:opacity-50"
                onClick={() => setShowDataExportModal(false)}
                disabled={exportingData}
              >
                Close
              </button>
            </div>

            <div className="mt-md space-y-sm">
              {(Object.keys(DATA_EXPORT_LABELS) as DataExportSection[]).map((section) => (
                <label key={section} className="flex items-center gap-sm text-sm text-on-surface">
                  <input
                    type="checkbox"
                    checked={dataExportSelection[section]}
                    onChange={() => toggleDataExportSection(section)}
                  />
                  <span>{DATA_EXPORT_LABELS[section]}</span>
                </label>
              ))}
            </div>

            {dataExportError ? <p className="mt-md text-sm text-error">{dataExportError}</p> : null}

            <div className="mt-lg flex justify-end gap-sm">
              <button
                type="button"
                className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface disabled:opacity-50"
                onClick={() => setShowDataExportModal(false)}
                disabled={exportingData}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50"
                onClick={handleDownloadData}
                disabled={exportingData || selectedDataExportSections(dataExportSelection).length === 0}
              >
                {exportingData ? "Preparing..." : "Download"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
