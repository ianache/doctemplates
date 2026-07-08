import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  listDocumentDesigns,
  type DocumentDesignListItem,
} from "../../lib/documentDesigns";

export default function DocumentDesignListPage() {
  const [items, setItems] = useState<DocumentDesignListItem[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listDocumentDesigns()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-md">
        <div>
          <h1 className="font-headings text-[24px] font-bold leading-[32px] text-on-surface">
            Document Designs
          </h1>
          <p className="mt-xs text-sm leading-5 text-on-surface-variant">
            Compose reusable document types from templates and static PDF pages.
          </p>
        </div>
        <Link
          to="/document-designs/new"
          className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          New Design
        </Link>
      </div>

      <div className="mt-xl">
        {error ? (
          <p className="text-sm text-error">We couldn't load document designs. Please try again.</p>
        ) : items === null ? null : items.length === 0 ? (
          <div className="flex flex-col items-center gap-md py-2xl text-center">
            <span className="material-symbols-outlined text-[48px] text-secondary">
              dashboard_customize
            </span>
            <h2 className="font-headings text-[24px] font-bold text-on-surface">
              No document designs yet
            </h2>
            <p className="max-w-md text-sm leading-5 text-on-surface-variant">
              Create a draft design scoped to a document type, then add templates and PDFs.
            </p>
            <Link
              to="/document-designs/new"
              className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
            >
              New Design
            </Link>
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
                  Status
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
              {items.map((item) => (
                <tr key={item.id} className="border-t border-outline-variant">
                  <td className="px-md py-sm text-sm font-bold text-primary">
                    <div className="flex flex-col">
                      <Link to={`/document-designs/${item.id}`} className="hover:underline">
                        {item.name}
                      </Link>
                      {item.version_number !== null && (
                        <span className="text-[11px] font-normal text-on-surface-variant">
                          Version {item.version_number}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-md py-sm text-sm text-on-surface">
                    {item.document_type_name}
                  </td>
                  <td className="px-md py-sm text-sm">
                    <span className={`inline-block rounded bg-surface-container px-sm py-xs text-[11px] font-bold uppercase ${
                      item.status === "active" || item.status === "draft"
                        ? "text-primary"
                        : "text-on-surface-variant"
                    }`}>
                      {item.status}
                    </span>
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
      </div>
    </section>
  );
}
