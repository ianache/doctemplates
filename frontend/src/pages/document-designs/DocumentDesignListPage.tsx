import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import PageHeader from "../../components/PageHeader";
import {
  listDocumentDesigns,
  type DocumentDesignListItem,
} from "../../lib/documentDesigns";

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  active: "Current",
  superseded: "Superseded",
};

const STATUS_STYLES: Record<string, string> = {
  draft: "text-primary",
  active: "text-green-700",
  superseded: "text-secondary",
};

const STATUS_DOT: Record<string, string> = {
  draft: "bg-primary",
  active: "bg-green-700",
  superseded: "bg-secondary",
};

const STATUS_OPTIONS = ["All", "draft", "active", "superseded"] as const;

export default function DocumentDesignListPage() {
  const [items, setItems] = useState<DocumentDesignListItem[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<(typeof STATUS_OPTIONS)[number]>("All");

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

  const filtered = useMemo(() => {
    if (!items) return null;
    return items.filter((it) => {
      if (status !== "All" && it.status !== status) return false;
      if (!query.trim()) return true;
      const q = query.toLowerCase();
      return (
        it.name.toLowerCase().includes(q) ||
        it.document_type_name.toLowerCase().includes(q) ||
        (it.created_by_email ?? "").toLowerCase().includes(q)
      );
    });
  }, [items, query, status]);

  const statusCounts = useMemo(() => {
    const counts = { all: items?.length ?? 0, draft: 0, active: 0, superseded: 0 };
    for (const item of items ?? []) {
      if (item.status in counts) counts[item.status as keyof typeof counts] += 1;
    }
    return counts;
  }, [items]);

  return (
    <section className="-m-lg flex min-h-[calc(100vh-4rem)] flex-col bg-surface-bright">
      <div className="sticky top-0 z-10 border-b border-outline-variant bg-surface-bright px-lg py-lg">
        <PageHeader
          breadcrumbs={[{ label: "Admin" }, { label: "Document Designs" }]}
          title="Document Designs"
          actions={
            <Link
              to="/document-designs/new"
              className="inline-flex items-center justify-center gap-sm rounded bg-primary px-lg py-sm font-bold uppercase tracking-wide text-label-caps text-on-primary hover:opacity-90 active:scale-95"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New Design
            </Link>
          }
        />

        <div className="grid gap-md md:grid-cols-4">
          <div className="rounded border border-outline-variant bg-surface-container-lowest p-md">
            <p className="font-label-caps text-on-surface-variant">All Designs</p>
            <p className="mt-base font-headings text-headline-md text-on-surface">{statusCounts.all}</p>
          </div>
          {(["active", "draft", "superseded"] as const).map((key) => (
            <button
              key={key}
              type="button"
              className={`rounded border p-md text-left transition-colors ${
                status === key
                  ? "border-primary bg-surface-container-high text-primary"
                  : "border-outline-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low"
              }`}
              onClick={() => setStatus(key)}
            >
              <p className="font-label-caps text-on-surface-variant">{STATUS_LABELS[key]}</p>
              <p className="mt-base font-headings text-headline-md">{statusCounts[key]}</p>
            </button>
          ))}
        </div>

        <div className="mt-lg flex flex-wrap items-end gap-md rounded border border-outline-variant bg-surface-container-lowest p-md">
          <div className="min-w-[240px] flex-1">
            <label className="mb-1 block text-label-caps text-on-surface-variant">Search Designs</label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-on-surface-variant">
                search
              </span>
              <input
                className="w-full rounded border border-outline-variant bg-surface-container-low py-2 pl-9 pr-4 text-body-md focus:border-primary focus:ring-0"
                placeholder="Search by design, type, or owner..."
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="w-48">
            <label className="mb-1 block text-label-caps text-on-surface-variant">Status</label>
            <select
              className="w-full rounded border border-outline-variant bg-surface-container-low py-2 text-body-md focus:border-primary focus:ring-0"
              value={status}
              onChange={(e) => setStatus(e.target.value as (typeof STATUS_OPTIONS)[number])}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt === "All" ? "All Status" : STATUS_LABELS[opt] ?? opt}
                </option>
              ))}
            </select>
          </div>
          <button
            className="rounded border border-outline-variant bg-surface-container px-md py-2 font-bold uppercase tracking-wide text-label-caps text-secondary hover:bg-surface-container-high active:scale-95"
            type="button"
            onClick={() => {
              setQuery("");
              setStatus("All");
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-lg py-lg">
        {error ? (
          <p className="rounded border border-error/30 bg-error-container p-md text-sm text-on-error-container">
            We couldn't load document designs. Please try again.
          </p>
        ) : filtered === null ? null : filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-md rounded border border-outline-variant bg-surface-container-lowest py-2xl text-center">
          <span className="material-symbols-outlined text-[48px] text-secondary">
            dashboard_customize
          </span>
          <h2 className="font-headings text-[24px] font-bold text-on-surface">No document designs yet</h2>
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
          <div className="flex flex-1 flex-col overflow-hidden rounded border border-outline-variant bg-surface-container-lowest">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-low">
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Name</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Document Type</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Status</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Pages</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created By</th>
                  <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {filtered.map((item) => (
                  <tr key={item.id} className="transition-colors hover:bg-surface">
                    <td className="px-md py-md">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary">dashboard_customize</span>
                        <div className="flex flex-col">
                          <Link to={`/document-designs/${item.id}`} className="font-bold text-primary hover:underline">
                            {item.name}
                          </Link>
                          {item.version_number !== null && (
                            <span className="text-[11px] font-normal text-on-surface-variant">
                              Version {item.version_number}
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-md py-md text-on-surface">{item.document_type_name}</td>
                    <td className="px-md py-md">
                      <span
                        className={`flex items-center gap-1.5 text-label-caps font-bold uppercase ${
                          STATUS_STYLES[item.status] ?? "text-secondary"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            STATUS_DOT[item.status] ?? "bg-secondary"
                          }`}
                        />
                        {STATUS_LABELS[item.status] ?? item.status}
                      </span>
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
            <div className="mt-auto flex items-center justify-between border-t border-outline-variant bg-surface-container-low p-md">
              <p className="text-body-sm text-secondary">
                Showing <span className="font-bold text-on-surface">{filtered.length}</span> document designs
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
