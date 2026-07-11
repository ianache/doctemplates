import { type FormEvent, useEffect, useState, useRef, useMemo } from "react";
import { useNavigate, Link, useParams } from "react-router-dom";

import PageHeader from "../../components/PageHeader";
import {
  getDocumentType,
  listDocumentTypes,
  type DocumentTypeDetail,
  type DocumentTypeListItem,
  type DocumentTypeField,
} from "../../lib/documentTypes";
import { buildSchemaFieldTree, type SchemaFieldTreeNode } from "../../lib/schemaFields";
import { createHtmlTemplate, getHtmlTemplate, updateHtmlTemplate } from "../../lib/content";

function getDragTextForNode(node: SchemaFieldTreeNode, allFields: DocumentTypeField[]): string {
  if (node.type === "leaf") {
    const path = node.fullPath;
    const lastListIndex = path.lastIndexOf("[]");
    if (lastListIndex !== -1) {
      const listPath = path.substring(0, lastListIndex);
      const relativePath = path.substring(lastListIndex + 3); // Skip "[]" and "."
      const listParts = listPath.split(".");
      const rawListName = listParts[listParts.length - 1];
      const iteratorName = rawListName.endsWith("s") ? rawListName.substring(0, rawListName.length - 1) : "item";
      return `{% for ${iteratorName} in ${listPath} %}\n  {{ ${iteratorName}.${relativePath} }}\n{% endfor %}`;
    } else {
      return `{{ ${node.fullPath} }}`;
    }
  } else if (node.type === "list") {
    const listPath = node.fullPath;
    const listParts = listPath.split(".");
    const rawListName = listParts[listParts.length - 1];
    const iteratorName = rawListName.endsWith("s") ? rawListName.substring(0, rawListName.length - 1) : "item";
    
    // Find all fields nested directly under this list
    const subFields = allFields.filter(f => f.name.startsWith(listPath + "."));
    const headers = subFields.map(f => {
      const name = f.name.substring(listPath.length + 1); // skip listPath + "."
      return `<th>${name.charAt(0).toUpperCase() + name.slice(1)}</th>`;
    }).join("\n      ");
    const cells = subFields.map(f => {
      const name = f.name.substring(listPath.length + 1); // skip listPath + "."
      return `<td>{{ ${iteratorName}.${name} }}</td>`;
    }).join("\n      ");
    
    return `<table>\n  <thead>\n    <tr>\n      ${headers}\n    </tr>\n  </thead>\n  <tbody>\n    {% for ${iteratorName} in ${listPath.replace("[]", "")} %}\n    <tr>\n      ${cells}\n    </tr>\n    {% endfor %}\n  </tbody>\n</table>`;
  } else {
    return `<!-- ${node.fullPath} -->`;
  }
}

export default function HtmlTemplateCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = !!id;
  const visualRef = useRef<HTMLDivElement>(null);

  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [html, setHtml] = useState("");
  const [htmlTouched, setHtmlTouched] = useState(false);
  const [mockDataJson, setMockDataJson] = useState("");
  const [mockDataError, setMockDataError] = useState<string | null>(null);

  // Layout & Editing Modes
  const [editorMode, setEditorMode] = useState<"visual" | "code">("code");
  const [collapsedTokens, setCollapsedTokens] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    
    const init = async () => {
      try {
        const rows = await listDocumentTypes();
        if (cancelled) return;
        setDocumentTypes(rows);

        if (isEditMode && id) {
          const t = await getHtmlTemplate(id);
          if (cancelled) return;
          if (t) {
            setName(t.name);
            setDocumentTypeId(t.document_type_id);
            setHtml(t.html);
            setHtmlTouched(true);
            if (t.mock_data) {
              setMockDataJson(JSON.stringify(t.mock_data, null, 2));
            }
            setTimeout(() => {
              if (visualRef.current) {
                visualRef.current.innerHTML = t.html;
              }
            }, 0);
          }
        } else {
          setDocumentTypeId(rows[0]?.id ?? "");
        }
      } catch (err) {
        console.error("Failed to load template/document types", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    init();

    return () => {
      cancelled = true;
    };
  }, [id, isEditMode]);

  useEffect(() => {
    if (!documentTypeId) {
      setSelectedDocumentType(null);
      return;
    }

    let cancelled = false;
    getDocumentType(documentTypeId).then((detail) => {
      if (cancelled) return;
      setSelectedDocumentType(detail);
      if (!htmlTouched && detail?.fields?.length) {
        setHtml(`<p>Welcome {{ ${detail.fields[0].name} }}</p>`);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [documentTypeId, htmlTouched]);

  // Synchronize visual and code editor inner states
  const handleToggleMode = (mode: "visual" | "code") => {
    setEditorMode(mode);
    if (mode === "visual") {
      setTimeout(() => {
        if (visualRef.current) {
          visualRef.current.innerHTML = html;
        }
      }, 0);
    }
  };

  const handleVisualChange = () => {
    if (visualRef.current) {
      setHtml(visualRef.current.innerHTML);
      setHtmlTouched(true);
    }
  };

  // Drag and Drop Logic
  const handleTextareaDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    const text = e.dataTransfer.getData("text/plain");
    if (!text) return;
    
    const textarea = e.currentTarget;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const currentVal = textarea.value;
    
    const newVal = currentVal.substring(0, start) + text + currentVal.substring(end);
    setHtml(newVal);
    setHtmlTouched(true);
    
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + text.length, start + text.length);
    }, 0);
  };

  const handleVisualDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const text = e.dataTransfer.getData("text/plain");
    if (!text) return;

    let range: Range | null = null;
    if (document.caretRangeFromPoint) {
      range = document.caretRangeFromPoint(e.clientX, e.clientY);
    } else if ((e.target as any).ownerDocument && (e.target as any).ownerDocument.caretPositionFromPoint) {
      const position = (e.target as any).ownerDocument.caretPositionFromPoint(e.clientX, e.clientY);
      if (position) {
        range = document.createRange();
        range.setStart(position.offsetNode, position.offset);
        range.collapse(true);
      }
    }

    if (range) {
      range.deleteContents();
      
      let nodeToInsert: Node;
      if (text.startsWith("{{") || text.startsWith("{%")) {
        const span = document.createElement("span");
        span.className = "mx-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded font-mono text-xs inline-block select-all";
        span.setAttribute("contenteditable", "false");
        span.innerText = text.replace(/\n/g, " ");
        nodeToInsert = span;
      } else {
        nodeToInsert = document.createTextNode(text);
      }
      
      range.insertNode(nodeToInsert);
      handleVisualChange();
    }
  };

  // Rich Text Toolbar Actions
  const execToolbarCommand = (command: string, value: string = "") => {
    document.execCommand(command, false, value);
    handleVisualChange();
  };

  const insertTable = () => {
    const tableHtml = `
      <table class="w-full border-collapse border border-outline-variant my-md">
        <thead>
          <tr class="bg-surface-container">
            <th class="border border-outline-variant p-2 text-left">Header 1</th>
            <th class="border border-outline-variant p-2 text-left">Header 2</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="border border-outline-variant p-2">Data 1</td>
            <td class="border border-outline-variant p-2">Data 2</td>
          </tr>
        </tbody>
      </table>
    `;
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0) {
      const range = sel.getRangeAt(0);
      range.deleteContents();
      const el = document.createElement("div");
      el.innerHTML = tableHtml;
      const fragment = document.createDocumentFragment();
      let node;
      while ((node = el.firstChild)) {
        fragment.appendChild(node);
      }
      range.insertNode(fragment);
      handleVisualChange();
    }
  };

  const handleSubmitForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!name.trim()) {
      setSubmitError("Template name is required.");
      return;
    }

    if (!documentTypeId) {
      setSubmitError("Choose a document type.");
      return;
    }

    let parsedMock: Record<string, unknown> | null = null;
    if (mockDataJson.trim()) {
      try {
        parsedMock = JSON.parse(mockDataJson);
        if (typeof parsedMock !== "object" || parsedMock === null || Array.isArray(parsedMock)) {
          setSubmitError("Mock Data JSON must be a valid JSON object.");
          return;
        }
      } catch (err) {
        setSubmitError(`Mock Data JSON has syntax errors: ${err instanceof Error ? err.message : "Error"}`);
        return;
      }
    }

    try {
      if (isEditMode && id) {
        await updateHtmlTemplate(id, {
          document_type_id: documentTypeId,
          name,
          html,
          mock_data: parsedMock,
        });
        navigate(`/content/templates/${id}`);
      } else {
        const created = await createHtmlTemplate({
          document_type_id: documentTypeId,
          name,
          html,
          mock_data: parsedMock,
        });
        navigate(`/content/templates/${created.id}`);
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "We couldn't save this template.");
    }
  };

  const toggleTokenNode = (nodeId: string) => {
    setCollapsedTokens((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const tokenTree = useMemo(() => {
    if (!selectedDocumentType?.fields) return [];
    return buildSchemaFieldTree(selectedDocumentType.fields);
  }, [selectedDocumentType]);

  const renderTokenNode = (node: SchemaFieldTreeNode) => {
    const isLeaf = node.type === "leaf";
    const isList = node.type === "list";
    const isObject = node.type === "object";
    const hasChildren = node.children && node.children.length > 0;
    const isCollapsed = collapsedTokens.has(node.id);

    return (
      <div key={node.id} className="select-none mt-xs">
        <div
          draggable
          onDragStart={(e) => {
            if (selectedDocumentType) {
              const text = getDragTextForNode(node, selectedDocumentType.fields);
              e.dataTransfer.setData("text/plain", text);
            }
          }}
          className={`flex items-center gap-xs py-xs px-sm rounded cursor-grab hover:bg-surface-container-high transition-colors group border border-transparent active:border-primary/30 ${
            isLeaf ? "text-on-surface" : "font-bold text-secondary"
          }`}
        >
          {!isLeaf ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggleTokenNode(node.id);
              }}
              className="material-symbols-outlined text-secondary hover:text-primary transition-colors text-[18px] focus:outline-none"
            >
              {isCollapsed ? "chevron_right" : "expand_more"}
            </button>
          ) : (
            <div className="w-[18px]"></div>
          )}

          <span className="material-symbols-outlined text-secondary text-[18px]">
            {isList ? "list" : isObject ? (isCollapsed ? "folder" : "folder_open") : "code"}
          </span>

          <span className="font-mono text-xs">{node.name}</span>

          {isLeaf && (
            <span className="rounded bg-surface-container-high px-1.5 py-0.5 text-[9px] font-bold uppercase text-on-surface-variant font-mono">
              {node.fieldType}
            </span>
          )}

          <span className="material-symbols-outlined text-secondary text-[16px] opacity-0 group-hover:opacity-100 ml-auto transition-opacity">
            drag_indicator
          </span>
        </div>

        {!isLeaf && !isCollapsed && hasChildren && (
          <div className="ml-md border-l border-outline-variant pl-xs space-y-xs">
            {node.children.map(renderTokenNode)}
          </div>
        )}
      </div>
    );
  };

  return (
    <section>
      <PageHeader
        breadcrumbs={[
          { label: "Content Library" },
          { label: "Templates", to: "/content/templates" },
          { label: isEditMode ? "Edit HTML Template" : "New HTML Template" }
        ]}
        title={isEditMode ? "Edit HTML Template" : "Create HTML Template"}
      />

      {submitError ? (
        <div className="mb-md rounded border border-error/30 bg-background p-sm text-sm text-error">
          {submitError}
        </div>
      ) : null}

      <div className="grid grid-cols-[1fr_320px] gap-lg items-start mt-lg">
        {/* Main Workspace (Left) */}
        <form onSubmit={handleSubmitForm} className="space-y-lg rounded-lg border border-outline-variant bg-surface-container-lowest p-md">
          <div className="grid gap-md md:grid-cols-2">
            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Template Name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                placeholder="e.g. Booking Confirmation"
                className="mt-xs w-full rounded border border-outline-variant px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white font-semibold"
              />
            </label>

            <label className="block text-[11px] font-bold uppercase tracking-[0.05em] text-secondary">
              Associated Document Type
              <select
                value={documentTypeId}
                onChange={(event) => {
                  setDocumentTypeId(event.target.value);
                  setHtmlTouched(false);
                }}
                className="mt-xs w-full rounded border border-outline-variant px-sm py-xs text-sm text-on-surface focus:border-primary focus:outline-none bg-white font-semibold"
              >
                {loading ? <option>Loading...</option> : null}
                {!loading && documentTypes.length === 0 ? <option value="">No document types available</option> : null}
                {documentTypes.map((documentType) => (
                  <option key={documentType.id} value={documentType.id}>
                    {documentType.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {/* Editor Container */}
          <div className="border border-outline-variant rounded-lg overflow-hidden flex flex-col bg-white">
            {/* Editor Mode Header Toolbar */}
            <div className="flex items-center justify-between bg-surface-container-low px-sm py-xs border-b border-outline-variant select-none">
              <div className="flex gap-xs bg-surface-container rounded p-0.5 border border-outline-variant">
                <button
                  type="button"
                  onClick={() => handleToggleMode("code")}
                  className={`flex items-center gap-xs px-sm py-1 rounded text-xs font-bold transition-all ${
                    editorMode === "code"
                      ? "bg-white text-primary shadow-sm"
                      : "text-secondary hover:text-on-surface"
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">code</span>
                  Escritura Directa
                </button>
                <button
                  type="button"
                  onClick={() => handleToggleMode("visual")}
                  className={`flex items-center gap-xs px-sm py-1 rounded text-xs font-bold transition-all ${
                    editorMode === "visual"
                      ? "bg-white text-primary shadow-sm"
                      : "text-secondary hover:text-on-surface"
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">format_align_left</span>
                  Editor Visual
                </button>
              </div>

              {/* Rich Text Toolbar Actions (Only in Visual Mode) */}
              {editorMode === "visual" && (
                <div className="flex items-center gap-xs border-l border-outline-variant/60 pl-sm ml-sm">
                  <button
                    type="button"
                    onClick={() => execToolbarCommand("bold")}
                    className="p-1 rounded hover:bg-surface-container text-secondary hover:text-on-surface text-sm font-bold material-symbols-outlined"
                    title="Bold"
                  >
                    format_bold
                  </button>
                  <button
                    type="button"
                    onClick={() => execToolbarCommand("italic")}
                    className="p-1 rounded hover:bg-surface-container text-secondary hover:text-on-surface text-sm font-bold material-symbols-outlined"
                    title="Italic"
                  >
                    format_italic
                  </button>
                  <button
                    type="button"
                    onClick={() => execToolbarCommand("underline")}
                    className="p-1 rounded hover:bg-surface-container text-secondary hover:text-on-surface text-sm font-bold material-symbols-outlined"
                    title="Underline"
                  >
                    format_underlined
                  </button>
                  <button
                    type="button"
                    onClick={() => execToolbarCommand("formatBlock", "h2")}
                    className="p-1 rounded hover:bg-surface-container text-secondary hover:text-on-surface text-xs font-bold"
                    title="Heading"
                  >
                    H2
                  </button>
                  <button
                    type="button"
                    onClick={() => execToolbarCommand("formatBlock", "p")}
                    className="p-1 rounded hover:bg-surface-container text-secondary hover:text-on-surface text-xs font-bold"
                    title="Paragraph"
                  >
                    P
                  </button>
                  <button
                    type="button"
                    onClick={() => insertTable()}
                    className="p-1 rounded hover:bg-surface-container text-secondary hover:text-on-surface text-sm font-bold material-symbols-outlined"
                    title="Insert Table"
                  >
                    table_chart
                  </button>
                </div>
              )}
            </div>

            {/* Workspace Areas */}
            <div className="relative min-h-[400px]">
              {/* Escritura Directa (Textarea / Code View) */}
              {editorMode === "code" && (
                <div className="w-full h-full flex">
                  {/* Line numbers dummy sidebar */}
                  <div className="w-12 bg-surface-container-low border-r border-outline-variant py-sm text-right pr-sm select-none font-mono text-[11px] text-outline text-height-relaxed">
                    {Array.from({ length: Math.max(15, html.split("\n").length) }).map((_, i) => (
                      <div key={i}>{i + 1}</div>
                    ))}
                  </div>
                  <textarea
                    value={html}
                    onChange={(event) => {
                      setHtml(event.target.value);
                      setHtmlTouched(true);
                    }}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleTextareaDrop}
                    rows={16}
                    placeholder="<!-- Write your HTML template code directly here. Drag and drop tokens. -->"
                    className="flex-1 w-full bg-slate-900 text-slate-100 p-sm font-mono text-sm leading-relaxed focus:outline-none resize-y min-h-[400px]"
                  />
                </div>
              )}

              {/* Editor Visual (contentEditable canvas) */}
              {editorMode === "visual" && (
                <div className="p-lg bg-surface-container-lowest min-h-[400px] overflow-y-auto">
                  <div
                    ref={visualRef}
                    contentEditable
                    onInput={handleVisualChange}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleVisualDrop}
                    className="w-full min-h-[350px] border border-dashed border-outline rounded-lg bg-white p-lg focus:outline-none prose max-w-none shadow-sm"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Mock Data Section */}
          <div className="rounded-lg border border-outline-variant bg-surface-container-low p-md">
            <h3 className="text-sm font-bold text-on-surface flex items-center gap-xs">
              <span className="material-symbols-outlined text-[18px] text-primary">data_object</span>
              Mock Data for Preview
            </h3>
            <p className="text-xs text-secondary mt-xs">
              Configure sample values matching your Document Type fields.
            </p>
            <label className="block mt-sm">
              <textarea
                value={mockDataJson}
                onChange={(e) => {
                  setMockDataJson(e.target.value);
                  try {
                    if (e.target.value.trim()) {
                      JSON.parse(e.target.value);
                      setMockDataError(null);
                    } else {
                      setMockDataError(null);
                    }
                  } catch (err) {
                    setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
                  }
                }}
                rows={6}
                placeholder={`{\n  "cliente": {\n    "nombre": "Juan Pérez",\n    "edad": 30\n  }\n}`}
                className={`mt-xs w-full rounded border font-mono text-xs p-sm bg-white focus:outline-none ${
                  mockDataError ? "border-error focus:border-error" : "border-outline-variant focus:border-primary"
                }`}
              />
            </label>
            {mockDataError && (
              <p className="text-xs text-error mt-xs font-mono">{mockDataError}</p>
            )}
          </div>

          <div className="flex justify-end gap-sm mt-md">
            <Link
              to="/content/templates"
              className="rounded border border-outline-variant bg-surface-container px-lg py-sm text-sm font-bold text-secondary hover:bg-surface-container-high active:scale-95 transition-all"
            >
              Cancel
            </Link>
            <button
              type="submit"
              className="rounded bg-primary px-lg py-sm text-sm font-bold text-white hover:bg-primary/90 active:scale-95 transition-all"
            >
              {isEditMode ? "Save Changes" : "Create Template"}
            </button>
          </div>
        </form>

        {/* Sidebar Panel: Token Explorer (Right) */}
        <aside className="rounded-lg border border-outline-variant bg-surface-container-lowest p-md flex flex-col max-h-[620px] overflow-y-auto sticky top-4">
          <div className="border-b border-outline-variant pb-sm mb-sm">
            <h3 className="font-headings text-[14px] font-bold text-on-surface flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-[20px]">explore</span>
              EXPLORADOR DE TOKENS
            </h3>
            <p className="text-[11px] text-secondary mt-xs">
              Drag tokens directly into the HTML code or visual canvas.
            </p>
          </div>

          <div className="space-y-sm flex-1">
            {!selectedDocumentType?.fields?.length ? (
              <div className="text-center py-lg border border-dashed border-outline-variant rounded bg-surface p-sm">
                <p className="text-xs text-secondary">
                  Select a document type on the left to explore available tokens.
                </p>
              </div>
            ) : (
              <div className="space-y-xs pr-xs">
                {tokenTree.map(renderTokenNode)}
              </div>
            )}
          </div>

          {/* Help box */}
          <div className="mt-md rounded bg-surface-container p-sm border border-outline-variant text-[11px] leading-relaxed text-secondary select-none">
            <div className="font-bold flex items-center gap-1 text-on-surface mb-1">
              <span className="material-symbols-outlined text-[14px] text-primary">info</span>
              Repetitive Lists Support
            </div>
            If you drag a property from a list, it will generate a Jinja loop <code className="bg-white px-1 border border-outline rounded font-mono">{"{% for %}"}</code> automatically. If you drag the list node itself (e.g. <code className="bg-white px-1 border border-outline rounded font-mono">{"cita.equipos[]"}</code>), it will generate a fully loopable HTML table!
          </div>
        </aside>
      </div>
    </section>
  );
}
