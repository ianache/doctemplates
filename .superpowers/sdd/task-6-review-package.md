# Task 6 Review Package

## Report
# Task 6 Report: AI Proposal Panel UI

## Status

Completed.

## Files Changed

- `frontend/src/pages/content/components/AiProposalPanel.tsx`
- `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`

## Tests Run and Results

- `rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"` - passed (`tsc -b && vite build`).

## Self-Review

- The panel only enables AI improvements for persisted templates and explains the limitation for new templates.
- It loads proposal history safely, submits the current HTML, CSS, and validated mock-data object, and exposes summary, HTML, and CSS proposal views.
- Applying an eligible proposal updates the parent HTML and CSS state and marks HTML as touched.
- The editor's right panel now allocates equal scrollable thirds to AI, CSS, and mock data.
- No unrelated workspace changes were modified. No git add or commit commands were run.

## Concerns

- The build completed with Vite plugin timing and >500 kB chunk-size warnings; neither is caused by this task.
- The requested write scope did not permit adding automated frontend tests, so validation is limited to the production build and source review.

## File: frontend/src/pages/content/components/AiProposalPanel.tsx
`
import { useEffect, useState } from "react";

import {
  createTemplateAiProposal,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type TemplateAiProposal,
} from "../../../lib/content";

interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  onApply: (proposal: TemplateAiProposal) => void;
}

function parseMockData(mockDataJson: string): Record<string, unknown> | null {
  if (!mockDataJson.trim()) return null;
  const parsed = JSON.parse(mockDataJson);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Mock data must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

export default function AiProposalPanel({ templateId, html, css, mockDataJson, onApply }: AiProposalPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [proposals, setProposals] = useState<TemplateAiProposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<TemplateAiProposal | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "html" | "css">("summary");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!templateId) return;
    let cancelled = false;
    listTemplateAiProposals(templateId)
      .then((rows) => {
        if (cancelled) return;
        setProposals(rows);
        setActiveProposal(rows[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setError("We couldn't load AI proposal history.");
      });
    return () => {
      cancelled = true;
    };
  }, [templateId]);

  const requestProposal = async () => {
    if (!templateId || !instruction.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
      });
      setProposals((current) => [proposal, ...current]);
      setActiveProposal(proposal);
      setActiveTab("summary");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI proposal failed.");
    } finally {
      setLoading(false);
    }
  };

  const applyProposal = async () => {
    if (!templateId || !activeProposal || !activeProposal.is_applyable) return;
    const applied = await markTemplateAiProposalApplied(templateId, activeProposal.id);
    onApply(applied);
    setProposals((current) => current.map((proposal) => (proposal.id === applied.id ? applied : proposal)));
    setActiveProposal(applied);
  };

  if (!templateId) {
    return (
      <div className="rounded border border-outline-variant bg-surface-container-low p-sm text-xs text-secondary">
        AI improvements are available after this template is created.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-sm rounded border border-outline-variant bg-white p-sm">
      <div className="flex items-center gap-xs">
        <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
        <h3 className="font-headings text-sm font-bold text-on-surface">AI Improve</h3>
      </div>

      <textarea
        value={instruction}
        onChange={(event) => setInstruction(event.target.value)}
        rows={3}
        aria-label="AI improvement instruction"
        className="w-full rounded border border-outline-variant p-sm text-xs text-on-surface focus:border-primary focus:outline-none"
      />

      <button
        type="button"
        onClick={requestProposal}
        disabled={loading || !instruction.trim()}
        className="rounded bg-primary px-md py-xs text-xs font-bold text-white disabled:opacity-50"
      >
        {loading ? "Generating..." : "Suggest improvement"}
      </button>

      {error ? <p className="text-xs text-error">{error}</p> : null}

      {activeProposal ? (
        <div className="space-y-sm border-t border-outline-variant pt-sm">
          <div className="flex gap-xs">
            {(["summary", "html", "css"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded px-sm py-xs text-xs font-bold ${
                  activeTab === tab ? "bg-primary text-white" : "bg-surface-container text-secondary"
                }`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>

          {activeTab === "summary" ? (
            <div className="space-y-xs text-xs">
              <p className="text-on-surface">{activeProposal.summary || "No summary provided."}</p>
              {activeProposal.validation_errors.length ? (
                <ul className="list-disc pl-md text-error">
                  {activeProposal.validation_errors.map((validationError) => (
                    <li key={validationError}>{validationError}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <textarea
              readOnly
              value={activeTab === "html" ? activeProposal.proposed_html : activeProposal.proposed_css}
              rows={10}
              className="w-full rounded border border-outline-variant bg-slate-900 p-sm font-mono text-xs text-slate-100"
            />
          )}

          <button
            type="button"
            onClick={applyProposal}
            disabled={!activeProposal.is_applyable}
            className="rounded border border-primary px-md py-xs text-xs font-bold text-primary disabled:border-outline-variant disabled:text-secondary"
          >
            Apply proposal
          </button>
        </div>
      ) : null}

      {proposals.length ? (
        <div className="border-t border-outline-variant pt-sm">
          <h4 className="text-[11px] font-bold uppercase text-secondary">History</h4>
          <div className="mt-xs max-h-32 overflow-y-auto space-y-xs">
            {proposals.map((proposal) => (
              <button
                key={proposal.id}
                type="button"
                onClick={() => setActiveProposal(proposal)}
                className="block w-full rounded border border-outline-variant px-sm py-xs text-left text-xs hover:bg-surface-container"
              >
                <span className="font-bold">{proposal.status}</span> - {new Date(proposal.created_at).toLocaleString()}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
`

## File: frontend/src/pages/content/HtmlTemplateCreatePage.tsx
`
import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createHtmlTemplate,
  getHtmlTemplate,
  updateHtmlTemplate,
  previewHtmlTemplate,
  type TemplateAiProposal,
} from "../../lib/content";
import { getDocumentType, listDocumentTypes, type DocumentTypeDetail, type DocumentTypeListItem } from "../../lib/documentTypes";
import { buildSchemaFieldTree, type SchemaFieldTreeNode } from "../../lib/schemaFields";
import AiProposalPanel from "./components/AiProposalPanel";

function getDragTextForNode(node: SchemaFieldTreeNode, fields: any[]): string {
  if (node.type === "list") {
    const listPath = node.fullPath;
    const cleanPath = listPath.replace(/\[\]/g, "");
    const listVar = cleanPath.split(".").pop() || "item";
    const itemAlias = listVar.slice(0, -1) || "item";

    const childFields = fields.filter(f => f.name.startsWith(cleanPath + "."));
    const columns = childFields.map(f => {
      const relPath = f.name.slice((cleanPath + ".").length);
      return {
        header: relPath.split(".").pop() || relPath,
        expr: `{{ ${itemAlias}.${relPath} }}`
      };
    });

    if (columns.length === 0) {
      columns.push({ header: "Item", expr: `{{ ${itemAlias} }}` });
    }

    return `
<table>
  <thead>
    <tr>
      ${columns.map(c => `<th>${c.header}</th>`).join("\n      ")}
    </tr>
  </thead>
  <tbody>
    {% for ${itemAlias} in ${cleanPath} %}
    <tr>
      ${columns.map(c => `<td>${c.expr}</td>`).join("\n      ")}
    </tr>
    {% endfor %}
  </tbody>
</table>`;
  }

  const isInsideList = node.fullPath.includes("[]");
  if (isInsideList) {
    const parts = node.fullPath.split("[]");
    const listPart = parts[0];
    const subPart = parts[1];
    const listVar = listPart.split(".").pop() || "item";
    const itemAlias = listVar.slice(0, -1) || "item";
    const cleanSubPart = subPart.startsWith(".") ? subPart.slice(1) : subPart;

    return `{% for ${itemAlias} in ${listPart} %}{{ ${itemAlias}.${cleanSubPart} }}{% endfor %}`;
  }

  return `{{ ${node.fullPath} }}`;
}

export default function HtmlTemplateCreatePage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = !!id;

  const [documentTypes, setDocumentTypes] = useState<DocumentTypeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentTypeDetail | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [documentTypeId, setDocumentTypeId] = useState("");
  const [html, setHtml] = useState("");
  const [htmlTouched, setHtmlTouched] = useState(false);
  const [css, setCss] = useState("");
  const [mockDataJson, setMockDataJson] = useState("");
  const [mockDataError, setMockDataError] = useState<string | null>(null);

  // Layout & Editing Modes
  const [editorMode, setEditorMode] = useState<"code" | "preview">("code");
  const [collapsedTokens, setCollapsedTokens] = useState<Set<string>>(new Set());
  const [previewHtml, setPreviewHtml] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

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
            if (t.css) {
              setCss(t.css);
            }
            if (t.mock_data) {
              setMockDataJson(JSON.stringify(t.mock_data, null, 2));
            }
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
      if (detail) {
        setSelectedDocumentType(detail);

        // Default HTML structure based on Document Type fields
        if (!htmlTouched && !isEditMode) {
          const defaultHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${name || "Template"}</title>
</head>
<body>
  <div class="template-container">
    <h1>${name || "DOCUMENT"}</h1>
    <p>Asociado a: ${detail.name}</p>
    <hr/>
    <!-- Drag and drop tokens here -->
  </div>
</body>
</html>`;
          setHtml(defaultHtml);
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, [documentTypeId, htmlTouched, isEditMode, name]);

  const handleSetEditorMode = (mode: "code" | "preview") => {
    setEditorMode(mode);
  };

  const handleApplyAiProposal = (proposal: TemplateAiProposal) => {
    setHtml(proposal.proposed_html);
    setCss(proposal.proposed_css);
    setHtmlTouched(true);
  };

  useEffect(() => {
    if (editorMode !== "preview") return;

    let cancelled = false;
    const fetchPreview = async () => {
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        let parsedMock: Record<string, unknown> | null = null;
        if (mockDataJson.trim()) {
          try {
            parsedMock = JSON.parse(mockDataJson);
          } catch {
            throw new Error("Invalid Mock Data JSON structure.");
          }
        }
        const resp = await previewHtmlTemplate({
          html,
          css,
          mock_data: parsedMock,
        });
        if (cancelled) return;
        setPreviewHtml(resp.rendered_html);
      } catch (err) {
        if (cancelled) return;
        setPreviewError(err instanceof Error ? err.message : "Failed to load preview.");
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    };

    const delayDebounceFn = setTimeout(() => {
      fetchPreview();
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(delayDebounceFn);
    };
  }, [editorMode, html, css, mockDataJson]);

  const srcDocContent = useMemo(() => {
    const cleanHtml = previewHtml || "";
    const styleTag = `<style>${css || ""}</style>`;
    if (cleanHtml.includes("<head>")) {
      return cleanHtml.replace("<head>", `<head>${styleTag}`);
    } else if (cleanHtml.includes("<HEAD>")) {
      return cleanHtml.replace("<HEAD>", `<HEAD>${styleTag}`);
    } else {
      return `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            ${styleTag}
          </head>
          <body>
            ${cleanHtml}
          </body>
        </html>
      `;
    }
  }, [previewHtml, css]);

  const handleTextareaDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    const token = e.dataTransfer.getData("text/plain");
    if (!token) return;

    const textarea = e.currentTarget;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const nextHtml = text.substring(0, start) + token + text.substring(end);

    setHtml(nextHtml);
    setHtmlTouched(true);
  };

  const handleSubmitForm = async (event: React.MouseEvent<HTMLButtonElement>) => {
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
          css,
          mock_data: parsedMock,
        });
        navigate("/content/templates");
      } else {
        await createHtmlTemplate({
          document_type_id: documentTypeId,
          name,
          html,
          css,
          mock_data: parsedMock,
        });
        navigate("/content/templates");
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

          <span className="material-symbols-outlined text-[18px] text-outline">
            {node.type === "list"
              ? "list"
              : node.type === "object"
              ? (isCollapsed ? "folder" : "folder_open")
              : "description"}
          </span>
          <span className="text-body-sm font-semibold">{node.name}</span>
        </div>

        {!isLeaf && !isCollapsed && node.children && (
          <div className="pl-md border-l border-outline-variant ml-sm space-y-xs">
            {node.children.map(renderTokenNode)}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-secondary">progress_activity</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden -m-lg">
      {/* Top action header bar */}
      <div className="h-14 flex items-center px-lg bg-surface-container-lowest border-b border-outline-variant shrink-0 justify-between">
        <div className="flex items-center gap-md">
          <h1 className="font-headings text-[20px] font-bold tracking-tight text-on-surface">
            {isEditMode ? "Edit HTML Template" : "New HTML Template"}
          </h1>
        </div>
        <div className="flex items-center gap-sm">
          <Link
            to="/content/templates"
            className="rounded border border-outline-variant bg-surface-container px-md py-xs text-xs font-bold text-secondary hover:bg-surface-container-high transition-all"
          >
            Cancel
          </Link>
          <button
            onClick={handleSubmitForm}
            type="button"
            className="rounded bg-primary px-md py-xs text-xs font-bold text-white hover:bg-primary/90 transition-all shadow-sm"
          >
            {isEditMode ? "Save Changes" : "Create Template"}
          </button>
        </div>
      </div>

      {/* Main Workspace (3 Panels) */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden min-h-0 bg-surface-container-low">
        {/* PANEL 1: Left Panel - Metadata & Tokens */}
        <aside className="col-span-3 border-r border-outline-variant bg-surface flex flex-col overflow-hidden h-full">
          <div className="p-md space-y-md border-b border-outline-variant shrink-0 bg-white">
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

          {/* Token Explorer title */}
          <div className="p-md bg-surface-container-low flex items-center justify-between shrink-0">
            <h3 className="font-headings text-sm font-bold text-on-surface flex items-center gap-xs">
              <span className="material-symbols-outlined text-primary text-[20px]">explore</span>
              EXPLORADOR DE TOKENS
            </h3>
          </div>

          {/* Token Explorer Tree (Scrollable) */}
          <div className="flex-1 overflow-y-auto p-md">
            {!selectedDocumentType?.fields?.length ? (
              <div className="text-center py-lg border border-dashed border-outline-variant rounded bg-surface p-sm">
                <p className="text-xs text-secondary">
                  Select a document type above to explore available tokens.
                </p>
              </div>
            ) : (
              <div className="space-y-xs pr-xs">
                {tokenTree.map(renderTokenNode)}
              </div>
            )}
          </div>

          <div className="p-md bg-primary-container/10 border-t border-outline-variant shrink-0">
            <p className="text-[10px] leading-tight text-on-surface-variant italic">
              Tip: Drag tokens directly into the editor to generate dynamic syntax automatically.
            </p>
          </div>
        </aside>

        {/* PANEL 2: Central Panel - Workspace (Canvas & Tabs) */}
        <section className="col-span-6 flex flex-col bg-surface-container-low overflow-hidden h-full">
          <div className="h-12 flex items-center px-md bg-white border-b border-outline-variant shadow-sm z-10 shrink-0">
            <div className="flex bg-surface-container rounded p-[2px]">
              <button
                type="button"
                className={`px-md py-1 font-bold text-xs rounded transition-all flex items-center gap-xs ${
                  editorMode === "code"
                    ? "bg-white text-primary shadow-sm"
                    : "text-secondary hover:text-primary"
                }`}
                onClick={() => handleSetEditorMode("code")}
              >
                <span className="material-symbols-outlined text-[16px]">code</span>
                Source
              </button>
              <button
                type="button"
                className={`px-md py-1 font-bold text-xs rounded transition-all flex items-center gap-xs ${
                  editorMode === "preview"
                    ? "bg-white text-primary shadow-sm"
                    : "text-secondary hover:text-primary"
                }`}
                onClick={() => handleSetEditorMode("preview")}
              >
                <span className="material-symbols-outlined text-[16px]">pageview</span>
                Preview
              </button>
            </div>
            {submitError && (
              <span className="ml-md text-xs text-error font-medium truncate max-w-[250px]">
                {submitError}
              </span>
            )}
          </div>

          {/* Canvas Container (Scrollable) */}
          <div className="flex-1 p-md overflow-y-auto flex flex-col items-center">
            {editorMode === "code" && (
              <div className="w-full max-w-[800px] border border-outline-variant rounded-lg overflow-hidden flex bg-white shadow-md">
                {/* Line numbers dummy sidebar */}
                <div className="w-12 bg-surface-container-low border-r border-outline-variant py-sm text-right pr-sm select-none font-mono text-[11px] text-outline text-height-relaxed">
                  {Array.from({ length: Math.max(25, html.split("\n").length) }).map((_, i) => (
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
                  rows={28}
                  placeholder="<!-- Write your HTML template code directly here. Drag and drop tokens. -->"
                  className="flex-1 w-full bg-slate-900 text-slate-100 p-sm font-mono text-sm leading-relaxed focus:outline-none resize-none min-h-[600px]"
                />
              </div>
            )}



            {editorMode === "preview" && (
              <div className="w-full max-w-[800px] bg-white min-h-[1056px] shadow-lg rounded border border-outline-variant flex flex-col relative overflow-hidden">
                {previewLoading && (
                  <div className="absolute inset-0 bg-white/75 flex items-center justify-center z-25">
                    <span className="material-symbols-outlined animate-spin text-primary text-[32px]">progress_activity</span>
                  </div>
                )}
                {previewError ? (
                  <div className="p-xl flex-1 flex flex-col items-center justify-center text-center gap-md text-error bg-error-container/10">
                    <span className="material-symbols-outlined text-[48px]">error_outline</span>
                    <div>
                      <h3 className="font-bold text-on-surface">Preview Rendering Failed</h3>
                      <p className="text-xs text-secondary mt-xs max-w-md font-mono">{previewError}</p>
                    </div>
                  </div>
                ) : (
                  <iframe
                    title="Jinja Template Preview"
                    className="w-full flex-1 min-h-[600px] border-0"
                    srcDoc={srcDocContent}
                  />
                )}
              </div>
            )}
          </div>
        </section>

        {/* PANEL 3: Right Panel - Styles & Preview Data */}
        <section className="col-span-3 border-l border-outline-variant flex flex-col bg-surface overflow-hidden h-full">
          <div className="h-1/3 overflow-y-auto border-b border-outline-variant p-sm bg-surface">
            <AiProposalPanel
              templateId={isEditMode && id ? id : null}
              html={html}
              css={css}
              mockDataJson={mockDataJson}
              onApply={handleApplyAiProposal}
            />
          </div>

          {/* CSS Styles Section */}
          <div className="h-1/3 flex flex-col border-b border-outline-variant overflow-hidden">
            <div className="p-md bg-surface-container-low flex items-center justify-between shrink-0">
              <div className="flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">css</span>
                <h3 className="font-headings text-sm font-bold text-on-surface">CSS Styles</h3>
              </div>
            </div>
            <div className="flex-1 p-sm bg-white overflow-hidden flex flex-col">
              <textarea
                value={css}
                onChange={(e) => setCss(e.target.value)}
                placeholder={`/* Write custom CSS rules here */\n.title {\n  color: #1a73e8;\n  font-size: 24px;\n}`}
                className="flex-1 w-full rounded border border-outline-variant p-sm font-mono text-xs text-on-surface focus:border-primary focus:outline-none bg-slate-900 text-slate-100 resize-none"
              />
            </div>
          </div>

          {/* Mock Data Section */}
          <div className="h-1/3 flex flex-col overflow-hidden">
            <div className="p-md bg-surface-container-low flex items-center justify-between shrink-0">
              <div className="flex items-center gap-xs">
                <span className="material-symbols-outlined text-primary text-[20px]">data_object</span>
                <h3 className="font-headings text-sm font-bold text-on-surface">Mock Preview Data</h3>
              </div>
              {mockDataError && (
                <span className="text-[10px] text-error font-mono truncate max-w-[120px]" title={mockDataError}>
                  Error
                </span>
              )}
            </div>
            <div className="flex-1 p-sm bg-white overflow-hidden flex flex-col">
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
                placeholder={`{\n  "cliente": {\n    "nombre": "Juan Pérez"\n  }\n}`}
                className={`flex-1 w-full rounded border font-mono text-xs p-sm bg-slate-900 text-slate-100 focus:outline-none resize-none ${
                  mockDataError ? "border-error focus:border-error" : "border-outline-variant focus:border-primary"
                }`}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
`
