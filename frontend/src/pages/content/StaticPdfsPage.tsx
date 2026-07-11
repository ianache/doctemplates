import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  listStaticPdfAssets,
  getStaticPdfAsset,
  type StaticPdfAssetListItem,
  type StaticPdfAssetDetail,
} from "../../lib/content";
import { listDocumentTypes, type DocumentTypeListItem } from "../../lib/documentTypes";
import PagedTable, { type Column } from "../../components/organisms/PagedTable";

export default function StaticPdfsPage() {
  const [pdfAssets, setPdfAssets] = useState<StaticPdfAssetListItem[] | null>(null);
  const [docTypes, setDocTypes] = useState<DocumentTypeListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Pagination State
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 8;

  // Filter States
  const [filenameKeyword, setFilenameKeyword] = useState("");
  const [uploadDate, setUploadDate] = useState("");
  const [selectedDocTypeId, setSelectedDocTypeId] = useState("");

  // Active filters applied
  const [appliedFilenameKeyword, setAppliedFilenameKeyword] = useState("");
  const [appliedUploadDate, setAppliedUploadDate] = useState("");
  const [appliedDocTypeId, setAppliedDocTypeId] = useState("");

  // Detail / Inspector States
  const [selectedPdfId, setSelectedPdfId] = useState<string | null>(null);
  const [selectedPdf, setSelectedPdf] = useState<StaticPdfAssetDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listStaticPdfAssets(), listDocumentTypes()])
      .then(([pdfRows, typeRows]) => {
        if (cancelled) return;
        setPdfAssets(pdfRows);
        setDocTypes(typeRows);
        if (pdfRows.length > 0) {
          setSelectedPdfId(pdfRows[0].id);
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not load PDF assets. Please try again.");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedPdfId) {
      setSelectedPdf(null);
      return;
    }
    let cancelled = false;
    setLoadingDetail(true);
    getStaticPdfAsset(selectedPdfId)
      .then((detail) => {
        if (cancelled) return;
        setSelectedPdf(detail);
      })
      .catch(() => {
        console.error("Failed to load PDF asset detail");
      })
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedPdfId]);

  const handleApplyFilters = () => {
    setAppliedFilenameKeyword(filenameKeyword);
    setAppliedUploadDate(uploadDate);
    setAppliedDocTypeId(selectedDocTypeId);
    setPage(1);
  };

  const filteredPdfs = useMemo(() => {
    if (!pdfAssets) return [];
    return pdfAssets.filter((item) => {
      const matchFilename = !appliedFilenameKeyword.trim() || item.filename.toLowerCase().includes(appliedFilenameKeyword.toLowerCase());
      const matchDocType = !appliedDocTypeId || item.document_type_id === appliedDocTypeId;
      const matchDate = !appliedUploadDate || new Date(item.created_at).toLocaleDateString() === new Date(appliedUploadDate).toLocaleDateString();
      return matchFilename && matchDocType && matchDate;
    });
  }, [pdfAssets, appliedFilenameKeyword, appliedDocTypeId, appliedUploadDate]);

  const paginatedPdfs = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredPdfs.slice(start, start + PAGE_SIZE);
  }, [filteredPdfs, page, PAGE_SIZE]);

  const columns: Column<StaticPdfAssetListItem>[] = [
    {
      key: "filename",
      header: "Document Name",
      render: (item) => (
        <div className="flex items-center gap-md">
          <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
            picture_as_pdf
          </span>
          <span className="font-body-md text-on-surface font-semibold">{item.filename}</span>
        </div>
      ),
    },
    {
      key: "document_type_name",
      header: "Document Type",
      render: (item) => item.document_type_name || "Unassociated",
    },
    {
      key: "created_at",
      header: "Upload Date",
      className: "font-code-sm text-code-sm text-on-surface-variant",
      render: (item) => new Date(item.created_at).toLocaleDateString(),
    },
    {
      key: "page_count",
      header: "Pages",
      className: "font-code-sm text-code-sm text-on-surface-variant",
      render: (item) => item.page_count,
    },
    {
      key: "created_by",
      header: "Author",
      render: (item) => (
        <span className="bg-secondary-container px-sm py-base rounded-full font-label-caps text-[10px] text-on-secondary-container truncate max-w-[150px] inline-block" title={item.created_by_email}>
          {item.created_by_email}
        </span>
      ),
    },
    {
      key: "action",
      header: <span className="sr-only">Actions</span>,
      className: "text-right",
      render: (item) => (
        <Link
          to={`/content/static-pdfs/${item.id}`}
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
      {/* Main Workspace (Left/Middle Area) */}
      <div className="flex-1 flex flex-col p-lg gap-lg overflow-y-auto">
        
        {/* Search & Filter Panel (Prominent) */}
        <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-lg shadow-sm">
          <div className="flex flex-col gap-md">
            <div className="flex items-center justify-between">
              <h2 className="font-headings text-headline-md flex items-center gap-sm text-primary">
                <span className="material-symbols-outlined">search</span>
                Search Static PDF
              </h2>
              <span className="font-body-sm text-body-sm text-on-surface-variant">
                {pdfAssets ? `${pdfAssets.length} total archived items` : "Loading..."}
              </span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-md items-end">
              <div className="md:col-span-1">
                <label className="block font-label-caps text-label-caps text-on-surface-variant mb-xs">FILENAME</label>
                <input
                  type="text"
                  placeholder="e.g. Manual_Usuario"
                  className="w-full bg-surface border border-outline-variant rounded-lg px-md py-xs focus:border-primary focus:ring-0 text-body-md transition-colors outline-none"
                  value={filenameKeyword}
                  onChange={(e) => setFilenameKeyword(e.target.value)}
                />
              </div>
              <div className="md:col-span-1">
                <label className="block font-label-caps text-label-caps text-on-surface-variant mb-xs">UPLOAD DATE</label>
                <input
                  type="date"
                  className="w-full bg-surface border border-outline-variant rounded-lg px-md py-xs focus:border-primary focus:ring-0 text-body-md transition-colors outline-none"
                  value={uploadDate}
                  onChange={(e) => setUploadDate(e.target.value)}
                />
              </div>
              <div className="md:col-span-1">
                <label className="block font-label-caps text-label-caps text-on-surface-variant mb-xs">DOCUMENT TYPE</label>
                <select
                  className="w-full bg-surface border border-outline-variant rounded-lg px-md py-xs focus:border-primary focus:ring-0 text-body-md transition-colors outline-none"
                  value={selectedDocTypeId}
                  onChange={(e) => setSelectedDocTypeId(e.target.value)}
                >
                  <option value="">All Document Types</option>
                  {docTypes?.map((dt) => (
                    <option key={dt.id} value={dt.id}>{dt.name}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-1">
                <button
                  className="w-full bg-primary text-on-primary py-sm rounded-lg font-label-caps text-label-caps flex items-center justify-center gap-xs hover:bg-opacity-90 active:scale-[0.98] transition-all"
                  onClick={handleApplyFilters}
                >
                  <span className="material-symbols-outlined text-[16px]">filter_list</span>
                  APPLY FILTERS
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Header */}
        <div className="flex justify-between items-end">
          <div>
            <p className="font-label-caps text-label-caps text-on-surface-variant opacity-60">STATIC PDF ASSETS</p>
            <h2 className="font-headings text-headline-lg text-primary">Master PDF Library</h2>
          </div>
          <div className="flex gap-sm">
            <Link
              to="/content/static-pdfs/upload"
              className="px-md py-xs bg-primary text-white font-label-caps text-label-caps hover:bg-primary-container transition-colors rounded flex items-center gap-xs"
            >
              + UPLOAD NEW
            </Link>
          </div>
        </div>

        {error ? <p className="text-sm text-error">{error}</p> : null}

        {pdfAssets === null ? (
          <div className="flex-1 flex items-center justify-center bg-surface-container-lowest border border-outline-variant rounded-xl p-xl">
            <p className="text-body-md text-secondary">Loading PDF assets...</p>
          </div>
        ) : filteredPdfs.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-md text-center py-2xl border border-dashed border-outline-variant bg-surface-container-lowest rounded-lg">
            <span className="material-symbols-outlined text-[48px] text-secondary">picture_as_pdf</span>
            <h3 className="font-headings text-[18px] font-bold text-on-surface">No PDFs found</h3>
            <p className="text-body-sm text-on-surface-variant max-w-md">
              There are no PDF assets matching your filter criteria, or the library is empty.
            </p>
          </div>
        ) : (
          <PagedTable
            columns={columns}
            rows={paginatedPdfs}
            rowKey={(item) => item.id}
            page={page}
            pageSize={PAGE_SIZE}
            total={filteredPdfs.length}
            itemName="PDF assets"
            onChangePage={setPage}
            onRowClick={(row) => setSelectedPdfId(row.id)}
            selectedRowId={selectedPdfId}
          />
        )}
      </div>

      {/* Right Property Inspector (Static Panel) */}
      <aside className="w-panel-width-tools border-l border-outline-variant bg-surface p-md overflow-y-auto flex flex-col gap-lg shrink-0">
        
        {loadingDetail ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-body-sm text-secondary">Loading details...</p>
          </div>
        ) : selectedPdf ? (
          <div className="flex flex-col gap-lg">
            <div className="flex flex-col gap-xs">
              <h3 className="font-label-caps text-label-caps text-primary uppercase tracking-widest border-b border-outline-variant pb-xs">
                Metadata Inspector
              </h3>
              <div className="bg-surface-container-low rounded-lg p-md mt-sm flex flex-col gap-md">
                <div className="flex flex-col gap-xs">
                  <span className="font-label-caps text-[10px] text-on-surface-variant uppercase">Document ID</span>
                  <span className="font-code-sm text-code-sm font-bold block truncate" title={selectedPdf.id}>
                    {selectedPdf.id}
                  </span>
                </div>
                <div className="flex flex-col gap-xs">
                  <span className="font-label-caps text-[10px] text-on-surface-variant uppercase">Storage Path</span>
                  <span className="font-code-sm text-code-sm truncate block" title={selectedPdf.stored_path}>
                    {selectedPdf.stored_path}
                  </span>
                </div>
                <div className="flex flex-col gap-xs">
                  <span className="font-label-caps text-[10px] text-on-surface-variant uppercase">Retention Period</span>
                  <div className="flex items-center gap-xs">
                    <span className="material-symbols-outlined text-primary text-[14px]">lock_clock</span>
                    <span className="font-body-sm text-body-sm">10 Years (Indefinite)</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-xs">
              <h3 className="font-label-caps text-label-caps text-primary uppercase tracking-widest border-b border-outline-variant pb-xs">
                File Preview
              </h3>
              <div className="aspect-[3/4] bg-surface-container-high border-2 border-dashed border-outline rounded-lg flex flex-col items-center justify-center gap-md text-center p-md mt-sm relative group overflow-hidden">
                <span className="material-symbols-outlined text-[48px] text-on-surface-variant">auto_stories</span>
                <div>
                  <p className="font-body-sm text-body-sm text-on-surface px-sm">
                    {selectedPdf.filename}
                  </p>
                  <p className="font-code-sm text-code-sm text-on-surface-variant mt-xs">
                    {(selectedPdf.file_size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="font-body-sm text-body-sm text-primary font-bold mt-sm">
                    {selectedPdf.page_count} pages
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-xs">
              <h3 className="font-label-caps text-label-caps text-primary uppercase tracking-widest border-b border-outline-variant pb-xs">
                Recent Activities
              </h3>
              <ul className="mt-sm space-y-md">
                <li className="flex gap-sm">
                  <div className="w-px bg-outline-variant relative">
                    <div className="absolute top-1 -left-[3px] w-2 h-2 rounded-full bg-primary"></div>
                  </div>
                  <div className="flex flex-col pb-sm">
                    <span className="font-body-sm text-body-sm text-on-surface">Uploaded and indexed</span>
                    <span className="font-label-caps text-[10px] text-on-surface-variant">
                      {new Date(selectedPdf.created_at).toLocaleDateString()} • {selectedPdf.created_by_email.split("@")[0].toUpperCase()}
                    </span>
                  </div>
                </li>
              </ul>
            </div>

            <div>
              <Link
                to={`/content/static-pdfs/${selectedPdf.id}`}
                className="w-full text-center block bg-primary text-white font-label-caps text-label-caps py-sm hover:bg-primary-container hover:text-on-primary-container transition-all rounded shadow-sm"
              >
                OPEN IN FULL SCREEN
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-md border-2 border-dashed border-outline-variant bg-surface-container rounded-lg">
            <span className="material-symbols-outlined text-[48px] text-on-surface-variant">picture_as_pdf</span>
            <p className="font-body-sm text-on-surface mt-sm">Select a PDF to view details.</p>
          </div>
        )}
      </aside>
    </section>
  );
}
