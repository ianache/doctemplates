# Phase 10 UAT Checklist: Complex Schema UI & Previsualization

Please complete the following browser verification steps to sign off on Phase 10 execution:

### 🚀 Setup Steps
1. Make sure both frontend and backend are running.
   - Frontend dev server: `npm run dev` (in the `frontend/` directory)
   - Backend server: `uvicorn main:app` or equivalent dev script (in the `backend/` directory)
2. Log in using the app's OIDC / login flow.

---

### 📋 UAT Test Cases

- [ ] **TC-1: Visual Complex Schema Configuration**
  - Go to **Document Types** -> **New Document Type**.
  - Add the following fields:
    - `cliente.nombre` (string)
    - `cliente.direccion.calle` (string)
    - `cliente.contactos[].nombre` (string)
    - `cliente.contactos[].telefono` (string)
  - Verify that the sidebar/fields editor groups these visually under parent objects and lists.
  - Save the Document Type.

- [ ] **TC-2: Collapsible Tree Visualization**
  - Go to the detail view of the newly created Document Type.
  - Confirm that the fields are rendered as a collapsible tree:
    - `cliente` is shown as an object folder.
    - `direccion` is shown as a nested object folder.
    - `contactos` is shown as a list folder.
    - Primitive fields (`nombre`, `calle`, `telefono`) display their full canonical paths and types correctly.

- [ ] **TC-3: Mock Data Auto-Generation**
  - Create or open a **Document Design** associated with the new Document Type.
  - Toggle the preview panel/frame to generated preview mode.
  - Verify that the raw JSON panel is pre-populated with nested mock data (e.g. `{ "cliente": { "nombre": "...", "direccion": { "calle": "..." }, "contactos": [{ "nombre": "...", "telefono": "..." }] } }`).

- [ ] **TC-4: Interactive Previsualization & Edit**
  - Edit the generated mock JSON values in the code editor panel.
  - Click **Preview** or trigger the preview generation.
  - Confirm that the generated PDF loads in the preview panel and reflects the edited mock data.
  - Confirm that if you write invalid JSON, a validation error is displayed.

- [ ] **TC-5: localStorage Mock Data Persistence**
  - Modify some mock JSON values, then refresh the page.
  - Verify that your edited JSON payload is preserved in the code editor and does not reset to the default schema-generated values.
  - Click **Reset** and verify that it correctly regenerates the default mock JSON from the schema.

- [ ] **TC-6: Generation vs. Preview Audits**
  - Generate multiple previews.
  - Confirm that no document issuance records or audit trace logs are created on the backend.

---

### 💬 Submission
Once completed, please reply with **`approved`** to complete the phase, or describe any issues/errors encountered.
