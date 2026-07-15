## Task 5: Frontend API Client

**Files:**

- Modify: `frontend/src/lib/content.ts`

**Interfaces:**

- Produces `TemplateAiProposal` interface.
- Produces `createTemplateAiProposal(templateId, payload)`.
- Produces `listTemplateAiProposals(templateId)`.
- Produces `markTemplateAiProposalApplied(templateId, proposalId)`.
- Later UI task imports these functions.

- [ ] **Step 1: Add TypeScript interfaces and client functions**

Modify `frontend/src/lib/content.ts`:

```ts
export interface TemplateAiProposal {
  id: string;
  template_id: string;
  created_by_id: string;
  instruction: string;
  input_html: string;
  input_css: string;
  proposed_html: string;
  proposed_css: string;
  summary: string;
  provider: string;
  model: string;
  status: "valid" | "invalid" | "failed";
  validation_errors: string[];
  is_applyable: boolean;
  applied_at: string | null;
  created_at: string;
}

export interface TemplateAiProposalCreatePayload {
  instruction: string;
  current_html: string;
  current_css?: string | null;
  mock_data?: Record<string, unknown> | null;
}

export async function createTemplateAiProposal(
  templateId: string,
  payload: TemplateAiProposalCreatePayload,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function listTemplateAiProposals(templateId: string): Promise<TemplateAiProposal[]> {
  return jsonOrError(await apiFetch(`/api/content/templates/${templateId}/ai-proposals`));
}

export async function markTemplateAiProposalApplied(
  templateId: string,
  proposalId: string,
): Promise<TemplateAiProposal> {
  return jsonOrError(
    await apiFetch(`/api/content/templates/${templateId}/ai-proposals/${proposalId}/apply`, {
      method: "POST",
    }),
  );
}
```

- [ ] **Step 2: Run frontend type build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 3: Commit**

Run:

```bash
rtk git add frontend/src/lib/content.ts
rtk git commit -m "feat: add template ai proposal client"
```

