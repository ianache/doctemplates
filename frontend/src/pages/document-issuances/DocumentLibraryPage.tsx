import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import DateRange from "../../components/molecules/DateRange";
import {
  listDocumentIssuances,
  type DocumentIssuanceFilters,
  type DocumentIssuanceListItem,
  type DocumentIssuanceStatus,
} from "../../lib/documentIssuances";

const STATUS_LABELS: Record<DocumentIssuanceStatus, string> = {
  success: "Success",
  failure: "Failure",
};

const STATUS_STYLES: Record<DocumentIssuanceStatus, string> = {
  success: "text-green-700",
  failure: "text-error",
};

const STATUS_DOT: Record<DocumentIssuanceStatus, string> = {
  success: "bg-green-700",
  failure: "bg-error",
};

const EMPTY_FILTERS: DocumentIssuanceFilters = {
  design_name: "",
  id: "",
  status: "",
  created_from: "",
  created_to: "",
  metadata_key: "",
  metadata_value: "",
};

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function DocumentLibraryPage() {
  const [filters, setFilters] = useState<DocumentIssuanceFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<DocumentIssuanceFilters>(EMPTY_FILTERS);
  const [items, setItems] = useState<DocumentIssuanceListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    listDocumentIssuances(appliedFilters)
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setItems([]);
          setError(err instanceof Error ? err.message : "We couldn't load document issuances.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [appliedFilters]);

  const updateFilter = (key: keyof DocumentIssuanceFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const submitFilters = (event: FormEvent) => {
    event.preventDefault();
    setAppliedFilters(filters);
  };

  const resetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Operations" }, { label: "Documents Library" }]}
        title="Documents Library"
      />

      <form
        className="mb-lg flex flex-wrap items-end gap-md rounded-lg border border-outline-variant bg-surface-container-lowest p-md"
        onSubmit={submitFilters}
      >
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-label-caps text-secondary">Search Documents</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-secondary">
              search
            </span>
            <input
              className="w-full rounded border border-outline-variant py-2 pl-9 pr-4 text-body-md focus:border-primary focus:ring-0"
              value={filters.design_name ?? ""}
              onChange={(event) => updateFilter("design_name", event.target.value)}
              placeholder="Enter document name or ID..."
              type="text"
            />
          </div>
        </div>
        <div className="w-48">
          <label className="mb-1 block text-label-caps text-secondary">Issuance ID</label>
          <input
            className="w-full rounded border border-outline-variant py-2 pl-3 pr-3 font-mono text-body-sm focus:border-primary focus:ring-0"
            value={filters.id ?? ""}
            onChange={(event) => updateFilter("id", event.target.value)}
            placeholder="UUID"
            type="text"
          />
        </div>
        <div className="w-48">
          <label className="mb-1 block text-label-caps text-secondary">Status</label>
          <select
            className="w-full rounded border border-outline-variant py-2 text-body-md focus:border-primary focus:ring-0"
            value={filters.status ?? ""}
            onChange={(event) => updateFilter("status", event.target.value)}
          >
            <option value="">All Status</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
        </div>
        <div className="w-48">
          <label className="mb-1 block text-label-caps text-secondary">Metadata Key</label>
          <input
            className="w-full rounded border border-outline-variant py-2 pl-3 pr-3 text-body-md focus:border-primary focus:ring-0"
            value={filters.metadata_key ?? ""}
            onChange={(event) => updateFilter("metadata_key", event.target.value)}
            placeholder="e.g. department"
            type="text"
          />
        </div>
        <div className="w-48">
          <label className="mb-1 block text-label-caps text-secondary">Metadata Value</label>
          <input
            className="w-full rounded border border-outline-variant py-2 pl-3 pr-3 text-body-md focus:border-primary focus:ring-0"
            value={filters.metadata_value ?? ""}
            onChange={(event) => updateFilter("metadata_value", event.target.value)}
            placeholder="e.g. sales"
            type="text"
          />
        </div>
        <div className="min-w-[260px] flex-1">
          <DateRange
            from={filters.created_from ?? ""}
            to={filters.created_to ?? ""}
            onFromChange={(v) => updateFilter("created_from", v)}
            onToChange={(v) => updateFilter("created_to", v)}
            fromLabel="Date From"
            toLabel="Date To"
          />
        </div>
        <div className="flex gap-sm">
          <button
            className="h-[42px] rounded bg-primary px-lg py-2 font-bold uppercase tracking-wide text-label-caps text-on-primary hover:opacity-90 active:scale-95"
            type="submit"
          >
            Apply
          </button>
          <button
            className="h-[42px] rounded border border-outline-variant bg-surface-container px-md py-2 font-bold uppercase tracking-wide text-label-caps text-secondary hover:bg-surface-container-high active:scale-95"
            type="button"
            onClick={resetFilters}
          >
            Reset
          </button>
        </div>
      </form>

      {error ? <p className="mb-md text-sm text-error">{error}</p> : null}

      {items === null ? null : items.length === 0 ? (
        <div className="flex flex-col items-center gap-md py-2xl text-center">
          <span className="material-symbols-outlined text-[48px] text-secondary">folder_open</span>
          <h2 className="font-headings text-[24px] font-bold text-on-surface">No generated documents found</h2>
          <p className="max-w-md text-sm leading-5 text-on-surface-variant">
            Adjust filters or generate a document from an active design.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-outline-variant bg-surface-container-low">
                <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Design</th>
                <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Issuance ID</th>
                <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Status</th>
                <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Generated By</th>
                <th className="px-md py-sm font-bold uppercase text-label-caps text-secondary">Created At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {items.map((item) => (
                <tr key={item.id} className="transition-colors hover:bg-surface">
                  <td className="px-md py-md">
                    <Link to={`/document-issuances/${item.id}`} className="font-bold text-primary hover:underline">
                      {item.design_name}
                    </Link>
                    {item.design_version_number !== null ? (
                      <div className="text-[11px] text-on-surface-variant">
                        Version {item.design_version_number} · {item.design_status}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-md py-md font-mono text-body-sm text-on-surface">{item.id}</td>
                  <td className="px-md py-md">
                    <span className={`flex items-center gap-1.5 text-label-caps font-bold uppercase ${STATUS_STYLES[item.status]}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[item.status]}`} />
                      {STATUS_LABELS[item.status]}
                    </span>
                  </td>
                  <td className="px-md py-md text-on-surface">{item.generated_by_email}</td>
                  <td className="px-md py-md text-on-surface">{formatDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-auto flex items-center justify-between border-t border-outline-variant bg-surface-container-low p-md">
            <p className="text-body-sm text-secondary">
              Showing <span className="font-bold text-on-surface">{items.length}</span> generated documents
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
