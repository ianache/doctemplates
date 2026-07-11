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
  discardDocumentDesignDraft,
  forkDocumentDesignVersion,
  getDocumentDesign,
  listDocumentDesignVersions,
  reorderDesignPages,
  updateDesignPage,
  previewDocumentDesign,
  updateDocumentDesign,
  type DocumentDesignDetail,
  type DocumentDesignListItem,
  type DocumentDesignPage,
} from "../../lib/documentDesigns";
import { getDocumentType, type DocumentTypeField, type DocumentTypeMetadata } from "../../lib/documentTypes";
import { generateMockDataFromFields } from "../../lib/schemaFields";
import AddContentModal from "./components/AddContentModal";
import DesignPageCard from "./components/DesignPageCard";
import DesignPageInspector from "./components/DesignPageInspector";
import { MockDataPanel } from "./components/MockDataPanel";
import { PreviewFrame } from "./components/PreviewFrame";

function sortPages(pages: DocumentDesignPage[]) {
  return [...pages].sort((a, b) => a.position - b.position);
}

function pageLabel(page: DocumentDesignPage | null) {
  if (!page) return "No page selected";
  if (page.title) return page.title;
  if (page.block_type === "html_template") return String(page.snapshot.name ?? "HTML template");
  return String(page.snapshot.filename ?? "Static PDF");
}

function pageMetadata(page: DocumentDesignPage | null) {
  if (!page) return "Select a fragment from the stack";
  if (page.block_type === "html_template") {
    const tokens = Array.isArray(page.snapshot.token_names) ? page.snapshot.token_names : [];
    return tokens.length ? `${tokens.length} token${tokens.length === 1 ? "" : "s"}` : "No tokens";
  }

  const pageCount = Number(page.snapshot.page_count ?? 0);
  const pageStart = page.snapshot.page_start;
  const pageEnd = page.snapshot.page_end;
  const range = pageStart && pageEnd ? `, pages ${pageStart}-${pageEnd}` : "";
  return `${pageCount} page${pageCount === 1 ? "" : "s"}${range}`;
}

function statusLabel(status: string) {
  if (status === "active") return "Current";
  return status;
}

function mergeMockData(
  loaded: Record<string, any>,
  fields: DocumentTypeField[],
  metadata: DocumentTypeMetadata[]
): Record<string, any> {
  const freshData = generateMockDataFromFields(fields);
  const freshMetadata: Record<string, any> = {};
  metadata.forEach((m) => {
    if (m.type === "number") freshMetadata[m.name] = 123.45;
    else if (m.type === "boolean") freshMetadata[m.name] = true;
    else if (m.type === "date") freshMetadata[m.name] = new Date().toISOString().split("T")[0];
    else if (m.type === "datetime") freshMetadata[m.name] = new Date().toISOString();
    else freshMetadata[m.name] = "Sample Text";
  });

  const loadedIsStructured = loaded && typeof loaded.data === "object" && loaded.data !== null && !Array.isArray(loaded.data);
  const needsStructure = metadata.length > 0;

  if (needsStructure) {
    const targetData = loadedIsStructured ? { ...loaded.data } : { ...loaded };
    const targetMetadata = loadedIsStructured && typeof loaded.metadata === "object" && loaded.metadata !== null ? { ...loaded.metadata } : {};

    // Remove metadata keys from targetData if they accidentally leaked there
    metadata.forEach((m) => {
      delete targetData[m.name];
    });

    // Fill missing data keys
    Object.keys(freshData).forEach((key) => {
      if (targetData[key] === undefined) {
        targetData[key] = freshData[key];
      }
    });

    // Fill missing metadata keys
    Object.keys(freshMetadata).forEach((key) => {
      if (targetMetadata[key] === undefined) {
        targetMetadata[key] = freshMetadata[key];
      }
    });

    return { data: targetData, metadata: targetMetadata };
  } else {
    const targetData = loadedIsStructured ? { ...loaded.data } : { ...loaded };
    Object.keys(freshData).forEach((key) => {
      if (targetData[key] === undefined) {
        targetData[key] = freshData[key];
      }
    });
    return targetData;
  }
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

  const [docTypeFields, setDocTypeFields] = useState<DocumentTypeField[]>([]);
  const [metadataDefs, setMetadataDefs] = useState<DocumentTypeMetadata[]>([]);
  const [mockJsonText, setMockJsonText] = useState<string>("{}");
  const [parsedPayload, setParsedPayload] = useState<Record<string, unknown>>({});
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [isSavingMock, setIsSavingMock] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBlob, setPreviewBlob] = useState<Blob | null>(null);
  const [previewMode, setPreviewMode] = useState<"fragment" | "pdf">("fragment");
  const [activeRightTab, setActiveRightTab] = useState<"inspector" | "mockData">("inspector");

  const [leftWidth, setLeftWidth] = useState(380);
  const [rightWidth, setRightWidth] = useState(330);
  const [isResizing, setIsResizing] = useState(false);

  const handleLeftMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = leftWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.max(260, Math.min(600, startWidth + deltaX));
      setLeftWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleRightMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = rightWidth;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = startX - moveEvent.clientX;
      const newWidth = Math.max(260, Math.min(600, startWidth + deltaX));
      setRightWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleSetPreviewMode = (mode: "fragment" | "pdf") => {
    setPreviewMode(mode);
    setActiveRightTab(mode === "pdf" ? "mockData" : "inspector");
  };

  const handleSetActiveRightTab = (tab: "inspector" | "mockData") => {
    setActiveRightTab(tab);
    setPreviewMode(tab === "mockData" ? "pdf" : "fragment");
  };

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
      setNotice(
        `New draft created from version ${location.state.sourceVersion}. Changes here won't affect the current version until you activate this one.`,
      );
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    if (!design?.document_type_id) return;
    let cancelled = false;
    getDocumentType(design.document_type_id)
      .then((data) => {
        if (cancelled) return;
        if (data) {
          setDocTypeFields(data.fields);
          setMetadataDefs(data.metadata_definitions || []);
          let loadedMock: Record<string, unknown> | null = null;
          if (design?.id) {
            try {
              const saved = localStorage.getItem(`mock_payload_${design.id}`);
              if (saved) {
                const parsed = JSON.parse(saved);
                if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
                  loadedMock = parsed as Record<string, unknown>;
                }
              } else if (design.mock_data) {
                loadedMock = design.mock_data;
              }
            } catch (err) {
              console.error("Failed to parse saved mock payload", err);
            }
          }

          let initialMock: Record<string, any>;
          if (loadedMock) {
            initialMock = mergeMockData(loadedMock, data.fields, data.metadata_definitions || []);
            // Save the merged mock back to localStorage to keep it up to date
            localStorage.setItem(`mock_payload_${design.id}`, JSON.stringify(initialMock));
          } else {
            const mockData = generateMockDataFromFields(data.fields);
            if (data.metadata_definitions && data.metadata_definitions.length > 0) {
              const mockMetadata: Record<string, any> = {};
              data.metadata_definitions.forEach((meta) => {
                if (meta.type === "number") mockMetadata[meta.name] = 123.45;
                else if (meta.type === "boolean") mockMetadata[meta.name] = true;
                else if (meta.type === "date") mockMetadata[meta.name] = new Date().toISOString().split("T")[0];
                else if (meta.type === "datetime") mockMetadata[meta.name] = new Date().toISOString();
                else mockMetadata[meta.name] = "Sample Text";
              });
              initialMock = { data: mockData, metadata: mockMetadata };
            } else {
              initialMock = mockData;
            }
          }

          const text = JSON.stringify(initialMock, null, 2);
          setMockJsonText(text);
          setParsedPayload(initialMock);
          setJsonError(null);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setPreviewError("Could not load schema fields for preview setup.");
      });
    return () => {
      cancelled = true;
    };
  }, [design?.document_type_id, design?.id]);

  const handleResetMockData = () => {
    const mockData = generateMockDataFromFields(docTypeFields);
    let initialMock: Record<string, any> = mockData;
    if (metadataDefs && metadataDefs.length > 0) {
      const mockMetadata: Record<string, any> = {};
      metadataDefs.forEach((meta) => {
        if (meta.type === "number") mockMetadata[meta.name] = 123.45;
        else if (meta.type === "boolean") mockMetadata[meta.name] = true;
        else if (meta.type === "date") mockMetadata[meta.name] = new Date().toISOString().split("T")[0];
        else if (meta.type === "datetime") mockMetadata[meta.name] = new Date().toISOString();
        else mockMetadata[meta.name] = "Sample Text";
      });
      initialMock = { data: mockData, metadata: mockMetadata };
    }

    const text = JSON.stringify(initialMock, null, 2);
    setMockJsonText(text);
    setParsedPayload(initialMock);
    setJsonError(null);
    if (design?.id) {
      localStorage.removeItem(`mock_payload_${design.id}`);
    }
  };

  const handleMockJsonChange = (text: string) => {
    setMockJsonText(text);
    try {
      if (!text.trim()) {
        setJsonError("JSON payload cannot be empty");
        return;
      }
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        setJsonError("JSON root must be an object");
      } else {
        setParsedPayload(parsed);
        setJsonError(null);
        if (design?.id) {
          localStorage.setItem(`mock_payload_${design.id}`, JSON.stringify(parsed));
        }
      }
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "Invalid JSON syntax");
    }
  };

  const handleTriggerPdfPreview = async () => {
    if (!design) return;
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const blob = await previewDocumentDesign(design.id, parsedPayload);
      setPreviewBlob(blob);
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to generate PDF preview.");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleSaveMockData = async () => {
    if (!design) return;
    setIsSavingMock(true);
    setPreviewError(null);
    try {
      await updateDocumentDesign(design.id, {
        name: design.name,
        description: design.description,
        mock_data: parsedPayload,
      });
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : "Failed to persist mock data to server.");
    } finally {
      setIsSavingMock(false);
    }
  };

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
        setNotice(
          `Version ${updated.version_number} is now current. Version ${updated.version_number - 1} has been preserved in version history.`,
        );
      } else {
        setNotice("Design activated.");
      }
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
    <section className="-m-lg flex min-h-[calc(100vh-4rem)] overflow-hidden bg-surface-container">
      <aside
        className="flex min-h-0 flex-col bg-surface-bright shrink-0"
        style={{ width: leftWidth }}
      >
        <div className="border-b border-outline-variant p-lg">
          <div className="flex items-start justify-between gap-md">
            <div className="min-w-0">
              <h1 className="truncate font-headings text-headline-lg font-bold text-on-surface">
                {design.name}
              </h1>
              <p className="mt-xs line-clamp-2 text-body-sm text-on-surface-variant">
                {design.description || "No description"}
              </p>
            </div>
            <span className="shrink-0 rounded bg-surface-container-high px-sm py-xs text-label-caps font-bold uppercase text-primary">
              {statusLabel(design.status)}
            </span>
          </div>

          <div className="mt-lg grid grid-cols-2 gap-md text-body-sm">
            <div>
              <p className="font-label-caps text-on-surface-variant">Document Type</p>
              <p className="mt-base font-bold text-on-surface">{design.document_type_name}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Created By</p>
              <p className="mt-base truncate text-on-surface">{design.created_by_email}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Created At</p>
              <p className="mt-base text-on-surface">{new Date(design.created_at).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="font-label-caps text-on-surface-variant">Fragments</p>
              <p className="mt-base text-on-surface">{pages.length}</p>
            </div>
          </div>

          <div className="mt-lg flex flex-wrap gap-sm">
            {design.status === "draft" ? (
              <>
                <button
                  type="button"
                  className="rounded border border-error px-md py-xs text-body-sm font-bold text-error hover:bg-error/10"
                  onClick={() => setShowDiscardModal(true)}
                >
                  Discard
                </button>
                <button
                  type="button"
                  className="rounded bg-primary px-md py-xs text-body-sm font-bold text-white hover:bg-primary/90"
                  onClick={handleActivate}
                >
                  Activate
                </button>
              </>
            ) : null}
            {design.status === "active" ? (
              <button
                type="button"
                className="rounded bg-primary px-md py-xs text-body-sm font-bold text-white hover:bg-primary/90"
                onClick={handleEditDesign}
              >
                Edit Design
              </button>
            ) : null}
            <Link
              to={`/document-designs/${design.id}/versions`}
              className="rounded border border-primary px-md py-xs text-body-sm font-bold text-primary hover:bg-primary/10"
            >
              Version History
            </Link>
          </div>

          {design.status === "superseded" && activeVersion ? (
            <div className="mt-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-body-sm font-bold text-on-surface">
              Past version.{" "}
              <Link to={`/document-designs/${activeVersion.id}`} className="text-primary hover:underline">
                View current version
              </Link>
            </div>
          ) : null}

          {error ? <p className="mt-md rounded border border-error/30 p-sm text-body-sm text-error">{error}</p> : null}
          {notice ? (
            <div className="mt-md rounded border border-outline-variant bg-surface-container-lowest p-sm text-body-sm text-on-surface">
              <div className="flex flex-wrap items-center justify-between gap-sm">
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
            </div>
          ) : null}
        </div>

        <div className="flex min-h-0 flex-1 flex-col p-md">
          <div className="mb-md flex items-center justify-between gap-sm">
            <div>
              <h2 className="font-headings text-headline-md text-on-surface">Fragments</h2>
              <p className="text-body-sm text-on-surface-variant">Ordered document body</p>
            </div>
            {!readOnly ? (
              <div className="flex gap-xs">
                <button
                  type="button"
                  className="rounded bg-primary px-sm py-xs text-label-caps font-bold text-white hover:bg-primary/90"
                  onClick={() => setModalMode("template")}
                >
                  Template
                </button>
                <button
                  type="button"
                  className="rounded border border-primary px-sm py-xs text-label-caps font-bold text-primary hover:bg-primary/10"
                  onClick={() => setModalMode("pdf")}
                >
                  PDF
                </button>
              </div>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto pr-xs">
            {pages.length === 0 ? (
              <div className="rounded border border-outline-variant bg-surface-container-lowest px-lg py-xl text-center">
                <p className="font-headings text-headline-md font-bold text-on-surface">Empty fragment stack</p>
                <p className="mt-xs text-body-sm text-on-surface-variant">
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
        </div>
      </aside>

      {/* Left Resize Handle */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-primary/45 active:bg-primary transition-colors h-full shrink-0 z-40 border-r border-outline-variant hover:border-transparent"
        onMouseDown={handleLeftMouseDown}
      />

      <main className="flex min-h-[640px] flex-1 flex-col overflow-hidden bg-surface-container">
        <div className="flex items-center justify-between gap-md border-b border-outline-variant bg-surface px-lg py-md">
          <div className="min-w-0">
            <p className="font-label-caps text-on-surface-variant">
              {previewMode === "pdf"
                ? "Generated PDF"
                : selectedPage
                ? `Page ${selectedPage.position + 1}`
                : "Preview"}
            </p>
            <h2 className="truncate font-headings text-headline-md text-on-surface">
              {previewMode === "pdf" ? "Document Previsualization" : pageLabel(selectedPage)}
            </h2>
          </div>
          <div className="flex items-center gap-md">
            <div className="flex border border-outline-variant rounded bg-surface-container-low p-[2px]">
              <button
                type="button"
                className={`rounded px-sm py-xs text-xs font-bold ${
                  previewMode === "fragment"
                    ? "bg-surface text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
                onClick={() => handleSetPreviewMode("fragment")}
              >
                Fragment Preview
              </button>
              <button
                type="button"
                className={`rounded px-sm py-xs text-xs font-bold ${
                  previewMode === "pdf"
                    ? "bg-surface text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
                onClick={() => handleSetPreviewMode("pdf")}
              >
                PDF Preview
              </button>
            </div>
            {previewMode === "fragment" && (
              <span className="rounded border border-outline-variant bg-surface-container-low px-sm py-xs text-label-caps text-on-surface-variant">
                {pageMetadata(selectedPage)}
              </span>
            )}
          </div>
        </div>

        <div className={`page-canvas-bg flex min-h-0 flex-1 items-start justify-center overflow-auto p-xl ${isResizing ? 'pointer-events-none' : ''}`}>
          {previewMode === "pdf" ? (
            <div className="w-full max-w-[800px] bg-surface-container-lowest p-md border border-outline-variant rounded-lg shadow-lg">
              <PreviewFrame blob={previewBlob} loading={previewLoading} error={previewError} />
            </div>
          ) : (
            <div className="flex min-h-[760px] w-full max-w-[595px] flex-col border border-outline-variant bg-white p-xl shadow-lg">
              {selectedPage ? (
                selectedPage.block_type === "html_template" && typeof selectedPage.snapshot.html === "string" ? (
                  <iframe
                    title={`Preview ${pageLabel(selectedPage)}`}
                    className="h-full min-h-[680px] w-full flex-1 border-0 bg-white"
                    srcDoc={`
                      <style>
                        body {
                          font-family: Helvetica, Arial, sans-serif;
                          font-size: 10pt;
                          line-height: 1.4;
                        }
                        ${selectedPage.snapshot.css || ""}
                      </style>
                      ${selectedPage.snapshot.html || ""}
                    `}
                  />
                ) : (
                  <div className="flex flex-1 flex-col items-center justify-center gap-md text-center">
                    <span className="material-symbols-outlined text-[56px] text-primary">picture_as_pdf</span>
                    <div>
                      <h3 className="font-headings text-headline-md text-on-surface">{pageLabel(selectedPage)}</h3>
                      <p className="mt-xs text-body-sm text-on-surface-variant">{pageMetadata(selectedPage)}</p>
                    </div>
                  </div>
                )
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center gap-md text-center">
                  <span className="material-symbols-outlined text-[56px] text-on-surface-variant">
                    dashboard_customize
                  </span>
                  <div>
                    <h3 className="font-headings text-headline-md text-on-surface">Select a fragment</h3>
                    <p className="mt-xs text-body-sm text-on-surface-variant">
                      The selected page preview appears here.
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-auto flex justify-between border-t border-outline-variant pt-md text-[10px] text-on-surface-variant">
                <span>Precision Archival</span>
                <span>{selectedPage ? `Page ${selectedPage.position + 1} of ${pages.length}` : `${pages.length} pages`}</span>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Right Resize Handle */}
      <div
        className="w-1.5 cursor-col-resize hover:bg-primary/45 active:bg-primary transition-colors h-full shrink-0 z-40 border-l border-outline-variant hover:border-transparent"
        onMouseDown={handleRightMouseDown}
      />

      <aside
        className="min-h-0 overflow-y-auto bg-surface p-md flex flex-col gap-md shrink-0"
        style={{ width: rightWidth }}
      >
        <div className="flex border border-outline-variant rounded bg-surface-container-low p-[2px] shrink-0">
          <button
            type="button"
            className={`flex-1 rounded py-xs text-xs font-bold text-center ${
              activeRightTab === "inspector"
                ? "bg-surface text-primary shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => handleSetActiveRightTab("inspector")}
          >
            Page Inspector
          </button>
          <button
            type="button"
            className={`flex-1 rounded py-xs text-xs font-bold text-center ${
              activeRightTab === "mockData"
                ? "bg-surface text-primary shadow-sm"
                : "text-on-surface-variant hover:text-on-surface"
            }`}
            onClick={() => handleSetActiveRightTab("mockData")}
          >
            Mock Data Preview
          </button>
        </div>

        <div className="flex-1 min-h-0">
          {activeRightTab === "inspector" ? (
            <DesignPageInspector page={selectedPage} onSave={handleSavePage} readOnly={readOnly} />
          ) : (
            <>
              {previewError ? (
                <div className="mb-sm text-xs text-error bg-error/5 border border-error/20 p-xs rounded font-mono">
                  {previewError}
                </div>
              ) : null}
              <MockDataPanel
                value={mockJsonText}
                onChange={handleMockJsonChange}
                onReset={handleResetMockData}
                onPreview={handleTriggerPdfPreview}
                onSave={handleSaveMockData}
                isValidJson={!jsonError}
                parseError={jsonError}
                loadingPreview={previewLoading}
                isSavingMock={isSavingMock}
              />
            </>
          )}
        </div>
      </aside>

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

      {showDiscardModal ? (
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
              Changes since version {design.version_number ? design.version_number - 1 : 1} will be lost. Version{" "}
              {design.version_number ? design.version_number - 1 : 1} itself stays intact and remains the current
              version.
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
      ) : null}
    </section>
  );
}
