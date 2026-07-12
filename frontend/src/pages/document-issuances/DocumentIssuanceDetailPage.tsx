import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import { API_BASE_URL, apiFetch } from "../../lib/api";
import {
  getDocumentIssuance,
  getDocumentTracelogs,
  shareDocumentIssuance,
  type DocumentIssuanceDetail,
  type DocumentIssuanceStatus,
  type DocumentTracelog,
} from "../../lib/documentIssuances";

const STATUS_LABELS: Record<DocumentIssuanceStatus, string> = {
  success: "Success",
  failure: "Failure",
};

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
    setError(null);
    Promise.all([getDocumentIssuance(id), getDocumentTracelogs(id)])
      .then(([issuance, logs]) => {
        if (cancelled) return;
        setDetail(issuance);
        setTracelogs(logs);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "We couldn't load this document issuance.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!detail) return;
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
      a.download = `${detail.design_name}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      const logs = await getDocumentTracelogs(detail.id);
      setTracelogs(logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't download the PDF.");
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
              disabled={downloading}
            >
              {downloading ? "Downloading..." : "Download PDF"}
            </button>
            <button
              type="button"
              className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10 disabled:opacity-50"
              onClick={handleShare}
              disabled={sharing}
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
          <div className="grid gap-sm border-b border-outline-variant pb-md text-sm md:grid-cols-2">
            <div className="flex justify-between gap-md">
              <span className="text-on-surface-variant">Issuance Status</span>
              <span className="font-bold text-on-surface">{STATUS_LABELS[detail.status]}</span>
            </div>
            <div className="flex justify-between gap-md">
              <span className="text-on-surface-variant">Design Version</span>
              <span className="text-on-surface">
                {detail.design_version_number ?? "None"} · {detail.design_status}
              </span>
            </div>
            <div className="flex justify-between gap-md">
              <span className="text-on-surface-variant">Generated By</span>
              <span className="text-on-surface">{detail.generated_by_email}</span>
            </div>
            <div className="flex justify-between gap-md">
              <span className="text-on-surface-variant">Created At</span>
              <span className="text-on-surface">{formatDate(detail.created_at)}</span>
            </div>
            <div className="md:col-span-2">
              <div className="mb-1 text-on-surface-variant">Issuance ID</div>
              <div className="break-all font-mono text-body-sm text-on-surface">{detail.id}</div>
            </div>
          </div>

          <div>
            <h2 className="mb-sm font-headings text-[18px] font-bold text-on-surface">PDF Preview</h2>
            {previewError ? (
              <p className="rounded border border-error/30 p-md text-sm text-error">{previewError}</p>
            ) : blobUrl ? (
              <iframe
                title={`PDF preview for ${detail.design_name}`}
                src={blobUrl}
                className="h-[720px] w-full rounded border border-outline-variant bg-surface-container-lowest"
              />
            ) : (
              <div className="flex h-[720px] w-full items-center justify-center rounded border border-outline-variant bg-surface-container-lowest">
                <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-lg">
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
