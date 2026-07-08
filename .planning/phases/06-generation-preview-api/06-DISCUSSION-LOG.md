# Phase 6: Generation & Preview API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-08
**Phase:** 06-generation-preview-api
**Areas discussed:** PDF Rendering & Templating Engines, Data Validation & Type Constraints, Issuance Persistence & PDF Storage, Preview API & Mock Data Sourcing

---

## PDF Rendering & Templating Engines

| Option | Description | Selected |
|--------|-------------|----------|
| xhtml2pdf | Pure Python library (ReportLab-based). Lightweight, no system-level binary dependencies, very easy to install on Windows, but only supports basic CSS. | ✓ |
| WeasyPrint | Advanced CSS Paged Media layout engine. Produces beautiful, modern layouts, but requires installing GTK/Cairo system binaries on Windows. | |
| Playwright | Full modern HTML/CSS support (renders exactly like Chrome). Heavy dependency requiring a browser binary download. | |

**User's choice:** `xhtml2pdf`
**Notes:** Chosen because it is lightweight and pure Python, avoiding binary setup complexities on Windows.

| Option | Description | Selected |
|--------|-------------|----------|
| Jinja2 | Robust templating engine that natively handles nested lookups (e.g., cliente.nombre) and is already configured/supported. | ✓ |
| Custom regex-based | A minimal, lightweight custom helper using python regex to replace tokens. Avoids external dependencies but requires writing parser code. | |

**User's choice:** `Jinja2`
**Notes:** Natively resolves nested objects/dictionaries.

| Option | Description | Selected |
|--------|-------------|----------|
| Standard Letter/A4 layout | Letter/A4 size with @page rules in a default base CSS stylesheet (handles standard margins and page numbering natively). | ✓ |
| Strict inline styling | Let the HTML template explicitly style margins and sizes inline on container divs, bypassing @page rules. | |

**User's choice:** Standard Letter/A4 layout
**Notes:** Standardized margins and layout.

| Option | Description | Selected |
|--------|-------------|----------|
| Standard system/PDF fonts | Helvetica, Times, Courier — Zero setup, fast rendering, and reliable fallback. | ✓ |
| Embed a custom font | Stores the TrueType font file in backend storage and embeds it via @font-face for a premium aesthetic. | |

**User's choice:** Standard system/PDF fonts
**Notes:** Built-in fonts chosen for simplicity and zero setup overhead.

---

## Data Validation & Type Constraints

| Option | Description | Selected |
|--------|-------------|----------|
| Raise 400 Bad Request | Strict validation. If any field defined in the document type schema is missing from the payload, reject the request. | ✓ |
| Render as empty/blank | Do not error. Leave the missing tokens blank in the template and proceed with generation. | |

**User's choice:** Raise 400 Bad Request
**Notes:** Enforces completeness for legal and operational safety.

| Option | Description | Selected |
|--------|-------------|----------|
| Ignore extra fields | Filter the payload and only keep variables defined in the schema. | ✓ |
| Reject with 400 | Strict validation. Any field not defined in the schema must trigger an error. | |

**User's choice:** Ignore extra fields
**Notes:** Offers better forward-compatibility for callers passing larger data payloads.

| Option | Description | Selected |
|--------|-------------|----------|
| Coerce and validate | Attempt to convert/coerce values to their schema types (e.g., parsing a numeric string to a float). Raise 400 if coercion fails. | ✓ |
| Strict matching | Reject with 400 immediately if JSON types do not match schema types exactly. | |

**User's choice:** Coerce and validate
**Notes:** Flexible coercion simplifies client calls.

| Option | Description | Selected |
|--------|-------------|----------|
| ISO 8601 YYYY-MM-DD | Caller must supply YYYY-MM-DD. In Jinja2 templates, we provide a custom filter to let users render dates formatted. | ✓ |
| String passthrough | Accept any string for date fields without parsing/validation and render it directly as-is. | |

**User's choice:** ISO 8601 YYYY-MM-DD validation with Jinja2 format filter
**Notes:** Clear date contract and formatting utility.

---

## Issuance Persistence & PDF Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Save to disk | Write the generated PDF to local server storage (e.g., storage/issuances/) so it can be re-downloaded later. | ✓ |
| Stream-only | Generate the PDF in-memory, write it directly to the response stream, and discard it. | |

**User's choice:** Save to disk
**Notes:** Establishes permanent and audit-friendly storage.

| Option | Description | Selected |
|--------|-------------|----------|
| Track in DB | Create a DocumentIssuance table to store the issuance ID, design version, file path, and audit metadata. | ✓ |
| Stateless | Write the file to disk but do not record it in our database. | |

**User's choice:** Track in DB
**Notes:** Enables querying of generation history and direct re-downloads.

| Option | Description | Selected |
|--------|-------------|----------|
| UUID filename | UUID filename (e.g., {issuance_id}.pdf) — Zero collision risk, clean mapping, and secure. | ✓ |
| Human-readable naming | Human-readable timestamped filenames (e.g., {design_name}_{timestamp}.pdf). | |

**User's choice:** UUID filename
**Notes:** Collision-free and security-hardened.

| Option | Description | Selected |
|--------|-------------|----------|
| Store input payload | Add a JSONB column (e.g., input_data) on the DocumentIssuance model to persist the caller's raw JSON input. | ✓ |
| Do not store payload | Discard the input payload after rendering to minimize database growth. | |

**User's choice:** Store input payload (JSONB)
**Notes:** Vital for auditing and debugging rendering errors.

---

## Preview API & Mock Data Sourcing

| Option | Description | Selected |
|--------|-------------|----------|
| Caller-supplied + fallback | Allow callers to supply custom values. If a field is omitted, automatically generate a realistic fallback value based on the field type. | ✓ |
| Strictly caller-supplied | The caller must supply all token values. Any missing field triggers a 400. | |

**User's choice:** Caller-supplied with fallback to auto-generated mock data
**Notes:** Enables seamless "instant preview" workflows.

| Option | Description | Selected |
|--------|-------------|----------|
| Preview draft and active | Allow previewing any design version. This is critical for the visual designer to support live previews before activation. | ✓ |
| Active designs only | Restrict previewing only to fully activated/current designs. | |

**User's choice:** Preview both draft and active designs
**Notes:** Crucial for designer live-previews.

| Option | Description | Selected |
|--------|-------------|----------|
| PDF binary stream | Return the raw PDF bytes with Content-Type: application/pdf. | ✓ |
| JSON + temp URL | Save the preview PDF to a temporary file and return a JSON containing the URL. | |

**User's choice:** PDF binary stream
**Notes:** Straightforward frontend rendering inside native elements.

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral in-memory | Build the preview document in-memory without writing files to disk or creating database records. | ✓ |
| Temporary disk storage | Save the preview PDF to a temporary directory that is pruned periodically, but do not write to the database. | |

**User's choice:** Ephemeral in-memory rendering
**Notes:** Complies with the non-persistence contract and is high performance.

---

## the agent's Discretion

- Base CSS stylesheet template structure for margins and spacing rules.
- Specific python mock generators per data type.
- URL endpoint structure on the FastAPI backend routers.

## Deferred Ideas

- None.
