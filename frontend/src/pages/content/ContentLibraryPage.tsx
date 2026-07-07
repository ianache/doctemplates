import { useEffect, useState } from "react";
import { Link, Outlet } from "react-router-dom";

import { listHtmlTemplates, listStaticPdfAssets, type HtmlTemplateListItem, type StaticPdfAssetListItem } from "../../lib/content";

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
      <div className="flex flex-wrap items-end justify-between gap-md">
        <div>
          <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
            Content Library
          </h1>
          <p className="mt-xs text-sm leading-5 text-on-surface-variant">
            Create reusable HTML templates and upload static PDF assets for later document designs.
          </p>
        </div>
        <div className="flex gap-sm">
          <Link
            to="/content/templates/new"
            className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90"
          >
            Create Template
          </Link>
          <Link
            to="/content/static-pdfs/upload"
            className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10"
          >
            Upload PDF
          </Link>
        </div>
      </div>

      {error ? <p className="mt-md text-sm text-error">{error}</p> : null}

      <div className="mt-lg flex gap-sm border-b border-outline-variant pb-xs text-sm font-bold">
        <a className="rounded px-sm py-xs text-primary" href="#templates">
          Templates
        </a>
        <a className="rounded px-sm py-xs text-primary" href="#static-pdfs">
          Static PDFs
        </a>
      </div>

      <div className="mt-lg space-y-xl">
        <section id="templates">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h2 className="font-headings text-[18px] font-bold text-on-surface">Templates</h2>
            <Link to="/content/templates/new" className="text-sm font-bold text-primary hover:underline">
              New Template
            </Link>
          </div>

          {templates === null ? null : templates.length === 0 ? (
            <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No templates yet</p>
            </div>
          ) : (
            <table className="w-full rounded border border-outline-variant bg-surface-container-lowest">
              <thead className="bg-surface-container">
                <tr>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Name
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Document Type
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Tokens
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Created By
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Created At
                  </th>
                </tr>
              </thead>
              <tbody>
                {templates.map((item) => (
                  <tr key={item.id} className="border-t border-outline-variant">
                    <td className="px-md py-sm text-sm font-bold text-primary">
                      <Link to={`/content/templates/${item.id}`} className="hover:underline">
                        {item.name}
                      </Link>
                    </td>
                    <td className="px-md py-sm text-sm text-on-surface">{item.document_type_name}</td>
                    <td className="px-md py-sm text-sm text-on-surface">{item.token_count}</td>
                    <td className="px-md py-sm text-sm text-on-surface">{item.created_by_email}</td>
                    <td className="px-md py-sm text-sm text-on-surface">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section id="static-pdfs">
          <div className="mb-sm flex items-center justify-between gap-md">
            <h2 className="font-headings text-[18px] font-bold text-on-surface">Static PDFs</h2>
            <Link to="/content/static-pdfs/upload" className="text-sm font-bold text-primary hover:underline">
              Upload PDF
            </Link>
          </div>

          {pdfAssets === null ? null : pdfAssets.length === 0 ? (
            <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="text-sm text-on-surface-variant">No PDF assets yet</p>
            </div>
          ) : (
            <table className="w-full rounded border border-outline-variant bg-surface-container-lowest">
              <thead className="bg-surface-container">
                <tr>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Filename
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Pages
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Created By
                  </th>
                  <th className="px-md py-sm text-left text-[11px] font-bold uppercase text-secondary">
                    Created At
                  </th>
                </tr>
              </thead>
              <tbody>
                {pdfAssets.map((item) => (
                  <tr key={item.id} className="border-t border-outline-variant">
                    <td className="px-md py-sm text-sm font-bold text-primary">
                      <Link to={`/content/static-pdfs/${item.id}`} className="hover:underline">
                        {item.filename}
                      </Link>
                    </td>
                    <td className="px-md py-sm text-sm text-on-surface">{item.page_count}</td>
                    <td className="px-md py-sm text-sm text-on-surface">{item.created_by_email}</td>
                    <td className="px-md py-sm text-sm text-on-surface">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <div className="mt-xl">
        <Outlet />
      </div>
    </section>
  );
}
