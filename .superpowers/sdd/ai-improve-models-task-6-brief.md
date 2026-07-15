# Task 6: Right Panel Tabs and AI Chat Model Selection

Plan file: `docs/superpowers/plans/2026-07-15-ai-improve-models-and-panel.md`

## Global Constraints

- AI requests remain disabled by default.
- Provider credentials stay server-side.
- Generated templates are validated before they can be applied.
- The BFF remains a generic proxy.
- Keep LiteLLM as the provider abstraction.
- The user chooses provider/model in UI from a backend-provided allowlist.
- Persist selected model in `localStorage`.
- AI Chat is a simple single-instruction proposal flow in this phase.
- Ollama uses an existing external/local instance through `OLLAMA_API_BASE`; do not add an Ollama Docker Compose service.
- Out of scope: multi-turn memory, streaming, UI-managed secrets, backend user preference persistence.

## Execution Adjustment

Do not attempt `git add` or `git commit`. This environment cannot create `.git/index.lock`. Report changed files instead.

## Files

- Modify: `frontend/src/pages/content/components/AiProposalPanel.tsx`
- Modify: `frontend/src/pages/content/HtmlTemplateCreatePage.tsx`

## Interfaces

- Consumes: `getAiModels()`, `createTemplateAiProposal(..., { model })`.
- Produces: tabbed panel props that own AI chat, CSS editor, mock data editor, and model localStorage selection.

## Current Structure

`HtmlTemplateCreatePage.tsx` currently renders the right panel as three vertical blocks:

- `AiProposalPanel`
- CSS Styles section
- Mock Data section

`AiProposalPanel.tsx` currently owns only AI instruction/proposal/history.

## Required Behavior

1. The right panel should render one full-height `AiProposalPanel`.
2. `AiProposalPanel` must render two top-level tabs:
   - `AI Chat`
   - `Settings`
3. `AI Chat` tab contains:
   - model selector loaded from `getAiModels()`;
   - selected model persisted in `localStorage` key `docmanagement.aiImprove.selectedModel`;
   - existing instruction box;
   - generate action;
   - proposal summary/status/errors/apply action;
   - proposal history.
4. `Settings` tab contains:
   - `CSS Style` textarea bound to parent `css`;
   - `Mock Preview Data` textarea bound to parent `mockDataJson`;
   - inline mock JSON error display.
5. Generate must:
   - block if `mockDataError` exists;
   - block if no model is selected;
   - include `model: selectedModel || null` in `createTemplateAiProposal`.
6. Existing apply behavior must still update HTML and CSS through `onApply`.
7. When the stored model is stale, ignore it and choose backend `default_model` if allowed, otherwise the first model.

## Component Prop Contract

Use this prop shape:

```ts
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
```

## Parent Usage

In `HtmlTemplateCreatePage.tsx`, replace the old three-section right panel with one `AiProposalPanel`:

```tsx
<section className="col-span-3 border-l border-outline-variant flex flex-col bg-surface overflow-hidden h-full">
  <AiProposalPanel
    templateId={isEditMode && id ? id : null}
    html={html}
    css={css}
    mockDataJson={mockDataJson}
    mockDataError={mockDataError}
    onCssChange={setCss}
    onMockDataJsonChange={(value) => {
      setMockDataJson(value);
      try {
        if (value.trim()) {
          JSON.parse(value);
          setMockDataError(null);
        } else {
          setMockDataError(null);
        }
      } catch (err) {
        setMockDataError(err instanceof Error ? err.message : "Invalid JSON syntax");
      }
    }}
    onApply={handleApplyAiProposal}
  />
</section>
```

## Verification

Run from `frontend/`:

```powershell
rtk npm run build
```

## Report

Write full report to `.superpowers/sdd/ai-improve-models-task-6-report.md` and return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created: none, because `.git` is read-only
- One-line test summary
- Concerns, if any
- Report file path
