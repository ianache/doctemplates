import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getDocumentDesign, type DocumentDesignDetail } from "../../lib/documentDesigns";

function pageLabel(page: DocumentDesignDetail["pages"][number]) {
  if (page.title) return page.title;
  if (page.block_type === "html_template") return String(page.snapshot.name ?? "HTML template");
  return String(page.snapshot.filename ?? "Static PDF");
}

export default function DocumentDesignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [design, setDesign] = useState<DocumentDesignDetail | null | undefined>(undefined);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getDocumentDesign(id)
      .then((data) => {
        if (!cancelled) setDesign(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return <p className="text-sm text-error">We couldn't load this design.</p>;
  }

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
    <section>
      <div className="flex flex-wrap items-start justify-between gap-md">
        <div>
          <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
            {design.name}
          </h1>
          <p className="mt-xs text-sm leading-5 text-on-surface-variant">
            {design.description || "No description"}
          </p>
        </div>
        <span className="rounded bg-surface-container px-sm py-xs text-sm font-bold text-primary">
          {design.status}
        </span>
      </div>

      <div className="mt-md grid gap-sm border-b border-outline-variant pb-md text-sm md:grid-cols-2">
        <div className="flex justify-between gap-md">
          <span className="text-on-surface-variant">Document Type</span>
          <span className="font-bold text-on-surface">{design.document_type_name}</span>
        </div>
        <div className="flex justify-between gap-md">
          <span className="text-on-surface-variant">Created By</span>
          <span className="text-on-surface">{design.created_by_email}</span>
        </div>
        <div className="flex justify-between gap-md">
          <span className="text-on-surface-variant">Created At</span>
          <span className="text-on-surface">{new Date(design.created_at).toLocaleDateString()}</span>
        </div>
        <div className="flex justify-between gap-md">
          <span className="text-on-surface-variant">Pages</span>
          <span className="text-on-surface">{design.pages.length}</span>
        </div>
      </div>

      <div className="mt-lg flex flex-wrap justify-end gap-sm">
        <button
          type="button"
          className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90"
        >
          Add Template
        </button>
        <button
          type="button"
          className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10"
        >
          Add PDF
        </button>
      </div>

      <div className="mt-lg grid gap-lg lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-sm">
          {design.pages.length === 0 ? (
            <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="font-headings text-[18px] font-bold text-on-surface">
                Empty page stack
              </p>
              <p className="mt-xs text-sm text-on-surface-variant">
                Add a template or static PDF page to start composing this design.
              </p>
            </div>
          ) : (
            design.pages.map((page) => (
              <div
                key={page.id}
                className="rounded border border-outline-variant bg-surface-container-lowest px-md py-sm"
              >
                <div className="flex items-start justify-between gap-md">
                  <div>
                    <p className="text-[11px] font-bold uppercase text-secondary">
                      Page {page.position + 1} · {page.block_type === "html_template" ? "Template" : "PDF"}
                    </p>
                    <h2 className="mt-xs font-headings text-[18px] font-bold text-on-surface">
                      {pageLabel(page)}
                    </h2>
                  </div>
                  <span className="material-symbols-outlined text-[20px] text-secondary">
                    drag_indicator
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        <aside className="rounded border border-outline-variant bg-surface-container-lowest p-md">
          <h2 className="font-headings text-[18px] font-bold text-on-surface">Inspector</h2>
          <p className="mt-xs text-sm leading-5 text-on-surface-variant">
            Select a page in the stack to review its title, notes, and page configuration.
          </p>
        </aside>
      </div>
    </section>
  );
}
