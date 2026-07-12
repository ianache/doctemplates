import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import {
  listHtmlTemplates,
  listStaticPdfAssets,
  type HtmlTemplateListItem,
  type StaticPdfAssetListItem,
} from "../../lib/content";

export default function ContentLibraryPage() {
  const [templates, setTemplates] = useState<HtmlTemplateListItem[] | null>(null);
  const [pdfAssets, setPdfAssets] = useState<StaticPdfAssetListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([listHtmlTemplates(), listStaticPdfAssets()])
      .then(([templateRows, pdfRows]) => {
        if (cancelled) return;
        setTemplates(templateRows);
        setPdfAssets(pdfRows);
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
