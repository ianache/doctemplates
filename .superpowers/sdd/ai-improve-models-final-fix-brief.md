# Final Review Fix Brief: AI Improve Models and Panel

## Findings To Fix

1. High security: Generated CSS can inject `</style><script>...` into preview because CSS is inserted into a `<style>` element and preview iframe is unsandboxed.
2. Medium UX: Disabled AI currently can be reported as provider unconfigured because provider readiness is checked before `TemplateAiAgent` disabled guard. Frontend also ignores `catalog.enabled`.
3. Medium data: Proposal `provider` is persisted as `litellm`, not the selected provider.
4. Medium config: Invalid model catalog config can raise raw `ValueError` from `GET /api/content/ai-models`.
5. Low persistence abuse: Disabled/unconfigured requests can persist arbitrarily large input rows because input size is checked inside `create_proposal`, but provider/disabled short paths bypass that.

## Constraints

- Do not run `git add` or `git commit`.
- Keep BFF generic.
- Keep LiteLLM abstraction.
- Do not add multi-turn memory, streaming, or UI-managed secrets.
- Run focused backend tests and frontend build.

## Expected Fix Shape

- Add CSS safety validation in `TemplateAiAgent._validate`, at minimum reject `</style` in generated CSS and unsafe script-like CSS that can break out of the style context.
- Sandbox the preview iframe in `HtmlTemplateCreatePage.tsx` for defense in depth.
- Ensure disabled AI returns `AI requests are disabled.` before provider configuration failure.
- Pass/store selected provider from catalog result, not constant `litellm`.
- Make `GET /api/content/ai-models` return a controlled 500 or 400-style HTTPException for invalid catalog config rather than raw exception.
- Ensure proposal endpoint applies the max input size guard before persisting disabled/provider-failed proposal rows.
- Add/adjust tests covering these behaviors.

## Verification

From `backend/`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_ai_model_catalog.py tests/test_template_ai_proposals.py -q
```

From `frontend/`:

```powershell
rtk npm run build
```

Write report to `.superpowers/sdd/ai-improve-models-final-fix-report.md`.
