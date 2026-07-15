# AI Improve Models and Right Panel Design

Date: 2026-07-15

## Goal

Improve the HTML template authoring workflow by letting AI Improve use allowed Gemini, Groq, and Ollama models, and by reorganizing the right panel into a more fluid two-tab experience:

- `AI Chat` for requesting and applying AI-generated template proposals.
- `Settings` for editing `CSS Style` and `Mock Preview Data`.

The feature must preserve the existing safety posture: AI requests remain disabled by default, provider credentials stay server-side, generated templates are validated before they can be applied, and the BFF remains a generic proxy.

## Current Context

The current backend uses LiteLLM through `TemplateAiAgent` with one global `AI_PROVIDER_MODEL`. The template proposal endpoint creates a proposal synchronously, validates the generated HTML/CSS, stores the proposal, and returns whether it can be applied. The database model already stores `provider` and `model`.

The current frontend editor has three right-panel blocks stacked vertically:

- AI Improve proposal panel.
- CSS editor.
- Mock data JSON editor.

This makes the right side cramped and gives the AI workflow a form-like feel instead of a chat-like assistant workflow.

## Decisions

- Keep LiteLLM as the provider abstraction.
- Add backend-owned allowed model configuration.
- Let the user choose provider/model in the UI from the backend-provided allowlist.
- Persist the selected model in `localStorage`.
- Keep AI Chat as a simple single-instruction proposal flow for this phase.
- Connect to existing Ollama instances by URL; do not add an Ollama Docker Compose service.
- Do not add multi-turn AI memory, streaming, UI-managed secrets, or backend user preference persistence in this phase.

## Architecture

Add a backend model catalog that is derived from environment variables. The backend exposes the catalog to authenticated frontend callers and validates every requested AI model against it before calling LiteLLM.

New effective environment variables:

```env
AI_REQUESTS_ENABLED=false
AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1
GEMINI_API_KEY=
GROQ_API_KEY=
OLLAMA_API_BASE=http://host.docker.internal:11434
```

`AI_PROVIDER_MODEL` may remain as a temporary fallback for compatibility, but `AI_DEFAULT_MODEL` becomes the preferred setting.

If `AI_ALLOWED_MODELS` is empty, the backend should expose an empty model list and reject proposal generation with a clear configuration error. If `AI_DEFAULT_MODEL` is not present in `AI_ALLOWED_MODELS`, startup/config parsing should treat that as a configuration error rather than silently choosing a different model.

Provider conventions follow LiteLLM model IDs:

- Gemini models use `gemini/...` and require `GEMINI_API_KEY`.
- Groq models use `groq/...` and require `GROQ_API_KEY`.
- Ollama models use `ollama/...` and require `OLLAMA_API_BASE`.

Docker Compose must pass the new provider variables into the backend container. It should not start Ollama itself.

## Backend API

Add an authenticated endpoint:

```http
GET /api/content/ai-models
```

Response shape:

```json
{
  "enabled": true,
  "default_model": "gemini/gemini-2.0-flash",
  "models": [
    {
      "id": "gemini/gemini-2.0-flash",
      "provider": "gemini",
      "label": "Gemini 2.0 Flash",
      "requires": "GEMINI_API_KEY"
    },
    {
      "id": "groq/llama-3.1-8b-instant",
      "provider": "groq",
      "label": "Groq Llama 3.1 8B Instant",
      "requires": "GROQ_API_KEY"
    },
    {
      "id": "ollama/llama3.1",
      "provider": "ollama",
      "label": "Ollama Llama 3.1",
      "requires": "OLLAMA_API_BASE"
    }
  ]
}
```

Extend the existing proposal request:

```http
POST /api/content/templates/{template_id}/ai-proposals
```

Additional optional field:

```json
{
  "model": "gemini/gemini-2.0-flash"
}
```

Rules:

- If `model` is omitted, use `AI_DEFAULT_MODEL`.
- If `model` is not in the allowlist, reject the request with `400`.
- If AI is disabled, return the existing failed proposal response pattern with a clear validation error.
- If the selected provider is missing required configuration, return a failed proposal response with `Provider is not configured.`
- Store the resolved provider/model in the existing proposal row.

## Frontend UI

The template editor keeps the left token panel and center source/preview workspace. The right panel changes to two tabs.

### AI Chat Tab

The `AI Chat` tab contains:

- A compact selected-model indicator or selector.
- A chat-style instruction input.
- A `Generate` action.
- Proposal responses displayed like assistant messages.
- Summary, validation errors, model metadata, and `Apply` action for valid proposals.
- Existing proposal history rendered as prior assistant responses rather than a separate technical list.

When the user applies a proposal, the page updates the HTML and CSS state using the existing `onApply` flow.

### Settings Tab

The `Settings` tab contains two subpanels:

- `CSS Style`: the existing CSS editor with more usable vertical space.
- `Mock Preview Data`: the existing JSON editor with inline validation.

`Mock Preview Data` validation remains local and prevents AI requests when JSON is invalid.

### Model Selection Persistence

The frontend loads `GET /api/content/ai-models` when the panel mounts. It chooses the active model in this order:

1. Valid `localStorage` selection.
2. Backend `default_model`.
3. First model in the backend list.

When the user selects a new model, the frontend stores it in `localStorage`. If a stored model is no longer allowed, it is ignored.

## Error Handling

- AI disabled: show an actionable message explaining that `AI_REQUESTS_ENABLED=true` and provider configuration are required.
- Model not allowed: show a clear frontend error and do not retry automatically.
- Provider not configured: show a concise message naming that backend provider configuration is missing, without exposing secrets.
- Provider timeout or invalid JSON: keep proposal status `failed`, display validation errors, and disable `Apply`.
- Mock data JSON invalid: keep inline error and block `Generate`.

## Testing

Backend tests:

- Parse and expose allowed models from configuration.
- Apply default model fallback when request omits model.
- Reject non-allowlisted models.
- Detect missing provider configuration for Gemini, Groq, and Ollama.
- Verify `TemplateAiAgent` receives the selected model when LiteLLM is mocked.
- Verify `GET /api/content/ai-models` response shape.

Frontend verification:

- Build passes.
- Selector chooses backend default when no valid localStorage value exists.
- Selector ignores stale localStorage model values.
- Generated proposal requests include the selected model.
- Invalid mock JSON blocks generation.

Manual UAT:

- Configure Gemini with `AI_REQUESTS_ENABLED=true`, `AI_DEFAULT_MODEL=gemini/gemini-2.0-flash`, `GEMINI_API_KEY`, and verify a proposal can be generated and applied.
- Configure Groq with `GROQ_API_KEY` and verify a proposal can be generated.
- Configure Ollama with a running local instance and `OLLAMA_API_BASE`, then verify a proposal can be generated.

## Out Of Scope

- Multi-turn chat memory.
- Streaming responses.
- Storing provider API keys through the UI.
- A Docker Compose Ollama service.
- Persisting user model preferences in backend storage.
- Reworking the left token panel or center source/preview workspace beyond what is needed for the right panel integration.

## Acceptance Criteria

- The backend exposes enabled state, default model, and allowed model options.
- AI proposal creation accepts and validates a selected model.
- Gemini, Groq, and Ollama configuration paths are documented and passed through Docker Compose.
- The right panel has `AI Chat` and `Settings` tabs.
- `Settings` contains `CSS Style` and `Mock Preview Data`.
- The selected model persists in `localStorage`.
- Invalid or unavailable models fail with clear user-facing errors.
- Existing template proposal validation and apply behavior remain intact.
