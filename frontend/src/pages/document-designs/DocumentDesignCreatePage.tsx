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
  const [loadingFormatOptions, setLoadingFormatOptions] = useState(false);
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
    setLoadingFormatOptions(true);
    setSelectedDocumentType(null);
    setXlsxTemplates([]);
    setXlsxTemplateId("");
    Promise.all([getDocumentType(documentTypeId), listXlsxTemplates(documentTypeId)])
      .then(([documentType, templates]) => {
        if (cancelled) return;
        setSelectedDocumentType(documentType);
        setXlsxTemplates(templates);
        const allowed = documentType?.allowed_output_formats ?? ["pdf"];
        const nextFormat = allowed.includes(outputFormat) ? outputFormat : allowed[0] ?? "pdf";
        setOutputFormat(nextFormat);
        setXlsxTemplateId(nextFormat === "xlsx" ? templates[0]?.id ?? "" : "");
      })
      .catch(() => {
        if (!cancelled) setSubmitError("We couldn't load format options.");
      })
      .finally(() => {
        if (!cancelled) setLoadingFormatOptions(false);
      });
    return () => {
      cancelled = true;
    };
  }, [documentTypeId]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!documentTypeId) {
      setSubmitError("Choose a document type.");
      return;
    }
    if (loadingFormatOptions || !selectedDocumentType) {
      setSubmitError("Wait until format options finish loading.");
      return;
    }
    if (!selectedDocumentType.allowed_output_formats.includes(outputFormat)) {
      setSubmitError("Choose an output format allowed by this document type.");
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
              onChange={(event) => {
                setDocumentTypeId(event.target.value);
                setSubmitError(null);
              }}
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
              onChange={(event) => {
                const nextFormat = event.target.value as OutputFormat;
                setOutputFormat(nextFormat);
                setXlsxTemplateId(nextFormat === "xlsx" ? xlsxTemplates[0]?.id ?? "" : "");
              }}
              disabled={loadingFormatOptions || !selectedDocumentType}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {(selectedDocumentType?.allowed_output_formats ?? []).map((format) => (
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
                disabled={loadingFormatOptions || xlsxTemplates.length === 0}
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
            disabled={loading || loadingFormatOptions}
            className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
          >
            Create Design
          </button>
        </div>
      </form>
    </section>
  );
}
