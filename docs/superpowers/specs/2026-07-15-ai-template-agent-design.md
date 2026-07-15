# AI Template Agent Design

Date: 2026-07-15
Phase: 16 - AI agent for page templating
Status: Design approved for user review

## Goal

Add an AI-assisted improvement workflow for existing HTML content templates. The first version helps template editors improve layout, print styling, and visual structure for an existing template while preserving its current Jinja tokens and meaning.

The feature is proposal-first: the AI never mutates the template directly. It returns a reviewable HTML/CSS proposal, strict backend validation decides whether the proposal can be applied, and the user must explicitly apply and then save the template.

## Non-Goals

- Generating a brand-new template from an empty prompt.
- Chat-style multi-turn template editing.
- Adding admin or auditor roles.
- Automatically saving AI output to the template.
- Moving AI work into asynchronous jobs in the first version.
- Allowing AI to add, remove, or reinterpret business tokens.

## Recommended Approach

Use a proposal-first backend agent.

The backend owns this feature because it already owns template persistence, document type schemas, Jinja validation, preview rendering, PDF rendering, and authentication. The frontend remains a review and apply surface. The BFF remains a session-aware proxy and should not contain custom AI orchestration.

The implementation should keep the AI call synchronous for Phase 16, but isolate it behind a service boundary so a later phase can move proposal creation to an async job without changing the proposal table or editor contract.

## Architecture

Add a backend proposal layer around existing HTML template editing.

New backend pieces:

- `HtmlTemplateAiProposal` SQLAlchemy model and Alembic migration.
- Pydantic schemas for proposal create, list, detail, validation, and apply responses.
- Routes under the existing content-template API namespace:
  - `POST /api/content/templates/{template_id}/ai-proposals`
  - `GET /api/content/templates/{template_id}/ai-proposals`
  - `POST /api/content/templates/{template_id}/ai-proposals/{proposal_id}/apply`
- `TemplateAiAgent` service that builds prompts, calls LiteLLM, parses output, validates output, and persists proposals.
- Backend config fields:
  - `ai_requests_enabled`
  - `ai_provider_model`
  - `ai_request_timeout_seconds`
  - `ai_max_input_chars`
  - `ai_max_output_tokens`

Provider API keys should use LiteLLM-supported environment variables such as `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Do not store provider secrets in the database.

Frontend additions:

- API helpers in the content client module.
- An AI improvement panel in the existing HTML template edit workspace.
- Proposal history and review UI.
- Apply behavior that updates local editor fields but does not save the template automatically.

## Data Model

`HtmlTemplateAiProposal` should be linked to `html_templates` and users.

Required fields:

- `id`
- `template_id`
- `created_by_id`
- `instruction`
- `input_html`
- `input_css`
- `proposed_html`
- `proposed_css`
- `summary`
- `provider`
- `model`
- `status`
- `validation_errors`
- `is_applyable`
- `applied_at`
- `created_at`

Recommended status values:

- `valid`
- `invalid`
- `failed`

Persist full proposal history, including invalid proposals, so template editors can understand what was suggested, why it failed, and which proposals were applied. In Phase 16, history is visible to users who can edit the template. Admin and auditor visibility is deferred until explicit roles exist.

## Data Flow

1. User opens an existing HTML template edit page.
2. Frontend loads template detail through the current content API.
3. User opens the AI improvement panel and enters an instruction such as "make this page look more formal and print-friendly".
4. Frontend calls `POST /api/content/templates/{template_id}/ai-proposals` with the instruction and the current unsaved `html` and `css` values.
5. Backend loads the persisted template and document type fields.
6. Backend sends LiteLLM a constrained JSON-only prompt containing:
   - user instruction
   - current HTML
   - current CSS
   - document type field names and types
   - existing extracted Jinja tokens and statements
   - output contract
7. Backend expects JSON with `html`, `css`, and `summary`.
8. Backend validates the result strictly.
9. Backend persists the full proposal and validation result.
10. Frontend shows the proposal and history.
11. Valid proposals show an Apply action. Invalid proposals show validation errors and cannot be applied.
12. On Apply, frontend replaces local editor `html` and `css` values and calls the apply endpoint to mark the proposal applied.
13. User uses the existing Save Changes action to persist the edited template.

## Validation and Safety

A proposal is applyable only if all gates pass:

- Model response is valid JSON with `html`, `css`, and `summary`.
- Generated HTML parses as Jinja using the existing sandboxed environment.
- Generated tokens are valid for the selected document type.
- Every existing Jinja expression and statement from the current input HTML is still present in the generated HTML.
- Preview rendering succeeds using current editor mock data when supplied, otherwise the stored template mock data.
- HTML does not include `<script>` tags.
- HTML does not include inline event handler attributes such as `onclick`.
- HTML and CSS do not reference external network assets or unsafe URLs.
- Request input size is below the synchronous feature limit.

Invalid proposals are still persisted with validation errors, but the API must set `is_applyable=false` and the UI must not render an Apply action for them.

## Prompt Contract

The service prompt should instruct the model to:

- Improve layout, print styling, typography, spacing, and visual hierarchy.
- Preserve all existing Jinja expressions and statements.
- Use only tokens already present in the current template.
- Avoid adding JavaScript.
- Avoid external fonts, images, scripts, and remote URLs.
- Return only JSON.

Expected model response:

```json
{
  "html": "<!DOCTYPE html>...",
  "css": "body { ... }",
  "summary": "Improved spacing, headings, and print-friendly table styling."
}
```

The backend must treat the prompt contract as untrusted input. It must parse, validate, and sanitize the response before marking a proposal applyable.

## Frontend Experience

Enable the AI panel only for edit mode because proposals attach to an existing persisted template.

Panel states:

- New-template disabled state explaining that AI improvements are available after the template is created.
- Instruction input.
- Loading state while proposal creation is in progress.
- Valid proposal state with summary and Apply button.
- Invalid proposal state with validation errors and no Apply button.
- Proposal history list, newest first.

Review UI should keep the first version simple:

- Tabs for `Summary`, `HTML`, and `CSS`.
- Read-only current vs proposed blocks or side-by-side textareas.
- No new diff dependency unless one already exists in the project.

Apply behavior:

- Replaces local `html` and `css` editor state.
- Marks the proposal applied server-side.
- Does not call the existing template save endpoint.
- Leaves final persistence to the existing Save Changes button.

## Error Handling

Backend should return clear errors for:

- AI requests disabled.
- Missing provider configuration.
- Template not found.
- Template too large for synchronous AI improvement.
- LiteLLM timeout or provider failure.
- Invalid model output.
- Validation failures.

Provider failures should persist a `failed` proposal record when enough request context exists. Validation failures should persist an `invalid` proposal record with user-readable validation errors.

Frontend should:

- Keep the user's current editor content unchanged on request failure.
- Show provider and validation errors near the AI panel.
- Allow retry with a revised instruction.
- Never offer Apply for failed or invalid proposals.

## Testing

Backend tests:

- Successful proposal creation with LiteLLM mocked.
- Invalid JSON/model response is persisted as invalid or failed and is not applyable.
- Unknown tokens fail validation.
- Removed existing tokens or Jinja statements fail validation.
- Unsafe HTML/CSS fails validation.
- Preview-render failure blocks applyability.
- Proposal history lists only proposals for the selected template.
- Apply endpoint marks the proposal applied without mutating the template.

Frontend verification:

- AI panel is disabled for new templates.
- Edit-mode proposal request uses current unsaved HTML/CSS.
- Valid proposal can be applied into local editor fields.
- Invalid proposal displays validation errors and no Apply action.
- History renders newest proposals.

Manual UAT:

1. Edit an existing template.
2. Ask AI to improve print-friendly layout.
3. Confirm a valid proposal appears.
4. Apply the proposal.
5. Save the template.
6. Preview or generate a document using the template.

## Future Extensions

- New-template generation from prompt.
- Async proposal jobs for slow providers.
- Multi-turn assistant panel.
- Admin and auditor proposal visibility.
- Version comparison between applied proposals and saved template revisions.
- Provider selection per request.

