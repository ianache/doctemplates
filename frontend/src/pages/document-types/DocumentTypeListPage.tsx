import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { type DocumentTypeListItem, listDocumentTypes } from "../../lib/documentTypes";

export default function DocumentTypeListPage() {
  const [items, setItems] = useState<DocumentTypeListItem[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listDocumentTypes()
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
      <div className="flex items-center justify-between gap-md">
        <h1 className="font-headings text-[24px] font-bold leading-[32px] tracking-[-0.01em] text-on-surface">
          Document Types
        </h1>
        <Link
          to="/document-types/new"
          className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
        >
          New Document Type
        </Link>
      </div>

      <div className="mt-xl">
        {error ? (
          <p className="text-sm text-error">
            We couldn't load document types. Please try again.
          </p>
        ) : items === null ? null : items.length === 0 ? (
          <div className="flex flex-col items-center gap-md py-2xl text-center">
            <span className="material-symbols-outlined text-[48px] text-secondary">
              folder_open
            </span>
            <h2 className="font-headings text-[24px] font-bold text-on-surface">
              No document types yet
            </h2>
            <p className="max-w-md text-sm leading-5 text-on-surface-variant">
              Create your first document type to define the tokens templates and designs will be allowed to use.
            </p>
            <Link
              to="/document-types/new"
              className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90"
            >
              New Document Type
            </Link>
          </div>
        ) : (
          <table className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest">
            <thead className="bg-surface-container">
              <tr>
                <th className="px-md py-sm text-left text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                  Name
                </th>
                <th className="px-md py-sm text-left text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                  Description
                </th>
                <th className="px-md py-sm text-left text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                  Fields
                </th>
                <th className="px-md py-sm text-left text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                  Created By
                </th>
                <th className="px-md py-sm text-left text-[11px] font-bold uppercase leading-[16px] tracking-[0.05em] text-secondary">
                  Created At
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-outline-variant">
                  <td className="px-md py-sm text-sm">
                    <Link
                      to={`/document-types/${item.id}`}
                      className="font-bold text-primary hover:underline"
                    >
                      {item.name}
                    </Link>
                  </td>
                  <td className="px-md py-sm text-sm text-on-surface">{item.description}</td>
                  <td className="px-md py-sm text-sm text-on-surface">{item.field_count} fields</td>
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
