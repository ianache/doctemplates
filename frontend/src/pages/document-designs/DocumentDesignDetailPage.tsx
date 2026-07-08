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
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import {
  activateDocumentDesign,
  addStaticPdfDesignPage,
  addTemplateDesignPage,
  deleteDesignPage,
  getDocumentDesign,
  reorderDesignPages,
  updateDesignPage,
  forkDocumentDesignVersion,
  discardDocumentDesignDraft,
  listDocumentDesignVersions,
  type DocumentDesignDetail,
  type DocumentDesignPage,
  type DocumentDesignListItem,
} from "../../lib/documentDesigns";
import AddContentModal from "./components/AddContentModal";
import DesignPageCard from "./components/DesignPageCard";
import DesignPageInspector from "./components/DesignPageInspector";

function sortPages(pages: DocumentDesignPage[]) {
  return [...pages].sort((a, b) => a.position - b.position);
}

export default function DocumentDesignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [design, setDesign] = useState<DocumentDesignDetail | null | undefined>(undefined);
  const [selectedPageId, setSelectedPageId] = useState<string | null>(null);
  const [modalMode, setModalMode] = useState<"template" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<DocumentDesignPage | null>(null);
  const [versions, setVersions] = useState<DocumentDesignListItem[]>([]);
  const [showDiscardModal, setShowDiscardModal] = useState(false);
  const [discarding, setDiscarding] = useState(false);

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

  useEffect(() => {
    if (!design?.id) return;
    listDocumentDesignVersions(design.id)
      .then(setVersions)
      .catch(() => {});
  }, [design?.id]);

  useEffect(() => {
    if (location.state?.justForked && location.state?.sourceVersion !== undefined) {
      setNotice(`New draft created from version ${location.state.sourceVersion}. Changes here won't affect the current version until you activate this one.`);
      // Clear navigation state
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const pages = useMemo(() => sortPages(design?.pages ?? []), [design?.pages]);
  const selectedPage = pages.find((page) => page.id === selectedPageId) ?? null;
  const existingPdfIds = useMemo(
    () => pages.filter((page) => page.block_type === "static_pdf").map((page) => page.content_id),
    [pages],
  );
  const readOnly = design ? design.status !== "draft" : true;
  const activeVersion = useMemo(() => versions.find((v) => v.status === "active"), [versions]);

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
      if (updated.version_number && updated.version_number > 1) {
        setNotice(`Version ${updated.version_number} is now current. Version ${updated.version_number - 1} has been preserved in version history.`);
      } else {
        setNotice("Design activated.");
      }
      // Refresh version history
      const hist = await listDocumentDesignVersions(updated.id);
      setVersions(hist);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't activate this design.");
    }
  };

  const handleEditDesign = async () => {
    if (!design) return;
    setError(null);
    try {
      const draft = await forkDocumentDesignVersion(design.id);
      navigate(`/document-designs/${draft.id}`, {
        state: { justForked: true, sourceVersion: design.version_number },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't create a new version. Try again.");
    }
  };

  const handleDiscardDraft = async () => {
    if (!design) return;
    setDiscarding(true);
    setError(null);
    try {
      await discardDocumentDesignDraft(design.id);
      setShowDiscardModal(false);
      const groupId = design.version_group_id || design.id;
      navigate(`/document-designs/${groupId}/versions`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We couldn't discard this draft. Try again.");
    } finally {
      setDiscarding(false);
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
          {design.status === "draft" && (
            <>
              <span className="rounded bg-surface-container px-sm py-xs text-sm font-bold text-primary uppercase">
                Draft
              </span>
              <button
                type="button"
                className="rounded border border-error px-md py-xs text-sm font-bold text-error hover:bg-error/10"
                onClick={() => setShowDiscardModal(true)}
              >
                Discard Draft Version
              </button>
              <button
                type="button"
                className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90"
                onClick={handleActivate}
              >
                Activate
              </button>
            </>
          )}
          {design.status === "active" && (
            <>
              <span className="rounded bg-surface-container px-sm py-xs text-sm font-bold text-primary uppercase">
                Current
              </span>
              <button
                type="button"
                className="rounded bg-primary px-md py-xs text-sm font-bold text-white hover:bg-primary/90"
                onClick={handleEditDesign}
              >
                Edit Design
              </button>
            </>
          )}
          {design.status === "superseded" && (
            <span className="rounded bg-surface-container px-sm py-xs text-sm font-bold text-on-surface-variant uppercase">
              Superseded
            </span>
          )}
          <Link
            to={`/document-designs/${design.id}/versions`}
            className="rounded border border-primary px-md py-xs text-sm font-bold text-primary hover:bg-primary/10"
          >
            Version History
          </Link>
        </div>
      </div>

      {design.status === "superseded" && activeVersion && (
        <div className="mt-md flex items-center justify-between gap-sm rounded border border-outline-variant bg-surface-container-lowest p-sm text-sm font-bold text-on-surface">
          <span>
            You're viewing version {design.version_number} — a past version and read-only.{" "}
            <Link to={`/document-designs/${activeVersion.id}`} className="text-primary hover:underline font-bold ml-xs">
              [View current version]
            </Link>
          </span>
        </div>
      )}

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

      {!readOnly && (
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
      )}

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
          ) : readOnly ? (
            <div className="space-y-sm">
              {pages.map((page) => (
                <DesignPageCard
                  key={page.id}
                  page={page}
                  selected={page.id === selectedPageId}
                  onSelect={setSelectedPageId}
                  onRemove={handleRemove}
                  readOnly={true}
                />
              ))}
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
                      readOnly={false}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}
        </div>

        <DesignPageInspector page={selectedPage} onSave={handleSavePage} readOnly={readOnly} />
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

      {showDiscardModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-md">
          <div className="w-full max-w-xl rounded border border-outline-variant bg-surface-container-lowest p-lg shadow-xl">
            <div className="flex items-center justify-between gap-md">
              <h2 className="font-headings text-[14px] font-bold text-on-surface">
                Discard this draft?
              </h2>
              <button
                type="button"
                className="text-sm font-bold text-primary"
                onClick={() => setShowDiscardModal(false)}
                disabled={discarding}
              >
                Close
              </button>
            </div>

            <p className="mt-md text-sm text-on-surface">
              Changes since version {design.version_number ? design.version_number - 1 : 1} will be lost. Version {design.version_number ? design.version_number - 1 : 1} itself stays intact and remains the current version.
            </p>

            {error ? <p className="mt-md text-sm text-error">{error}</p> : null}

            <div className="mt-lg flex justify-end gap-sm">
              <button
                type="button"
                className="rounded border border-outline-variant px-md py-xs text-sm font-bold text-on-surface"
                onClick={() => setShowDiscardModal(false)}
                disabled={discarding}
              >
                Keep Editing
              </button>
              <button
                type="button"
                disabled={discarding}
                className="rounded bg-error px-md py-xs text-sm font-bold text-white hover:bg-error/90 disabled:opacity-50"
                onClick={handleDiscardDraft}
              >
                {discarding ? "Discarding..." : "Discard Draft"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
