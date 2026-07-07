import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { uploadStaticPdfAsset } from "../../lib/content";

export default function StaticPdfUploadPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [pageStart, setPageStart] = useState("");
  const [pageEnd, setPageEnd] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!file) {
      setSubmitError("Choose a PDF file.");
      return;
    }

    try {
      const created = await uploadStaticPdfAsset(
        file,
        pageStart ? Number(pageStart) : null,
        pageEnd ? Number(pageEnd) : null,
      );
      navigate(`/content/static-pdfs/${created.id}`);
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We couldn't upload this PDF.");
    }
  };

  return (
    <section className="rounded border border-outline-variant bg-surface-container-lowest p-lg">
      <div className="flex items-center justify-between gap-md">
        <h2 className="font-headings text-[18px] font-bold text-on-surface">Upload PDF</h2>
        <span className="text-sm text-on-surface-variant">Page range is optional and inclusive.</span>
      </div>

      {submitError ? (
        <p className="mt-md rounded border border-error/30 bg-background p-sm text-sm text-error">
          {submitError}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-md space-y-md">
        <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
          PDF File
          <input
            type="file"
            accept="application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-xs block w-full text-sm text-on-surface"
          />
        </label>

        <div className="grid gap-md sm:grid-cols-2">
          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Page Start
            <input
              type="number"
              min={1}
              value={pageStart}
              onChange={(event) => setPageStart(event.target.value)}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </label>
          <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
            Page End
            <input
              type="number"
              min={1}
              value={pageEnd}
              onChange={(event) => setPageEnd(event.target.value)}
              className="mt-xs w-full rounded border border-outline px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </label>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
          >
            Upload PDF
          </button>
        </div>
      </form>
    </section>
  );
}
