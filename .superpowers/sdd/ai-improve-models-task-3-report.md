# Task 3: Selected Model Validation in Proposal Creation

## Status

DONE_WITH_CONCERNS

## Scope

Implemented selected-model validation for HTML template AI proposal creation.

## Changes

- Added optional `model` to `HtmlTemplateAiProposalCreate`.
- Resolved the requested model through `resolve_ai_model` before creating the AI agent.
- Returned HTTP 400 with the catalog error when the requested model is not allowlisted or model configuration is invalid.
- Passed the resolved model ID to `TemplateAiAgent`.
- Checked provider configuration with `is_provider_configured` before invoking `create_proposal`.
- Added `TemplateAiAgent.provider_configuration_failed()` returning a persisted failed result with `Provider is not configured.`.
- Preserved existing proposal persistence for valid, invalid, disabled, and provider-failure results.
- Added regression coverage for selected-model forwarding, allowlist rejection, and unconfigured-provider persistence.
- Updated the existing successful proposal test to explicitly configure its allowlisted provider.

## Verification

Command run from `backend/`:

```text
.venv/Scripts/python.exe -m pytest tests/test_template_ai_proposals.py tests/test_ai_model_catalog.py -q
```

Result: 29 passed.

## Concerns

- Pytest reports three pre-existing warnings: Starlette/httpx deprecation, `datetime.utcnow()` deprecation, and inability to write `.pytest_cache` due to filesystem permissions. None failed the requested tests or is introduced by this task.
- No commit was created because `.git` is read-only, per task instructions.

## Changed Files

- `backend/app/schemas/template_ai_proposal.py`
- `backend/app/api/template_ai_proposals.py`
- `backend/app/services/template_ai_agent.py`
- `backend/tests/test_template_ai_proposals.py`
- `.superpowers/sdd/ai-improve-models-task-3-report.md`
