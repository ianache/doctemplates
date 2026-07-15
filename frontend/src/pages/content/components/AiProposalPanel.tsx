import { useEffect, useState } from "react";

import {
  createTemplateAiProposal,
  getAiModels,
  listTemplateAiProposals,
  markTemplateAiProposalApplied,
  type AiModelCatalog,
  type TemplateAiProposal,
} from "../../../lib/content";

interface AiProposalPanelProps {
  templateId: string | null;
  html: string;
  css: string;
  mockDataJson: string;
  mockDataError: string | null;
  onCssChange: (value: string) => void;
  onMockDataJsonChange: (value: string) => void;
  onApply: (proposal: TemplateAiProposal) => void;
}

const selectedModelStorageKey = "docmanagement.aiImprove.selectedModel";

function parseMockData(mockDataJson: string): Record<string, unknown> | null {
  if (!mockDataJson.trim()) return null;
  const parsed = JSON.parse(mockDataJson);
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("Mock data must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}

function formatAiError(error: unknown): string {
  const message = error instanceof Error ? error.message : "AI proposal failed.";
  if (message.includes("AI requests are disabled")) {
    return "AI Improve is disabled in this environment. Set AI_REQUESTS_ENABLED=true and configure a provider API key on the backend, then restart the service.";
  }
  return message;
}

export default function AiProposalPanel({
  templateId,
  html,
  css,
  mockDataJson,
  mockDataError,
  onCssChange,
  onMockDataJsonChange,
  onApply,
}: AiProposalPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [proposals, setProposals] = useState<TemplateAiProposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<TemplateAiProposal | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "html" | "css">("summary");
  const [panelTab, setPanelTab] = useState<"chat" | "settings">("chat");
  const [modelCatalog, setModelCatalog] = useState<AiModelCatalog | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelError, setModelError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const aiEnabled = modelCatalog?.enabled === true;

  useEffect(() => {
    setProposals([]);
    setActiveProposal(null);
    setError(null);
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

  useEffect(() => {
    let cancelled = false;
    getAiModels()
      .then((catalog) => {
        if (cancelled) return;
        setModelCatalog(catalog);
        const storedModel = localStorage.getItem(selectedModelStorageKey);
        const storedModelIsAllowed = catalog.models.some((model) => model.id === storedModel);
        const defaultModelIsAllowed = catalog.models.some((model) => model.id === catalog.default_model);
        const nextModel = storedModelIsAllowed
          ? storedModel!
          : defaultModelIsAllowed
            ? catalog.default_model
            : catalog.models[0]?.id ?? "";
        setSelectedModel(nextModel);
        if (nextModel) localStorage.setItem(selectedModelStorageKey, nextModel);
      })
      .catch((err) => {
        if (!cancelled) setModelError(err instanceof Error ? err.message : "We couldn't load AI models.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectModel = (model: string) => {
    setSelectedModel(model);
    localStorage.setItem(selectedModelStorageKey, model);
  };

  const requestProposal = async () => {
    if (!templateId || !instruction.trim()) return;
    if (!aiEnabled) {
      setError("AI Improve is disabled in this environment.");
      return;
    }
    if (mockDataError) {
      setError("Fix the mock preview data JSON before generating an AI proposal.");
      return;
    }
    if (!selectedModel) {
      setError("Select an AI model before generating a proposal.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const proposal = await createTemplateAiProposal(templateId, {
        instruction,
        current_html: html,
        current_css: css,
        mock_data: parseMockData(mockDataJson),
        model: selectedModel || null,
      });
      setProposals((current) => [proposal, ...current]);
      setActiveProposal(proposal);
      setActiveTab("summary");
    } catch (err) {
      setError(formatAiError(err));
    } finally {
      setLoading(false);
    }
  };

  const applyProposal = async () => {
    if (!templateId || !activeProposal || !activeProposal.is_applyable) return;
    setApplying(true);
    setError(null);
    try {
      const applied = await markTemplateAiProposalApplied(templateId, activeProposal.id);
      onApply(applied);
      setProposals((current) => current.map((proposal) => (proposal.id === applied.id ? applied : proposal)));
      setActiveProposal(applied);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Applying the AI proposal failed.");
    } finally {
      setApplying(false);
    }
  };

  return (
    <section className="flex h-full min-h-0 flex-col bg-white">
      <div className="flex border-b border-outline-variant bg-surface-container-low px-sm pt-sm">
        <button
          type="button"
          onClick={() => setPanelTab("chat")}
          className={`border-b-2 px-sm py-xs text-xs font-bold ${panelTab === "chat" ? "border-primary text-primary" : "border-transparent text-secondary"}`}
        >
          AI Chat
        </button>
        <button
          type="button"
          onClick={() => setPanelTab("settings")}
          className={`border-b-2 px-sm py-xs text-xs font-bold ${panelTab === "settings" ? "border-primary text-primary" : "border-transparent text-secondary"}`}
        >
          Settings
        </button>
      </div>

      {panelTab === "settings" ? (
        <div className="flex min-h-0 flex-1 flex-col gap-md overflow-y-auto p-sm">
          <label className="flex min-h-48 flex-1 flex-col gap-xs text-[11px] font-bold uppercase text-secondary">
            CSS Style
            <textarea
              value={css}
              onChange={(event) => onCssChange(event.target.value)}
              placeholder="/* Write custom CSS rules here */"
              className="min-h-40 flex-1 resize-none rounded border border-outline-variant bg-slate-900 p-sm font-mono text-xs normal-case text-slate-100 focus:border-primary focus:outline-none"
            />
          </label>
          <label className="flex min-h-48 flex-1 flex-col gap-xs text-[11px] font-bold uppercase text-secondary">
            Mock Preview Data
            <textarea
              value={mockDataJson}
              onChange={(event) => onMockDataJsonChange(event.target.value)}
              placeholder={'{\n  "cliente": {\n    "nombre": "Juan Perez"\n  }\n}'}
              className={`min-h-40 flex-1 resize-none rounded border bg-slate-900 p-sm font-mono text-xs normal-case text-slate-100 focus:outline-none ${mockDataError ? "border-error focus:border-error" : "border-outline-variant focus:border-primary"}`}
            />
            {mockDataError ? <span className="normal-case text-xs font-normal text-error">{mockDataError}</span> : null}
          </label>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-sm overflow-y-auto p-sm">
          <div className="flex items-center gap-xs">
            <span className="material-symbols-outlined text-primary text-[20px]">auto_awesome</span>
            <h3 className="font-headings text-sm font-bold text-on-surface">AI Improve</h3>
          </div>

          {!templateId ? <p className="text-xs text-secondary">AI improvements are available after this template is created.</p> : null}

          <label className="text-[11px] font-bold uppercase text-secondary">
            Model
            <select
              value={selectedModel}
              onChange={(event) => selectModel(event.target.value)}
              disabled={!aiEnabled || modelCatalog.models.length === 0}
              className="mt-xs w-full rounded border border-outline-variant bg-white p-sm text-xs normal-case text-on-surface focus:border-primary focus:outline-none disabled:opacity-50"
            >
              <option value="">{modelCatalog ? "No AI models available" : "Loading AI models..."}</option>
              {modelCatalog?.models.map((model) => <option key={model.id} value={model.id}>{model.label}</option>)}
            </select>
          </label>
          {modelError ? <p className="text-xs text-error">{modelError}</p> : null}
          {modelCatalog && !modelCatalog.enabled ? <p className="text-xs text-secondary">AI Improve is disabled in this environment.</p> : null}

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
            disabled={loading || !templateId || !aiEnabled || !instruction.trim() || !selectedModel || Boolean(mockDataError)}
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
            disabled={applying || !activeProposal.is_applyable}
            className="rounded border border-primary px-md py-xs text-xs font-bold text-primary disabled:border-outline-variant disabled:text-secondary"
          >
            {applying ? "Applying..." : "Apply proposal"}
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
        </div>
      )}
    </section>
  );
}
