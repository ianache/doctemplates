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
