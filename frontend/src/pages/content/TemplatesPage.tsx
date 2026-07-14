import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  listHtmlTemplates,
  getHtmlTemplate,
  type HtmlTemplateListItem,
  type HtmlTemplateDetail,
} from "../../lib/content";
import { getDocumentType, listDocumentTypes, type DocumentTypeDetail, type DocumentTypeListItem } from "../../lib/documentTypes";
import PagedTable, { type Column } from "../../components/organisms/PagedTable";
import TokenExplorer from "../document-designs/components/organisms/TokenExplorer";

const PAGE_SIZE_OPTIONS = [5, 10, 20, 50];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<HtmlTemplateListItem[] | null>(null);
  const [docTypes, setDocTypes] = useState<DocumentTypeListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [keyword, setKeyword] = useState("");
  const [selectedDocTypeId, setSelectedDocTypeId] = useState("");
  const [creatorFilter, setCreatorFilter] = useState("");

  // Active filters applied
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [appliedDocTypeId, setAppliedDocTypeId] = useState("");
  const [appliedCreatorFilter, setAppliedCreatorFilter] = useState("");

  // Detail / Inspector States
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<HtmlTemplateDetail | null>(null);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Pagination State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(8);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listHtmlTemplates(), listDocumentTypes()])
      .then(([templateRows, typeRows]) => {
        if (cancelled) return;
        setTemplates(templateRows);
        setDocTypes(typeRows);
        if (templateRows.length > 0) {
          setSelectedTemplateId(templateRows[0].id);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load templates. Please try again.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedTemplateId) {
      setSelectedTemplate(null);
      setSelectedDocumentType(null);
      return;
    }
    let cancelled = false;
    setLoadingDetail(true);
    getHtmlTemplate(selectedTemplateId)
      .then((detail) => {
        if (cancelled) return;
        setSelectedTemplate(detail);
      })
      .catch(() => {
        console.error("Failed to load template detail");
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTemplateId]);

  useEffect(() => {
    if (!selectedTemplate?.document_type_id) {
      setSelectedDocumentType(null);
      return;
    }

    let cancelled = false;
    getDocumentType(selectedTemplate.document_type_id)
      .then((detail) => {
        if (!cancelled) setSelectedDocumentType(detail);
      })
      .catch(() => {
        if (!cancelled) setSelectedDocumentType(null);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTemplate?.document_type_id]);

  const handleApplyFilters = () => {
    setAppliedKeyword(keyword);
    setAppliedDocTypeId(selectedDocTypeId);
    setAppliedCreatorFilter(creatorFilter);
    setPage(1);
  };

  const filteredTemplates = useMemo(() => {
    if (!templates) return [];
    return templates.filter((item) => {
      const matchKeyword = !appliedKeyword.trim() || item.name.toLowerCase().includes(appliedKeyword.toLowerCase());
      const matchDocType = !appliedDocTypeId || item.document_type_id === appliedDocTypeId;
      const matchCreator = !appliedCreatorFilter || (
        appliedCreatorFilter === "me" 
          ? item.created_by_email.includes("admin") // mock creator check or similar
          : item.created_by_email.toLowerCase().includes(appliedCreatorFilter.toLowerCase())
      );
      return matchKeyword && matchDocType && matchCreator;
    });
  }, [templates, appliedKeyword, appliedDocTypeId, appliedCreatorFilter]);

  const uniqueCreators = useMemo(() => {
    if (!templates) return [];
    const creators = new Set<string>();
    templates.forEach(t => {
      if (t.created_by_email) creators.add(t.created_by_email);
    });
    return Array.from(creators);
  }, [templates]);

  const paginatedTemplates = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredTemplates.slice(start, start + pageSize);
  }, [filteredTemplates, page, pageSize]);

  const handleChangePageSize = (nextSize: number) => {
    setPageSize(nextSize);
    setPage(1);
  };

  const columns: Column<HtmlTemplateListItem>[] = [
    {
      key: "id",
      header: "ID",
      className: "w-16 font-mono text-[12px] text-on-surface-variant opacity-60",
      render: (item) => item.id.slice(0, 5).toUpperCase(),
    },
    {
      key: "name",
      header: "TEMPLATE NAME",
      render: (item) => (
        <div className="flex items-center gap-sm">
          <span className="material-symbols-outlined text-primary">description</span>
          <span className="font-bold text-on-surface">{item.name}</span>
        </div>
      ),
    },
    {
      key: "document_type_name",
      header: "DOCUMENT TYPE",
      render: (item) => item.document_type_name,
    },
    {
      key: "token_count",
      header: "TOKENS",
      className: "font-bold",
      render: (item) => item.token_count,
    },
    {
      key: "creator",
      header: "CREATOR",
      render: (item) => item.created_by_email,
    },
    {
      key: "action",
      header: <span className="sr-only">Actions</span>,
      className: "text-right",
      render: (item) => (
        <Link
          to={`/content/templates/${item.id}/edit`}
          className="inline-flex p-1 text-primary hover:bg-surface-container-high rounded"
          title="Open details"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="material-symbols-outlined text-[18px]">visibility</span>
        </Link>
      ),
    },
  ];

  return (
    <section className="-m-lg flex min-h-[calc(100vh-4rem)] overflow-hidden bg-surface-container">
      {/* Left Tool Panel: Filter/Search */}
      <aside className="w-[300px] border-r border-outline-variant bg-surface-container-low flex flex-col p-md shrink-0 overflow-y-auto">
        <div className="mb-lg">
          <h3 className="font-label-caps text-label-caps text-on-surface-variant opacity-60 mb-sm">SEARCH TEMPLATES</h3>
          <div className="space-y-md">
            <div>
              <label className="font-label-caps text-[10px] text-primary mb-xs block">KEYWORDS</label>
              <input
                className="w-full bg-surface border border-outline-variant rounded px-sm py-xs text-body-sm focus:border-primary outline-none transition-colors"
                placeholder="Enter template name..."
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
              />
            </div>
            <div>
              <label className="font-label-caps text-[10px] text-primary mb-xs block">DOCUMENT TYPE</label>
              <select
                className="w-full bg-surface border border-outline-variant rounded px-sm py-xs text-body-sm focus:border-primary outline-none"
                value={selectedDocTypeId}
                onChange={(e) => setSelectedDocTypeId(e.target.value)}
              >
                <option value="">All Document Types</option>
                {docTypes?.map((dt) => (
                  <option key={dt.id} value={dt.id}>{dt.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="font-label-caps text-[10px] text-primary mb-xs block">CREATED BY</label>
              <select
                className="w-full bg-surface border border-outline-variant rounded px-sm py-xs text-body-sm focus:border-primary outline-none"
                value={creatorFilter}
                onChange={(e) => setCreatorFilter(e.target.value)}
              >
                <option value="">Everyone</option>
                {uniqueCreators.map((email) => (
                  <option key={email} value={email}>{email}</option>
                ))}
              </select>
            </div>
            <button
              className="w-full py-sm bg-tertiary text-white font-label-caps text-label-caps tracking-widest hover:bg-black transition-colors rounded active:scale-95"
              onClick={handleApplyFilters}
            >
              APPLY FILTERS
            </button>
          </div>
        </div>
        <div className="mt-auto">
          <div className="bg-surface-container p-md border border-outline-variant border-dashed rounded">
            <p className="font-body-sm text-on-surface-variant text-center italic">
              "Consistency in archival documentation ensures long-term institutional reliability."
            </p>
          </div>
        </div>
      </aside>

      {/* Main Table View */}
      <section className="flex-1 overflow-y-auto bg-white p-lg flex flex-col">
        <div className="flex justify-between items-end mb-lg">
          <div>
            <p className="font-label-caps text-label-caps text-on-surface-variant opacity-60">ADMINISTRATIVE ASSETS</p>
            <h2 className="font-headings text-headline-lg text-primary">Master Template Library</h2>
          </div>
          <div className="flex gap-sm">
            <Link
              to="/content/templates/new"
              className="px-md py-xs bg-primary text-white font-label-caps text-label-caps hover:bg-primary-container transition-colors rounded flex items-center gap-xs"
            >
              + ADD NEW
            </Link>
          </div>
        </div>

        {error ? <p className="text-sm text-error mb-md">{error}</p> : null}

        {templates === null ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-body-md text-secondary">Loading templates...</p>
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-md text-center py-2xl border border-dashed border-outline-variant bg-surface-container-lowest rounded-lg">
            <span className="material-symbols-outlined text-[48px] text-secondary">description</span>
            <h3 className="font-headings text-[18px] font-bold text-on-surface">No templates found</h3>
            <p className="text-body-sm text-on-surface-variant max-w-md">
              There are no templates matching your filter criteria, or the library is empty.
            </p>
          </div>
        ) : (
          <PagedTable
            columns={columns}
            rows={paginatedTemplates}
            rowKey={(item) => item.id}
            page={page}
            pageSize={pageSize}
            total={filteredTemplates.length}
            itemName="templates"
            onChangePage={setPage}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            onChangePageSize={handleChangePageSize}
            onRowClick={(row) => setSelectedTemplateId(row.id)}
            selectedRowId={selectedTemplateId}
          />
        )}

        {/* Bento/Visual Stats Area */}
        <div className="mt-xl grid grid-cols-3 gap-lg">
          <div className="col-span-2 bg-surface-container-low p-md border border-outline-variant flex flex-col justify-center rounded">
            <h4 className="font-headings text-headline-md text-primary mb-xs">Template Usage Statistics</h4>
            <p className="font-body-sm text-on-surface-variant mb-md">Monitor template volume across types.</p>
            <div className="flex gap-lg items-end">
              <div className="flex-1 h-16 bg-white border border-outline-variant relative flex items-end px-sm rounded-sm">
                <div className="w-full bg-primary h-[80%] rounded-t-sm"></div>
              </div>
              <div className="flex-1 h-16 bg-white border border-outline-variant relative flex items-end px-sm rounded-sm">
                <div className="w-full bg-primary h-[45%] rounded-t-sm"></div>
              </div>
              <div className="flex-1 h-16 bg-white border border-outline-variant relative flex items-end px-sm rounded-sm">
                <div className="w-full bg-primary h-[60%] rounded-t-sm"></div>
              </div>
            </div>
          </div>
          <div className="col-span-1 bg-primary text-on-primary p-md flex flex-col justify-between rounded">
            <div>
              <span className="material-symbols-outlined text-[32px]">shield_person</span>
              <h4 className="font-headings text-headline-md mt-sm leading-tight">Admin Access Only</h4>
            </div>
            <p className="font-body-sm opacity-80 mt-xs leading-snug">
              Creating master templates requires clearance. Changes are version-tracked.
            </p>
          </div>
        </div>
      </section>

      {/* Right Inspector: TEMPLATE PREVIEW */}
      <aside className="w-[320px] bg-surface-container-low border-l border-outline-variant p-md flex flex-col shrink-0">
        <h3 className="font-label-caps text-label-caps text-on-surface-variant opacity-60 mb-md">TEMPLATE PREVIEW</h3>
        
        {loadingDetail ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-body-sm text-secondary">Loading preview...</p>
          </div>
        ) : selectedTemplate ? (
          <div className="flex-1 flex flex-col gap-md min-h-0">
            {/* Properties box */}
            <div className="bg-white border border-outline-variant p-md rounded-lg">
              <label className="font-label-caps text-[10px] text-primary mb-xs block">PROPERTIES</label>
              <div className="space-y-xs text-body-sm">
                <div className="flex justify-between border-b border-outline-variant/30 pb-xs">
                  <span className="opacity-60">Creator:</span>
                  <span className="font-mono text-xs max-w-[160px] truncate" title={selectedTemplate.created_by_email}>
                    {selectedTemplate.created_by_email}
                  </span>
                </div>
                <div className="flex justify-between border-b border-outline-variant/30 pb-xs">
                  <span className="opacity-60">Created At:</span>
                  <span>{new Date(selectedTemplate.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="opacity-60">Variables:</span>
                  <span className="font-bold text-primary">{selectedTemplate.token_names.length} detected</span>
                </div>
              </div>
            </div>

            <div className="bg-white border border-outline-variant p-md rounded-lg min-h-0 flex flex-col">
              <label className="font-label-caps text-[10px] text-primary mb-xs block">VARIABLES</label>
              <div className="max-h-64 overflow-y-auto">
                <TokenExplorer
                  fields={selectedDocumentType?.fields ?? []}
                  emptyMessage={
                    selectedTemplate.token_names.length > 0
                      ? "Loading document type tokens..."
                      : "This template has no detected variables."
                  }
                />
              </div>
            </div>

            <div className="mt-auto">
              <Link
                to={`/content/templates/${selectedTemplate.id}/edit`}
                className="w-full text-center block bg-primary text-white font-label-caps text-label-caps py-sm hover:bg-primary-container hover:text-on-primary-container transition-all rounded shadow-sm"
              >
                OPEN DETAILS
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-md border-2 border-dashed border-outline-variant bg-surface-container rounded-lg">
            <span className="material-symbols-outlined text-[48px] text-on-surface-variant">auto_stories</span>
            <p className="font-body-sm text-on-surface mt-sm">Select a template to view details.</p>
          </div>
        )}
      </aside>
    </section>
  );
}
