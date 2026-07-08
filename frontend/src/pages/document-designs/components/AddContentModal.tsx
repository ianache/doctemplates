import { useEffect, useMemo, useState } from "react";

import {
  listHtmlTemplates,
  listStaticPdfAssets,
  type HtmlTemplateListItem,
  type StaticPdfAssetListItem,
} from "../../../lib/content";

interface AddContentModalProps {
  mode: "template" | "pdf";
  documentTypeId: string;
  existingPdfIds: string[];
  onClose: () => void;
  onAddTemplate: (templateId: string) => Promise<void>;
  onAddPdf: (assetId: string) => Promise<void>;
}

export default function AddContentModal({
  mode,
  documentTypeId,
  existingPdfIds,
  onClose,
  onAddTemplate,
  onAddPdf,
}: AddContentModalProps) {
  const [templates, setTemplates] = useState<HtmlTemplateListItem[]>([]);
  const [pdfs, setPdfs] = useState<StaticPdfAssetListItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setSelectedId("");

    const loader = mode === "template" ? listHtmlTemplates(documentTypeId) : listStaticPdfAssets(documentTypeId);

    loader
      .then((rows) => {
        if (cancelled) return;
        if (mode === "template") {
          const templateRows = rows as HtmlTemplateListItem[];
          setTemplates(templateRows);
          setSelectedId(templateRows[0]?.id ?? "");
        } else {
          const pdfRows = rows as StaticPdfAssetListItem[];
          setPdfs(pdfRows);
          setSelectedId(pdfRows.find((pdf) => !existingPdfIds.includes(pdf.id))?.id ?? "");
        }
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load compatible content.");
      });

    return () => {
      cancelled = true;
    };
  }, [documentTypeId, existingPdfIds, mode]);

  const rows = mode === "template" ? templates : pdfs;
  const title = mode === "template" ? "Add Template" : "Add PDF";
  const selectableRows = useMemo(
    () => (mode === "pdf" ? pdfs.filter((pdf) => !existingPdfIds.includes(pdf.id)) : rows),
    [existingPdfIds, mode, pdfs, rows],
  );

  const handleSubmit = async () => {
    if (!selectedId) return;
    setSaving(true);
    setError(null);
    try {
      if (mode === "template") await onAddTemplate(selectedId);
      else await onAddPdf(selectedId);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't add this content.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-md">
      <div className="w-full max-w-xl rounded border border-outline-variant bg-surface-container-lowest p-lg shadow-xl">
        <div className="flex items-center justify-between gap-md">
          <h2 className="font-headings text-[18px] font-bold text-on-surface">{title}</h2>
          <button type="button" className="text-sm font-bold text-primary" onClick={onClose}>
            Close
          </button>
        </div>

        {error ? <p className="mt-md text-sm text-error">{error}</p> : null}

        <div className="mt-md space-y-sm">
          {selectableRows.length === 0 ? (
            <p className="rounded border border-outline-variant bg-background px-md py-sm text-sm text-on-surface-variant">
              No compatible {mode === "template" ? "templates" : "PDFs"} available.
            </p>
          ) : (
            selectableRows.map((row) => (
              <label
                key={row.id}
                className={`block rounded border px-md py-sm text-sm ${
                  selectedId === row.id ? "border-primary" : "border-outline-variant"
                }`}
              >
                <input
                  type="radio"
                  className="mr-sm"
                  checked={selectedId === row.id}
                  onChange={() => setSelectedId(row.id)}
                />
                <span className="font-bold text-on-surface">
                  {"name" in row ? row.name : row.filename}
                </span>
                <span className="ml-sm text-on-surface-variant">
                  {"token_count" in row
                    ? `${row.token_count} token${row.token_count === 1 ? "" : "s"}`
                    : `${row.page_count} page${row.page_count === 1 ? "" : "s"}`}
                </span>
              </label>
            ))
          )}
        </div>

        <div className="mt-lg flex justify-end gap-sm">
          <button
            type="button"
            className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!selectedId || saving}
            className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90 disabled:opacity-50"
            onClick={handleSubmit}
          >
            {title}
          </button>
        </div>
      </div>
    </div>
  );
}
