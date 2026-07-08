import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  activateDocumentDesign,
  addStaticPdfDesignPage,
  addTemplateDesignPage,
  deleteDesignPage,
  getDocumentDesign,
  reorderDesignPages,
  updateDesignPage,
  type DocumentDesignDetail,
  type DocumentDesignPage,
} from "../../lib/documentDesigns";
import AddContentModal from "./components/AddContentModal";
import DesignPageCard from "./components/DesignPageCard";
import DesignPageInspector from "./components/DesignPageInspector";

function sortPages(pages: DocumentDesignPage[]) {
  return [...pages].sort((a, b) => a.position - b.position);
}

export default function DocumentDesignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [design, setDesign] = useState<DocumentDesignDetail | null | undefined>(undefined);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [modalMode, setModalMode] = useState<"template" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<DocumentDesignPage | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    getDocumentDesign(id)
      .then((data) => {
        if (cancelled) return;
        setDesign(data);
        setSelectedPageId(data?.pages[0]?.id ?? null);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load this design.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const pages = useMemo(() => sortPages(design?.pages ?? []), [design?.pages]);
  const selectedPage = pages.find((page) => page.id === selectedPageId) ?? null;
  const existingPdfIds = pages
    .filter((page) => page.block_type === "static_pdf")
    .map((page) => page.content_id);

  const setPages = (nextPages: DocumentDesignPage[]) => {
    setDesign((current) =>
      current ? { ...current, pages: nextPages.map((page, index) => ({ ...page, position: index })) } : current,
    );
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    if (!design || event.over === null || event.active.id === event.over.id) return;

    const oldIndex = pages.findIndex((page) => page.id === event.active.id);
    const newIndex = pages.findIndex((page) => page.id === event.over?.id);
    if (oldIndex < 0 || newIndex < 0) return;

    const previousPages = pages;
    const nextPages = arrayMove(pages, oldIndex, newIndex).map((page, index) => ({
      ...page,
      position: index,
    }));
    setPages(nextPages);
    setError(null);
    try {
      const updated = await reorderDesignPages(design.id, nextPages.map((page) => page.id));
      setDesign(updated);
    } catch (err) {
      setPages(previousPages);
      setError(err instanceof Error ? err.message : "We couldn't save the page order.");
    }
  };

  const handleAddTemplate = async (templateId: string) => {
    if (!design) return;
    const page = await addTemplateDesignPage(design.id, { template_id: templateId });
    setDesign({ ...design, pages: [...pages, page] });
    setSelectedPageId(page.id);
    setNotice("Template page added.");
  };

  const handleAddPdf = async (assetId: string) => {
    if (!design) return;
    const page = await addStaticPdfDesignPage(design.id, { static_pdf_asset_id: assetId });
    setDesign({ ...design, pages: [...pages, page] });
    setSelectedPageId(page.id);
    setNotice("PDF page added.");
  };

  const handleSavePage = async (
    pageId: string,
    values: { title: string | null; notes: string | null; config: Record<string, unknown> },
  ) => {
    if (!design) return;
    const updatedPage = await updateDesignPage(design.id, pageId, values);
    setDesign({
      ...design,
      pages: pages.map((page) => (page.id === pageId ? updatedPage : page)),
    });
    setNotice("Page saved.");
  };

  const handleRemove = (page: DocumentDesignPage) => {
    setPendingRemove(page);
    setPages(pages.filter((candidate) => candidate.id !== page.id));
    if (selectedPageId === page.id) setSelectedPageId(null);
    setNotice("Page removed locally. Undo or confirm removal.");
  };

  const undoRemove = () => {
    if (!pendingRemove) return;
    setPages([...pages, pendingRemove].sort((a, b) => a.position - b.position));
    setSelectedPageId(pendingRemove.id);
    setPendingRemove(null);
    setNotice("Page restored.");
  };

  const confirmRemove = async () => {
    if (!design || !pendingRemove) return;
    try {
      await deleteDesignPage(design.id, pendingRemove.id);
      setPendingRemove(null);
      setNotice("Page removal saved.");
    } catch (err) {
      setPages([...pages, pendingRemove].sort((a, b) => a.position - b.position));
      setError(err instanceof Error ? err.message : "We couldn't remove this page.");
      setPendingRemove(null);
    }
  };

  const handleActivate = async () => {
    if (!design) return;
    setError(null);
    try {
      const updated = await activateDocumentDesign(design.id);
      setDesign(updated);
      setNotice("Design activated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't activate this design.");
    }
  };

  if (error && design === undefined) return <p className="text-sm text-error">{error}</p>;
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
        <div className="flex items-center gap-sm">
          <span className="rounded bg-surface-container px-sm py-xs text-sm font-bold text-primary">
            {design.status}
          </span>
          <button
            type="button"
            className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10"
            onClick={handleActivate}
          >
            Activate
          </button>
        </div>
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
          <span className="text-on-surface">{pages.length}</span>
        </div>
      </div>

      {error ? <p className="mt-md rounded border border-error/30 p-sm text-sm text-error">{error}</p> : null}
      {notice ? (
        <div className="mt-md flex flex-wrap items-center justify-between gap-sm rounded border border-outline-variant bg-surface-container-lowest p-sm text-sm text-on-surface">
          <span>{notice}</span>
          {pendingRemove ? (
            <span className="flex gap-sm">
              <button type="button" className="font-bold text-primary" onClick={undoRemove}>
                Undo
              </button>
              <button type="button" className="font-bold text-error" onClick={confirmRemove}>
                Confirm
              </button>
            </span>
          ) : null}
        </div>
      ) : null}

      <div className="mt-lg flex flex-wrap justify-end gap-sm">
        <button
          type="button"
          className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90"
          onClick={() => setModalMode("template")}
        >
          Add Template
        </button>
        <button
          type="button"
          className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10"
          onClick={() => setModalMode("pdf")}
        >
          Add PDF
        </button>
      </div>

      <div className="mt-lg grid gap-lg lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-sm">
          {pages.length === 0 ? (
            <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
              <p className="font-headings text-[18px] font-bold text-on-surface">
                Empty page stack
              </p>
              <p className="mt-xs text-sm text-on-surface-variant">
                Add a template or static PDF page to start composing this design.
              </p>
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={pages.map((page) => page.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-sm">
                  {pages.map((page) => (
                    <DesignPageCard
                      key={page.id}
                      page={page}
                      selected={page.id === selectedPageId}
                      onSelect={setSelectedPageId}
                      onRemove={handleRemove}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </div>

        <DesignPageInspector page={selectedPage} onSave={handleSavePage} />
      </div>

      {modalMode ? (
        <AddContentModal
          mode={modalMode}
          documentTypeId={design.document_type_id}
          existingPdfIds={existingPdfIds}
          onClose={() => setModalMode(null)}
          onAddTemplate={handleAddTemplate}
          onAddPdf={handleAddPdf}
        />
      ) : null}
    </section>
  );
}
