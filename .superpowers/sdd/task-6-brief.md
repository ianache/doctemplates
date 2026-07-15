## Task 6: AI Proposal Panel UI

**Files:**

- Create: `frontend/src/pages/content/components/AiProposalPanel.tsx`
- Modify: `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`

**Interfaces:**

- `AiProposalPanel` props:
  - `templateId: string | null`
  - `html: string`
  - `css: string`
  - `mockDataJson: string`
  - `onApply(proposal: TemplateAiProposal): void`
- Consumes frontend API helpers from Task 5.

- [ ] **Step 1: Create panel component**

Create `frontend/src/pages/content/components/AiProposalPanel.tsx`:

```tsx
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
```

- [ ] **Step 2: Mount panel in editor**

Modify `frontend/src/pages/content/HtmlTemplateCreatePage.tsx` imports:

```tsx
import AiProposalPanel from "./components/AiProposalPanel";
import type { TemplateAiProposal } from "../../lib/content";
```

Add handler inside `HtmlTemplateCreatePage`:

```tsx
const handleApplyAiProposal = (proposal: TemplateAiProposal) => {
  setHtml(proposal.proposed_html);
  setCss(proposal.proposed_css);
  setHtmlTouched(true);
};
```

Insert the panel at the top of the right panel before the CSS section. Change the CSS and mock-data panel heights from `h-1/2` to flexible thirds:

```tsx
<div className="h-1/3 overflow-y-auto border-b border-outline-variant p-sm bg-surface">
  <AiProposalPanel
    templateId={isEditMode && id ? id : null}
    html={html}
    css={css}
    mockDataJson={mockDataJson}
    onApply={handleApplyAiProposal}
  />
</div>
```

Then update the CSS and mock-data wrappers to:

```tsx
<div className="h-1/3 flex flex-col border-b border-outline-variant overflow-hidden">
```

and:

```tsx
<div className="h-1/3 flex flex-col overflow-hidden">
```

- [ ] **Step 3: Run frontend build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
rtk git add frontend/src/pages/content/components/AiProposalPanel.tsx frontend/src/pages/content/HtmlTemplateCreatePage.tsx
rtk git commit -m "feat: add ai proposal panel"
```

