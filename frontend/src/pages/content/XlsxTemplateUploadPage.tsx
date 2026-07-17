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
    if (!documentTypeId) {
      setError("Choose a document type.");
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
