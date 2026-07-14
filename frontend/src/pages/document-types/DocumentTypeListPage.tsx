import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import PageHeader from "../../components/molecules/PageHeader";
import PagedTable from "../../components/organisms/PagedTable";
import type { Column } from "../../components/organisms/PagedTable";
import { type DocumentTypeListItem, listDocumentTypes } from "../../lib/documentTypes";

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50];

export default function DocumentTypeListPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<DocumentTypeListItem[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

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

  useEffect(() => {
    setPage(1);
  }, [query]);

  const filtered = useMemo(() => {
    if (!items) return null;
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(
      (it) =>
        it.name.toLowerCase().includes(q) ||
        (it.description ?? "").toLowerCase().includes(q) ||
        (it.created_by_email ?? "").toLowerCase().includes(q),
    );
  }, [items, query]);

  const paged = useMemo(
    () => filtered?.slice((page - 1) * pageSize, page * pageSize) ?? null,
    [filtered, page, pageSize],
  );

  const total = filtered?.length ?? 0;

  const handleChangePageSize = (nextSize: number) => {
    setPageSize(nextSize);
    setPage(1);
  };

  const columns: Column<DocumentTypeListItem>[] = [
    {
      key: "name",
      header: "Name",
      render: (item) => (
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">schema</span>
          <Link
            to={`/document-types/${item.id}`}
            className="font-bold text-primary hover:underline"
          >
            {item.name}
          </Link>
        </div>
      ),
    },
    { key: "description", header: "Description", render: (item) => item.description },
    { key: "fields", header: "Fields", render: (item) => `${item.field_count} fields` },
    { key: "created_by", header: "Created By", render: (item) => item.created_by_email },
    {
      key: "created_at",
      header: "Created At",
      render: (item) => new Date(item.created_at).toLocaleDateString(),
    },
    {
      key: "actions",
      header: "Actions",
      render: (item) => (
        <div className="flex items-center gap-sm">
          <Link
            to={`/document-types/${item.id}/edit`}
            className="flex items-center gap-xs rounded border border-outline-variant bg-surface-container px-sm py-xs text-xs font-bold text-secondary hover:bg-surface-container-high hover:text-primary active:scale-95 transition-all"
            onClick={(e) => e.stopPropagation()} // Prevent row click navigation
          >
            <span className="material-symbols-outlined text-[16px]">edit</span>
            Edit
          </Link>
        </div>
      ),
    },
  ];

  return (
    <section>
      <PageHeader
        breadcrumbs={[{ label: "Admin" }, { label: "Document Types" }]}
        title="Document Types"
        actions={
          <Link
            to="/document-types/new"
            className="rounded bg-primary px-lg py-sm font-bold uppercase tracking-wide text-label-caps text-on-primary hover:opacity-90 active:scale-95"
          >
            New Document Type
          </Link>
        }
      />

      <div className="mb-lg flex flex-wrap items-end gap-md rounded-lg border border-outline-variant bg-surface-container-lowest p-md">
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-label-caps text-secondary">Search</label>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-secondary">
              search
            </span>
            <input
              className="w-full rounded border border-outline-variant py-2 pl-9 pr-4 text-body-md focus:border-primary focus:ring-0"
              placeholder="Enter name, description or author..."
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
        <button
          className="rounded border border-outline-variant bg-surface-container px-md py-2 font-bold uppercase tracking-wide text-label-caps text-secondary hover:bg-surface-container-high active:scale-95"
          type="button"
          onClick={() => setQuery("")}
        >
          Reset
        </button>
      </div>

      {error ? (
        <p className="text-sm text-error">We couldn't load document types. Please try again.</p>
      ) : filtered === null ? null : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-md py-2xl text-center">
          <span className="material-symbols-outlined text-[48px] text-secondary">folder_open</span>
          <h2 className="font-headings text-[24px] font-bold text-on-surface">No document types yet</h2>
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
        <PagedTable
          columns={columns}
          rows={paged ?? []}
          rowKey={(item) => item.id}
          page={page}
          pageSize={pageSize}
          total={total}
          itemName="document types"
          onChangePage={setPage}
          pageSizeOptions={PAGE_SIZE_OPTIONS}
          onChangePageSize={handleChangePageSize}
          onRowClick={(item) => navigate(`/document-types/${item.id}/edit`)}
        />
      )}
    </section>
  );
}
