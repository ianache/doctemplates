## Task 7: End-to-End Verification and Documentation

**Files:**

- Modify: `.env.example`
- Modify: `.planning/ROADMAP.md`
- Create or modify: `.planning/phases/16-ai-agent-for-page-templating/16-01-PLAN.md`

**Interfaces:**

- Documents required environment variables and verification commands.
- Marks Phase 16 planning artifacts consistently with GSD conventions.

- [ ] **Step 1: Document AI environment configuration**

Add to `.env.example`:

```dotenv
AI_REQUESTS_ENABLED=false
AI_PROVIDER_MODEL=gpt-4o-mini
AI_REQUEST_TIMEOUT_SECONDS=30
AI_MAX_INPUT_CHARS=20000
AI_MAX_OUTPUT_TOKENS=2000
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
```

- [ ] **Step 2: Run backend proposal tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_template_ai_proposals.py -v"
```

Expected: PASS.

- [ ] **Step 3: Run existing template regression tests**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location backend; uv run pytest tests/test_content_templates.py tests/test_template_ast_validation.py tests/test_pdf_generator.py -v"
```

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run:

```bash
rtk proxy powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 5: Manual UAT**

Run the app with the existing local development flow, then verify:

```text
1. Open an existing HTML template in edit mode.
2. Confirm AI Improve panel is visible.
3. Enter: Make this template more formal and print-friendly.
4. Confirm a valid proposal appears.
5. Confirm invalid validation errors block Apply when the mocked/provider output removes a token.
6. Apply a valid proposal.
7. Confirm local HTML and CSS fields update.
8. Click Save Changes.
9. Preview or generate a document using the saved template.
```

- [ ] **Step 6: Commit documentation and planning updates**

Run:

```bash
rtk git add .env.example .planning/ROADMAP.md .planning/phases/16-ai-agent-for-page-templating/16-01-PLAN.md
rtk git commit -m "docs: document ai template agent verification"
```

