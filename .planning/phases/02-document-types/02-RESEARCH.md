# Phase 2: Document Types - Research

**Researched:** 2026-07-06
**Domain:** CRUD data-modeling feature on an established FastAPI + SQLAlchemy + Postgres backend, with a React 19 + react-router 7 frontend (form authoring + table browsing)
**Confidence:** HIGH

## Summary

Phase 2 is a self-contained CRUD slice on top of the working Phase 1 foundation (Postgres 16, SQLAlchemy 2.0.51, Alembic 1.18.5, FastAPI 0.139.0, Pydantic 2.13.4, cookie-session auth). There is no new infrastructure to stand up — the task is to add two related SQLAlchemy models (`DocumentType`, `DocumentTypeField`), an Alembic migration, Pydantic request/response schemas, three FastAPI endpoints (create, list, detail), and three React pages (create form, list table, detail/schema view), all behind the existing `get_current_user` cookie-session dependency. No RBAC/role system exists yet (AUTH-02 "fine-grained roles" is v2/out of scope) — "admin/operational user" in this phase's language means any authenticated user, not a distinct role check.

The main design decision left to research (per CONTEXT.md "Claude's Discretion") is the storage shape for typed fields: a normalized child table (`document_type_fields`, one row per field with `name`/`type`/`description`/`position`) versus a single JSONB column on `document_types`. The normalized-table approach is recommended: it matches the existing project convention (Phase 1 used dedicated tables for `users`/`sessions`, not JSON blobs), it lets Postgres enforce field-name uniqueness per document type via a `UNIQUE(document_type_id, name)` constraint instead of hand-rolled duplicate-checking, and it keeps the `type` column as a `VARCHAR` + `CHECK` constraint (not a native Postgres `ENUM`) so that if the 4 fixed types (string/number/date/boolean) ever need to expand, it's a plain `ALTER TABLE ... DROP CONSTRAINT / ADD CONSTRAINT`, not the more invasive `ALTER TYPE ... ADD VALUE` migration native enums require.

On the frontend, the existing codebase has no form library, no data table library, and `AuthenticatedShell.tsx` currently renders everything itself with no nested routing (`App.tsx` has exactly 2 flat routes). Phase 2 needs at least 2-3 new pages, so introducing `react-router-dom`'s nested-route/`<Outlet>` pattern is a small but necessary structural change, not just "add a page." For the add/remove field-row form (D-05), hand-rolling dynamic array state with array-index React keys is a well-known pitfall (breaks focus/state on remove); `react-hook-form`'s `useFieldArray` is the standard solution and its installed-version-compatible release (`^7.55.0`+ peer-supports React 16-19) is confirmed compatible with the project's React 19.2.7.

**Primary recommendation:** Normalized `document_types` + `document_type_fields` tables (VARCHAR+CHECK for type, not native enum), Pydantic v2 schemas with a `model_validator` rejecting duplicate field names, three FastAPI endpoints under `/api/document-types`, and a React nested-route layout under `AuthenticatedShell` using `react-hook-form` + `useFieldArray` for the schema-builder form.

## User Constraints

### Locked Decisions

- **D-01:** Each field/token consists of: name, type (string/number/date/boolean), and an optional description. Untyped "name-only" fields were rejected — typed fields are needed for real validation in Phase 3 (VALID-01) and clearer schema browsing (DOCTYPE-02).
- **D-02:** Dotted/namespaced token names (e.g. `cliente.nombre`, `servicio.tipo`) are an available convention, not an enforced structure. The platform treats the full token name as one opaque string — no nested-namespace parsing or grouping logic.
- **D-03:** Document types are freely editable after creation — an admin can add, remove, or rename fields at any time. No versioning of document types themselves (only document DESIGNS get versioned, per VERSION-01/02 in Phase 5). The risk of a schema edit breaking a design/template that referenced a removed field is explicitly accepted for MVP1.
- **D-04:** What happens to templates/designs referencing a removed field is explicitly deferred to Phase 3 (Content Building Blocks). Phase 2 defines schemas in isolation; nothing consumes them yet.
- **D-05:** Admin builds the schema via a form with add/remove field rows (name, type, description per row) — no JSON authoring required.
- **D-06:** A document type has name + description only as top-level metadata, beyond its field list. No category/tag system.
- **D-07:** The document type list shows: name, description, field count, AND created-by/created-at audit info per row (the local user record from Phase 1's D-07 already supports attribution).
- **D-08:** List layout is a table (not cards) — dense, scannable, fits an admin/operational tool.

### Claude's Discretion

- Exact DB schema for storing typed fields (JSONB column vs. a separate `document_type_fields` table) — **resolved by this research: normalized table, see Summary/Architecture Patterns.**
- Detail/schema view layout specifics (beyond "shows the full field list with types/descriptions").
- Whether type values are a fixed enum (string/number/date/boolean) or extensible — **resolved by this research: VARCHAR+CHECK, not native Postgres ENUM, to keep future expansion cheap; still exactly 4 allowed values for MVP1.**

### Deferred Ideas (OUT OF SCOPE)

- Category/tag system for organizing document types.
- Enforced nested-namespace schema structure (parsing `cliente.*` into real groups).
- Locking/versioning document types themselves once designs reference them.
- Field-removal impact handling (what breaks when a referenced field is deleted) — deferred to Phase 3.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCTYPE-01 | Admin/operational user can define a new document type with its own allowed data schema (tokens/fields) | Normalized schema design (Architecture Patterns), Pydantic request schema with duplicate-name validation (Code Examples), POST `/api/document-types` endpoint pattern, React form using `react-hook-form` + `useFieldArray` (Don't Hand-Roll) |
| DOCTYPE-02 | User can list/view existing document types and their schemas | GET list endpoint (lightweight, field_count only) + GET detail endpoint (full fields) — see Architecture Patterns; React table page (D-08) and detail page patterns |

## Project Constraints (from CLAUDE.md)

- **GSD Workflow Enforcement:** No direct file edits outside a GSD workflow (`/gsd:execute-phase` etc.) — applies to whoever implements this plan, not to this research doc.
- **Stack constraints (from project CLAUDE.md Technology Stack section):** Python 3.12+, uv package manager, no hard frontend/backend framework mandate — but Phase 1 already chose FastAPI + SQLAlchemy + Postgres + React 19 + Vite + Tailwind, and this phase must follow those established choices, not introduce alternatives.
- **Conventions:** No formatter/linter enforced yet for backend (no black/ruff in `backend/pyproject.toml`); frontend uses `oxlint`. Follow existing code style (4-space indent, type hints via `Mapped`/`mapped_column`, no docstrings mandated but present in Phase 1 code — match that documentation density).
- **Auth:** Must remain gated behind the Phase 1 OIDC/session mechanism — no new auth pattern for this phase's endpoints (reuse `get_current_user` / `verify_bearer_token_dep`).

## Standard Stack

### Core (already installed — no new dependencies required for backend)

| Library | Version (verified installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.51 | ORM models for `DocumentType`/`DocumentTypeField` | Already the project's ORM (Phase 1 `User`/`Session` models) |
| Alembic | 1.18.5 | Migration for new tables | Already the project's migration tool; Postgres is now live (unlike Phase 1's 0001 migration, this one CAN be autogenerated) |
| FastAPI | 0.139.0 | New `/api/document-types` router | Already the project's API framework |
| Pydantic | 2.13.4 | Request/response schemas, field-list validation | Ships with FastAPI; already a transitive dependency (`pydantic-settings`) |
| psycopg[binary] | (installed, per `backend/pyproject.toml`) | Postgres driver | Already the project's driver |

### Supporting (new frontend dependency recommended)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-hook-form | ^7.81.0 (latest; peer supports React 16-19) | Dynamic add/remove field-row form (D-05) | Any form with a variable-length list of inputs — exactly this phase's schema-builder |
| @hookform/resolvers | latest (peer requires react-hook-form ^7.55.0+) | Optional: wire a schema validator (zod) into react-hook-form | Only if zod (below) is also adopted; otherwise skip and use react-hook-form's built-in `rules` |
| zod | ^4.4.3 (latest) | Optional: shared client-side validation schema (name required, type in fixed set, duplicate check) | Nice-to-have for matching backend Pydantic validation client-side; not required to satisfy DOCTYPE-01/02 — Claude's Discretion whether to add it now or defer |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Normalized `document_type_fields` table | Single JSONB column on `document_types` storing `[{name, type, description}]` | Faster to write initially, but loses DB-enforced uniqueness on field name, loses a stable per-field `id` for future edit/delete-by-id operations, and diverges from the project's existing relational-table convention. Rejected. |
| VARCHAR + CHECK constraint for `type` | Native Postgres ENUM type (SQLAlchemy `Enum` with `native_enum=True`, the SQLAlchemy default) | Native enum is slightly more self-documenting in `psql \d`, but adding a 5th type later requires `ALTER TYPE ... ADD VALUE` (a Postgres-level DDL op, historically non-transactional pre-PG12, and Alembic's autogenerate handles it poorly). Given the discretion note ("start with fixed 4 types unless research surfaces a reason to expand"), VARCHAR+CHECK is the lower-friction choice for a schema likely to grow. |
| react-hook-form `useFieldArray` | Hand-rolled `useState<Field[]>` array with `.map((f, i) => ...)` using `index` as React `key` | Classic pitfall: removing a middle row with index-based keys causes React to reuse/misassign DOM state (e.g., focus, uncommitted input) to the wrong row. `useFieldArray` provides a stable `field.id` per row specifically to avoid this. |

**Installation:**
```bash
cd frontend
npm install react-hook-form
# Optional, only if adopting zod for shared validation:
npm install zod @hookform/resolvers
```

**Version verification:** Verified live against the npm registry on 2026-07-06:
- `react-hook-form` → 7.81.0 (peer: `react ^16.8.0 || ^17 || ^18 || ^19` — compatible with installed React 19.2.7)
- `zod` → 4.4.3
- `@hookform/resolvers` → peer requires `react-hook-form ^7.55.0` (satisfied)

No backend package version changes needed — `backend/pyproject.toml` already pins compatible versions; confirmed via `.venv/Scripts/python.exe -c "import ..."` that installed versions match the lockfile (SQLAlchemy 2.0.51, Alembic 1.18.5, FastAPI 0.139.0, Pydantic 2.13.4).

## Architecture Patterns

### Recommended Project Structure (additions only)
```
backend/
├── app/
│   ├── models/
│   │   └── document_type.py       # NEW: DocumentType + DocumentTypeField (aggregate pair, one file)
│   ├── schemas/                    # NEW package: Pydantic request/response models
│   │   └── document_type.py       # DocumentTypeCreate, DocumentTypeFieldIn, DocumentTypeOut, DocumentTypeListItem, DocumentTypeDetail
│   └── api/
│       └── document_types.py      # NEW: router, mounted at /api/document-types
├── alembic/versions/
│   └── 0002_document_types.py     # NEW migration (can be autogenerated — Postgres is live)
└── tests/
    └── test_document_types.py     # NEW

frontend/
├── src/
│   ├── pages/
│   │   ├── document-types/
│   │   │   ├── DocumentTypeListPage.tsx    # DOCTYPE-02 (table, D-08)
│   │   │   ├── DocumentTypeDetailPage.tsx  # DOCTYPE-02 (schema view)
│   │   │   └── DocumentTypeCreatePage.tsx  # DOCTYPE-01 (form, D-05)
│   │   └── AuthenticatedShell.tsx  # MODIFIED: becomes a layout with <Outlet/>, nested routes added in App.tsx
│   └── lib/
│       └── documentTypes.ts        # NEW: typed apiFetch wrappers (mirrors lib/api.ts pattern)
```

### Pattern 1: Normalized parent/child model with cascade delete-orphan
**What:** `DocumentType` owns a list of `DocumentTypeField` rows via a one-to-many relationship with `cascade="all, delete-orphan"`, ordered by an explicit `position` column (not insertion order, which Postgres does not guarantee on read).
**When to use:** Any time a parent aggregate has an ordered, typed list of children that the parent fully owns (children never exist independently) — exactly this phase's field list.
**Example:**
```python
# backend/app/models/document_type.py
# Source: SQLAlchemy 2.0 declarative Mapped/mapped_column style,
# following backend/app/models/session.py's existing relationship pattern
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ALLOWED_FIELD_TYPES = ("string", "number", "date", "boolean")


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]
    description: Mapped[str | None]
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    fields: Mapped[list["DocumentTypeField"]] = relationship(
        back_populates="document_type",
        cascade="all, delete-orphan",
        order_by="DocumentTypeField.position",
    )
    created_by = relationship("User")


class DocumentTypeField(Base):
    __tablename__ = "document_type_fields"
    __table_args__ = (
        UniqueConstraint("document_type_id", "name", name="uq_document_type_field_name"),
        CheckConstraint(
            f"type IN {ALLOWED_FIELD_TYPES!r}", name="ck_document_type_field_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="CASCADE")
    )
    name: Mapped[str]
    type: Mapped[str]  # VARCHAR + CHECK, not native Postgres ENUM (see Alternatives)
    description: Mapped[str | None]
    position: Mapped[int]

    document_type: Mapped["DocumentType"] = relationship(back_populates="fields")
```

### Pattern 2: Pydantic v2 schema with duplicate-name validation
**What:** Reject duplicate field names within a single create request at the API boundary (400/422), before it ever reaches the DB unique constraint (which would otherwise surface as a raw `IntegrityError`/500).
**When to use:** Any list-of-typed-items input where uniqueness matters within the request.
**Example:**
```python
# backend/app/schemas/document_type.py
# Source: Pydantic v2 model_validator pattern (docs.pydantic.dev/latest/concepts/validators/)
from typing import Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

FieldType = Literal["string", "number", "date", "boolean"]


class DocumentTypeFieldIn(BaseModel):
    name: str
    type: FieldType
    description: str | None = None


class DocumentTypeCreate(BaseModel):
    name: str
    description: str | None = None
    fields: list[DocumentTypeFieldIn]

    @model_validator(mode="after")
    def check_unique_field_names(self) -> "DocumentTypeCreate":
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Field names must be unique within a document type")
        return self


class DocumentTypeFieldOut(DocumentTypeFieldIn):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class DocumentTypeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    field_count: int
    created_by_email: str
    created_at: datetime


class DocumentTypeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    fields: list[DocumentTypeFieldOut]
    created_by_email: str
    created_at: datetime
```
Note: `field_count`/`created_by_email` aren't native ORM attributes — populate them explicitly in the route handler (e.g. `DocumentTypeListItem(id=dt.id, ..., field_count=len(dt.fields), created_by_email=dt.created_by.email)`) rather than trying to force `from_attributes` to compute them.

### Pattern 3: React nested routes under the authenticated shell
**What:** `AuthenticatedShell` becomes a layout route rendering `<Outlet/>` for its children, instead of a single page that renders everything inline.
**When to use:** As soon as more than one authenticated page exists — true starting this phase.
**Example:**
```tsx
// frontend/src/App.tsx
// Source: react-router-dom v7 nested routes (stable pattern since v6.4, unchanged in v7)
import { Routes, Route } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthenticatedShell from "./pages/AuthenticatedShell";
import DocumentTypeListPage from "./pages/document-types/DocumentTypeListPage";
import DocumentTypeDetailPage from "./pages/document-types/DocumentTypeDetailPage";
import DocumentTypeCreatePage from "./pages/document-types/DocumentTypeCreatePage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AuthenticatedShell />}>
        <Route path="document-types" element={<DocumentTypeListPage />} />
        <Route path="document-types/new" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id" element={<DocumentTypeDetailPage />} />
      </Route>
    </Routes>
  );
}
```
`AuthenticatedShell.tsx` keeps its existing 401-redirect `useEffect` (unchanged logic) but replaces its hardcoded `<section>...</section>` placeholder content with `<Outlet />`.

### Anti-Patterns to Avoid
- **JSON-authoring the schema:** D-05 explicitly rejects requiring JSON input for building the field list — the form UI is mandatory, not a "nice to have."
- **Trusting the DB unique constraint alone for duplicate field names:** Surfacing a raw Postgres `IntegrityError` as a 500 is a worse UX than a 422 from Pydantic validation; validate at the schema layer first (Pattern 2), let the DB constraint be the backstop.
- **Native Postgres ENUM for `type`:** Given the discretion note flags future extensibility as plausible, avoid `sa.Enum(..., native_enum=True)` (the SQLAlchemy default) — use `sa.String` + `CheckConstraint` instead (see Alternatives Considered).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dynamic add/remove form rows | `useState<Field[]>` + manual array splice + index-based `key` | `react-hook-form`'s `useFieldArray` | Index-based keys break input focus/state on row removal — well-documented React footgun; `useFieldArray` assigns a stable per-row `id` specifically to solve this |
| Duplicate field-name detection | String-loop dedup logic scattered across frontend and backend independently | One Pydantic `model_validator` (Pattern 2) as the single source of truth; frontend can optionally mirror it with zod but backend validation is the actual guard | Avoids two implementations drifting out of sync; Pydantic validator runs on every request regardless of client |
| Field-type constraint enforcement | App-code `if field.type not in [...]: raise` sprinkled in multiple places | Pydantic `Literal["string","number","date","boolean"]` (schema layer) + Postgres `CHECK` constraint (DB layer) | Two-layer defense is standard: schema layer gives a clean 422 to API callers, DB constraint protects against any code path that bypasses the schema (e.g. a future script/admin tool) |
| UUID generation for new rows | Custom ID scheme | `uuid.uuid4()` default on `mapped_column`, exactly as `User`/`Session` already do | Already the project's established primary-key convention (Phase 1) |

**Key insight:** Every "don't hand-roll" here already has an established, in-repo precedent (Phase 1's `User`/`Session` models, `uuid.uuid4` defaults) — the discipline for Phase 2 is consistency with what Phase 1 already proved out, not introducing new primitives.

## Common Pitfalls

### Pitfall 1: Alembic autogenerate misses new models if not imported in `env.py`
**What goes wrong:** `alembic revision --autogenerate` produces an empty migration (no `op.create_table` calls) even though new SQLAlchemy models exist.
**Why it happens:** `alembic/env.py` explicitly imports `from app.models import User, Session` to register them on `Base.metadata` before autogenerate diffs the metadata against the live DB. New models not added to that import (and to `app/models/__init__.py`'s `__all__`) never get registered, so Alembic sees "no changes."
**How to avoid:** Add `DocumentType, DocumentTypeField` to both `backend/app/models/__init__.py` and the import line in `backend/alembic/env.py` before running `alembic revision --autogenerate`.
**Warning signs:** Generated migration file has an empty or near-empty `upgrade()`/`downgrade()` body.

### Pitfall 2: List endpoint accidentally serializes full field arrays
**What goes wrong:** DOCTYPE-02's list view (D-07) only needs `field_count`, not the full field list — but if the route handler reuses `DocumentTypeDetail` (which includes `fields: list[...]`) for the list endpoint "for convenience," every list request pays for serializing every field of every document type.
**Why it happens:** Reusing one Pydantic model across list and detail endpoints is tempting but conflates two different response shapes.
**How to avoid:** Keep `DocumentTypeListItem` (lightweight, `field_count: int`) and `DocumentTypeDetail` (full `fields` array) as separate Pydantic models (Pattern 2) with separate route return types.
**Warning signs:** List endpoint response payload size grows linearly with total field count across all document types, not just document-type count.

### Pitfall 3: `created_by` attribution lazy-loads per row (N+1)
**What goes wrong:** D-07 requires `created_by` in the list view; if the route handler accesses `dt.created_by.email` in a loop over a plain `db.query(DocumentType).all()`, SQLAlchemy issues one extra `SELECT` per document type (N+1 queries).
**Why it happens:** The `created_by` relationship is lazy by default; accessing it outside the original query triggers a new query per instance.
**How to avoid:** Use `.options(joinedload(DocumentType.created_by))` (or `selectinload`) in the list query, matching the scale expected (small number of document types — either works, `selectinload` is generally safer for one-to-many but this is a many-to-one so `joinedload` is idiomatic).
**Warning signs:** Slow list endpoint response time that scales with row count; visible in query logs as repeated `SELECT * FROM users WHERE id = ...`.

### Pitfall 4: Editing scope ambiguity (D-03 vs. numbered success criteria)
**What goes wrong:** CONTEXT.md's D-03 ("document types are freely editable after creation") reads as a locked decision, but the phase's three numbered Success Criteria (create, list, view-schema) do not explicitly list "edit an existing document type" as a criterion to satisfy in Phase 2.
**Why it happens:** D-03/D-04 describe a *lifecycle property* (edits are allowed, no versioning) more than a proposal to build an edit UI/endpoint in this specific phase.
**How to avoid:** Flagged as an Open Question below — the planner should explicitly decide whether Phase 2 includes a PUT/PATCH edit endpoint + edit UI, or whether D-03 is scoped as "the door is open for a later phase to add editing" while Phase 2 itself only implements create+list+detail (no update/delete endpoints).
**Warning signs:** N/A (a scoping decision, not a runtime bug) — resolve before planning tasks, not during implementation.

## Code Examples

### FastAPI router (create + list + detail)
```python
# backend/app/api/document_types.py
# Source: follows backend/app/api/health.py's existing router-mounting pattern
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.document_type import DocumentType, DocumentTypeField
from app.models.user import User
from app.schemas.document_type import (
    DocumentTypeCreate,
    DocumentTypeDetail,
    DocumentTypeListItem,
)

router = APIRouter(prefix="/api/document-types", tags=["document-types"])


@router.post("", response_model=DocumentTypeDetail, status_code=201)
async def create_document_type(
    payload: DocumentTypeCreate,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentType:
    document_type = DocumentType(
        name=payload.name,
        description=payload.description,
        created_by_id=user.id,
        fields=[
            DocumentTypeField(name=f.name, type=f.type, description=f.description, position=i)
            for i, f in enumerate(payload.fields)
        ],
    )
    db.add(document_type)
    db.commit()
    db.refresh(document_type)
    return document_type


@router.get("", response_model=list[DocumentTypeListItem])
async def list_document_types(
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> list[DocumentTypeListItem]:
    rows = (
        db.query(DocumentType)
        .options(joinedload(DocumentType.created_by), joinedload(DocumentType.fields))
        .all()
    )
    return [
        DocumentTypeListItem(
            id=dt.id,
            name=dt.name,
            description=dt.description,
            field_count=len(dt.fields),
            created_by_email=dt.created_by.email,
            created_at=dt.created_at,
        )
        for dt in rows
    ]


@router.get("/{document_type_id}", response_model=DocumentTypeDetail)
async def get_document_type(
    document_type_id: UUID,
    user: User = Depends(get_current_user),
    db: SQLAlchemySession = Depends(get_db),
) -> DocumentType:
    document_type = (
        db.query(DocumentType)
        .options(joinedload(DocumentType.created_by), joinedload(DocumentType.fields))
        .filter_by(id=document_type_id)
        .first()
    )
    if document_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return document_type
```
Wire into `backend/app/main.py`: `app.include_router(document_types_router)` alongside the existing `auth_router`/`health_router` includes.

### React form with `useFieldArray`
```tsx
// frontend/src/pages/document-types/DocumentTypeCreatePage.tsx
// Source: react-hook-form useFieldArray docs (react-hook-form.com/docs/usefieldarray)
import { useFieldArray, useForm } from "react-hook-form";

type FieldRow = { name: string; type: "string" | "number" | "date" | "boolean"; description: string };
type FormValues = { name: string; description: string; fields: FieldRow[] };

export default function DocumentTypeCreatePage() {
  const { register, control, handleSubmit } = useForm<FormValues>({
    defaultValues: { name: "", description: "", fields: [{ name: "", type: "string", description: "" }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "fields" });

  // fields.map must key by field.id (react-hook-form's stable per-row id),
  // NOT by array index — see Don't Hand-Roll.
  return (
    <form onSubmit={handleSubmit(async (values) => { /* POST /api/document-types */ })}>
      {fields.map((field, index) => (
        <div key={field.id}>
          <input {...register(`fields.${index}.name`)} />
          <select {...register(`fields.${index}.type`)}>
            <option value="string">string</option>
            <option value="number">number</option>
            <option value="date">date</option>
            <option value="boolean">boolean</option>
          </select>
          <input {...register(`fields.${index}.description`)} />
          <button type="button" onClick={() => remove(index)}>Remove</button>
        </div>
      ))}
      <button type="button" onClick={() => append({ name: "", type: "string", description: "" })}>
        Add field
      </button>
    </form>
  );
}
```

## State of the Art

Not applicable in the "old vs. new approach" sense — this is greenfield within an established Phase 1 stack, not a migration off a legacy pattern. No deprecated approaches to flag.

## Open Questions

1. **Does Phase 2 include an edit (PUT/PATCH) endpoint and edit UI for document types, or only create + list + detail?**
   - What we know: D-03/D-04 (CONTEXT.md, locked decisions) state document types are "freely editable after creation" and describe the lifecycle/risk tradeoffs of editing.
   - What's unclear: The phase's three numbered Success Criteria only list create, list, and view-schema — not edit.
   - Recommendation: Planner should explicitly scope this. Given DOCTYPE-01/02 requirement text also only says "define" and "list/view," the safer reading is that Phase 2 ships create+list+detail only, and D-03 is establishing the *policy* (no versioning, edits allowed) for whenever an edit endpoint is added — potentially still this phase if the planner judges it cheap to add alongside create (same Pydantic schema, an UPDATE instead of INSERT), potentially deferred. Either is defensible; the plan should state which explicitly rather than leaving it implicit.

2. **Field ordering: does the UI/API need to let a user reorder fields after adding them (not just append/remove)?**
   - What we know: D-05 says "add/remove field rows" — reordering isn't mentioned.
   - What's unclear: Whether `position` is purely creation-order (append-only, no drag-to-reorder) or needs a reorder affordance.
   - Recommendation: Start with creation-order only (`position` = index at submit time); no drag-to-reorder UI needed for MVP1 unless the planner finds explicit evidence otherwise. `useFieldArray`'s `move()` method is available cheaply later if this changes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | New tables, Alembic migration | ✓ | 16 (docker-compose, container running) | — |
| Alembic autogenerate | Migration authoring | ✓ | 1.18.5, Postgres reachable so autogenerate (unlike Phase 1's hand-written 0001) will work | Hand-write migration if DB connection issue arises |
| SQLAlchemy | Models | ✓ | 2.0.51 | — |
| FastAPI | Router | ✓ | 0.139.0 | — |
| Pydantic | Schemas | ✓ | 2.13.4 | — |
| Node/npm | Frontend dependency install | ✓ | (npm registry reachable; used to verify react-hook-form/zod versions live) | — |
| react-hook-form | Dynamic field-row form | Not yet installed, but registry-verified available | 7.81.0 latest, peer-compatible with installed React 19.2.7 | Hand-rolled array state possible but not recommended (see Don't Hand-Roll) |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `react-hook-form` is not yet in `frontend/package.json` — needs `npm install react-hook-form` as part of this phase's first frontend task. No blocking risk; verified available and compatible.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (`pytest-asyncio` 1.4.0 also installed) |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| Quick run command | `cd backend && VIRTUAL_ENV= uv run pytest tests/test_document_types.py -q` (Phase 1 SUMMARYs note a stray `VIRTUAL_ENV` env var breaks `uv run pytest` in this shell — unset it first, or use `.venv/Scripts/python.exe -m pytest` directly) |
| Full suite command | `cd backend && VIRTUAL_ENV= uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCTYPE-01 | Create document type with valid fields succeeds (201, fields persisted with correct `position`) | integration | `uv run pytest tests/test_document_types.py::test_create_document_type -x` | ❌ Wave 0 |
| DOCTYPE-01 | Create with duplicate field names rejected (422) | integration | `uv run pytest tests/test_document_types.py::test_create_rejects_duplicate_field_names -x` | ❌ Wave 0 |
| DOCTYPE-01 | Create with invalid `type` value rejected (422, Pydantic `Literal` enforcement) | integration | `uv run pytest tests/test_document_types.py::test_create_rejects_invalid_field_type -x` | ❌ Wave 0 |
| DOCTYPE-01 | Unauthenticated create rejected (401) | integration | `uv run pytest tests/test_document_types.py::test_create_requires_auth -x` | ❌ Wave 0 |
| DOCTYPE-02 | List returns all document types with correct `field_count` and `created_by_email` | integration | `uv run pytest tests/test_document_types.py::test_list_document_types -x` | ❌ Wave 0 |
| DOCTYPE-02 | Detail endpoint returns full field list with types/descriptions for one document type | integration | `uv run pytest tests/test_document_types.py::test_get_document_type_detail -x` | ❌ Wave 0 |
| DOCTYPE-02 | Detail endpoint 404s for a nonexistent id | integration | `uv run pytest tests/test_document_types.py::test_get_document_type_not_found -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && VIRTUAL_ENV= uv run pytest tests/test_document_types.py -q`
- **Per wave merge:** `cd backend && VIRTUAL_ENV= uv run pytest -q` (full suite, including Phase 1's auth tests, to catch regressions from the new router/models)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_document_types.py` — covers DOCTYPE-01, DOCTYPE-02 (new file; reuses existing `client`/`db_session` fixtures from `backend/tests/conftest.py`, no new fixtures needed)
- [ ] `backend/alembic/versions/0002_document_types.py` — new migration (autogenerate now viable; see Common Pitfalls #1 for the import-registration gotcha)
- [ ] Frontend: no test framework currently detected in `frontend/package.json` (no vitest/jest/testing-library dependency) — if frontend tests are desired for the new pages, framework setup is itself a Wave 0 task; otherwise frontend verification stays manual per this project's current testing posture (Phase 1 had no frontend automated tests either).

## Sources

### Primary (HIGH confidence)
- Direct repository inspection: `backend/app/models/user.py`, `backend/app/models/session.py`, `backend/app/api/health.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/auth/dependencies.py`, `backend/app/auth/routes.py`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial_users_sessions.py`, `backend/tests/conftest.py`, `backend/tests/test_auth_gating.py`, `backend/pyproject.toml`, `frontend/package.json`, `frontend/src/App.tsx`, `frontend/src/pages/AuthenticatedShell.tsx`, `frontend/src/lib/api.ts`, `frontend/tailwind.config.ts`, `.design/DESIGN.md`, `docker-compose.yml`, `.env.example`
- Installed-version verification via `.venv/Scripts/python.exe -c "import ...; print(...__version__)"`: SQLAlchemy 2.0.51, Alembic 1.18.5, FastAPI 0.139.0, Pydantic 2.13.4
- npm registry live check (`npm view <pkg> version`/`peerDependencies`): react-hook-form 7.81.0, zod 4.4.3, @hookform/resolvers peer requirement
- `docker ps` — confirmed Postgres 16 and Keycloak 26.6 containers running for this project
- `.planning/phases/02-document-types/02-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/phases/01-foundation-authentication/01-01-SUMMARY.md`, `01-06-SUMMARY.md` (test command conventions, `VIRTUAL_ENV` quirk)
- WebFetch of official docs: `docs.sqlalchemy.org` (Enum type native_enum/migration behavior), `react-hook-form.com/docs/usefieldarray` (append/remove/key semantics)

### Secondary (MEDIUM confidence)
- None — WebSearch tool returned repeated 502 errors during this research session (inference gateway issue); all findings that would normally be WebSearch-sourced were instead verified via WebFetch against official docs or the npm registry directly, keeping them at HIGH rather than falling back to unverified MEDIUM/LOW claims.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all backend versions confirmed via direct `.venv` inspection; frontend additions confirmed via live npm registry query
- Architecture: HIGH — directly extends verified, working Phase 1 patterns (SQLAlchemy `Mapped`/`mapped_column`, FastAPI router mounting, Alembic autogenerate wiring)
- Pitfalls: HIGH — Pitfall 1 (Alembic env.py registration) and the `VIRTUAL_ENV` quirk are drawn directly from this repo's own Phase 1 SUMMARY documents, not general knowledge; Pitfalls 2-3 are standard, well-established ORM/ODM patterns

**Research date:** 2026-07-06
**Valid until:** 30 days (stable, established stack; no fast-moving dependencies in this phase's scope)
