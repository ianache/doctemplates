# Task 5: Frontend API Client for Model Catalog

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

- Modify: `frontend/src/lib/content.ts`

## Interfaces

- Produces: `AiModelOption`, `AiModelCatalog`, `getAiModels()`, and `TemplateAiProposalCreatePayload.model`.
- Consumes: `GET /api/content/ai-models` and existing `createTemplateAiProposal`.

## Steps

1. Add TypeScript interfaces:
   - `AiModelOption`
   - `AiModelCatalog`
2. Add `getAiModels(): Promise<AiModelCatalog>` calling `/api/content/ai-models`.
3. Extend `TemplateAiProposalCreatePayload` with `model?: string | null`.
4. Run frontend build from `frontend/`:
   - `rtk npm run build`

## Required Code

```ts
export interface AiModelOption {
  id: string;
  provider: string;
  label: string;
  requires: string;
}

export interface AiModelCatalog {
  enabled: boolean;
  default_model: string;
  models: AiModelOption[];
}

export async function getAiModels(): Promise<AiModelCatalog> {
  return jsonOrError(await apiFetch("/api/content/ai-models"));
}
```

```ts
export interface TemplateAiProposalCreatePayload {
  instruction: string;
  current_html: string;
  current_css?: string | null;
  mock_data?: Record<string, unknown> | null;
  model?: string | null;
}
```

## Report

Write full report to `.superpowers/sdd/ai-improve-models-task-5-report.md` and return only:

- Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created: none, because `.git` is read-only
- One-line test summary
- Concerns, if any
- Report file path
