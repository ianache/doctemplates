import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getDocumentType,
  listDocumentTypes,
  type DocumentTypeDetail,
  type DocumentTypeListItem,
} from "../../lib/documentTypes";
import { createHtmlTemplate } from "../../lib/content";

export default function HtmlTemplateCreatePage() {
  const navigate = useNavigate();
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [html, setHtml] = useState("");
  const [htmlTouched, setHtmlTouched] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listDocumentTypes()
      .then((rows) => {
        if (cancelled) return;
        setDocumentTypes(rows);
        setDocumentTypeId(rows[0]?.id ?? "");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!documentTypeId) {
      setSelectedDocumentType(null);
      return;
    }

    let cancelled = false;
    getDocumentType(documentTypeId).then((detail) => {
      if (cancelled) return;
      setSelectedDocumentType(detail);
      if (!htmlTouched && detail?.fields?.length) {
        setHtml(`<p>{{${detail.fields[0].name}}}</p>`);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [documentTypeId, htmlTouched]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!documentTypeId) {
      setSubmitError("Choose a document type.");
      return;
    }

    try {
      const created = await createHtmlTemplate({
        document_type_id: documentTypeId,
        name,
        html,
      });
      navigate(`/content/templates/${created.id}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We couldn't save this template.");
    }
  };

  return (
    <section className="rounded border border-outline-variant bg-surface-container-lowest p-lg">
      <div className="flex items-center justify-between gap-md">
        <h2 className="font-headings text-[18px] font-bold text-on-surface">Create Template</h2>
        <span className="text-sm text-on-surface-variant">Tokens are validated against the selected document type.</span>
      </div>

      {submitError ? (
        <p className="mt-md rounded border border-error/30 bg-background p-sm text-sm text-error">
          {submitError}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-md space-y-md">
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
          />
        </label>

        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          Document Type
          <select
            value={documentTypeId}
            onChange={(event) => {
              setDocumentTypeId(event.target.value);
              setHtmlTouched(false);
            }}
            className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
          >
            {loading ? <option>Loading...</option> : null}
            {!loading && documentTypes.length === 0 ? <option value="">No document types available</option> : null}
            {documentTypes.map((documentType) => (
              <option key={documentType.id} value={documentType.id}>
                {documentType.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          HTML
          <textarea
            value={html}
            onChange={(event) => {
              setHtml(event.target.value);
              setHtmlTouched(true);
            }}
            rows={12}
            className="mt-xs w-full rounded border border-outline px-sm py-xs font-mono text-sm text-on-surface focus:border-primary focus:outline-none"
          />
        </label>

        <div className="rounded border border-outline-variant bg-surface-container-lowest px-md py-sm text-sm text-on-surface-variant">
          <p className="text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Allowed Tokens
          </p>
          {selectedDocumentType?.fields?.length ? (
            <div className="mt-xs flex flex-wrap gap-xs">
              {selectedDocumentType.fields.map((field) => (
                <code
                  key={field.id}
                  className="rounded bg-surface-container px-2 py-0.5 text-[12px] text-on-surface"
                >
                  {`{{${field.name}}}`}
                </code>
              ))}
            </div>
          ) : (
            <p className="mt-xs">
              Select a document type to see the tokens available for that template.
            </p>
          )}
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
          >
            Create Template
          </button>
        </div>
      </form>
    </section>
  );
}
