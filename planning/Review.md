# Review.md

Phase-by-phase implementation log. Updated after each phase so essential context survives conversation compaction.

---

## Phase 1: Foundation & CSV Ingestion

**Status:** Complete  
**Date:** 2026-04-23

### What was built

- **Docker Compose** (`docker-compose.yml`): PostgreSQL, backend (FastAPI), frontend (Next.js) services. Postgres uses healthcheck; backend depends on healthy postgres.
- **Backend scaffold** (`backend/`): FastAPI app with lifespan, CORS, `/api/health` endpoint. Config via pydantic-settings loading `.env`.
- **Frontend scaffold** (`frontend/`): Next.js 16 App Router with Tailwind CSS v4, three pages (landing, upload, data browser).
- **SQLAlchemy models** (`backend/app/models/database.py`): All 14 tables from PLAN.md §3 — `csv_uploads`, `raw_rent_roll` (all 61 CSV columns mapped), `fund_mapping`, `tenant_master`, `tenant_name_alias`, `property_master` (~40 fields including ESG + tech specs), `data_inconsistencies`, `chat_sessions`, `chat_messages`, `master_data_audit`, `reporting_periods`, and 4 snapshot tables.
- **Parser plugin system** (`backend/app/parsers/`): Abstract `RentRollParser` base class with `detect()`, `extract_metadata()`, `parse()`. GARBE Mieterliste implementation handles encoding, apostrophe number format, dd.mm.yyyy dates, row-type classification, orphan fund inheritance, automatic fund discovery.
- **Schema validator** (`backend/app/core/schema_validator.py`): Column fingerprinting against expected 61-column header layout. Reports added/removed/changed columns.
- **Upload API** (`backend/app/api/upload.py`): `POST /api/upload` (multipart file → background parse), `GET /api/uploads` (list), `GET /api/uploads/{id}` (detail), `GET /api/uploads/{id}/rows` (paginated with row_type/fund/property_id filters), `DELETE /api/uploads/{id}`.
- **Upload UI** (`frontend/src/app/upload/page.tsx`): Drag-and-drop file upload with state machine (idle → uploading → processing → complete/error). Polls status every 1s. Shows summary on completion. Lists previous uploads.
- **Data browser UI** (`frontend/src/app/data/page.tsx`): Upload selector, row-type filter, paginated table (50 rows/page) with color-coded type badges and orphan-row highlighting.
- **API client** (`frontend/src/lib/api.ts`): Typed functions for all backend endpoints. Uses `NEXT_PUBLIC_API_URL` env var.

### Key technical decisions

| Decision | Rationale |
|---|---|
| `psycopg[binary]` instead of `psycopg2-binary` | psycopg2 fails to build on Windows; psycopg3 is the maintained successor |
| SQLAlchemy URL dialect `postgresql+psycopg://` | Required for psycopg3 driver registration |
| `set_session_factory()` pattern in upload.py | Background tasks run outside the request DI scope; this lets tests inject a test session |
| File-based SQLite (`sqlite:///test.db`) for tests | In-memory SQLite creates separate DBs per connection; file-based shares state across background task threads |
| `TESTING=1` env var to skip DB init in lifespan | Prevents test startup from connecting to PostgreSQL |
| Tailwind CSS v4 (CSS-based config via `@theme inline`) | Came with Next.js 16 scaffold; no `tailwind.config.ts` file |

### Test coverage

**47 tests passing** (`backend/tests/`):

- `test_parser.py` (36 tests): Numeric/percent/date parsing helpers, detect valid/invalid files, metadata extraction (fund_label, stichtag, fingerprint), full parse (row counts: 3298 data + 221 summary + 14 orphan + 1 total = 3534), orphan fund inheritance, LEERSTAND count, specific field values.
- `test_schema_validator.py` (4 tests): Valid schema, wrong column count, header mismatch, sample file validation.
- `test_upload_api.py` (7 tests): Health endpoint, full upload lifecycle (stichtag/fund_label/row counts), empty file rejection, list uploads, row browsing with type filter, property filtering, delete.

### Bugs fixed during implementation

| Bug | Root cause | Fix |
|---|---|---|
| `pip install psycopg2-binary` fails on Windows | No prebuilt wheel for Python version | Switched to `psycopg[binary]==3.2.9` |
| `ModuleNotFoundError: No module named 'psycopg2'` | SQLAlchemy defaults to psycopg2 dialect | Changed URL scheme to `postgresql+psycopg://` |
| Tests hang on startup | Lifespan tries to connect to PostgreSQL | Guard with `TESTING != "1"` env var check |
| `no such table: csv_uploads` in tests | In-memory SQLite gives each connection its own DB | Switched to file-based `sqlite:///test.db` |
| SQLAlchemy `LegacyAPIWarning` for `Query.get()` | Deprecated in SQLAlchemy 2.0 | Replaced `db.query(X).get(id)` with `db.get(X, id)` |

### File inventory

```
docker-compose.yml
.env
.env.example
.gitignore
CLAUDE.md
backend/
  requirements.txt
  Dockerfile
  app/
    __init__.py
    main.py
    config.py
    database.py
    models/
      __init__.py
      database.py    (14 SQLAlchemy models)
      schemas.py     (Pydantic response schemas)
    parsers/
      __init__.py
      base.py        (abstract RentRollParser)
      garbe_mieterliste.py
    core/
      __init__.py
      schema_validator.py
    api/
      __init__.py
      upload.py
  tests/
    __init__.py
    conftest.py
    test_parser.py
    test_schema_validator.py
    test_upload_api.py
frontend/
  package.json
  Dockerfile
  next.config.ts
  tsconfig.json
  src/
    app/
      layout.tsx
      page.tsx
      globals.css
      upload/page.tsx
      data/page.tsx
    lib/
      api.ts
```

---

## Design System: GARBE Industrial Branding

**Status:** Complete  
**Date:** 2026-04-23  
**Added to:** PLAN.md §15

Applied GARBE Industrial Design Manual to the frontend. Key changes:

- **Colors:** Custom GARBE palette registered via Tailwind v4 `@theme inline` — GARBE-Blau (`#003255`) with 4 tint steps, GARBE-Grün (`#64B42D`) with 3 tints, plus Ocker, Rot, Türkis accent colors and neutral tones.
- **Typography:** Switched from Geist to Open Sans via `next/font/google`. Global CSS sets `h1`–`h4` to uppercase, semibold, `letter-spacing: 0.045em`, GARBE-Blau color.
- **Nav bar:** GARBE-Blau background, white brand text, GARBE-Blau-20 link colors with white hover.
- **Tables:** GARBE-Blau-20 header band, alternating white/off-white rows, GARBE-Ocker highlight for orphan rows.
- **Buttons:** Primary = GARBE-Grün, secondary/outline = GARBE-Blau, destructive = GARBE-Rot.
- **Status badges:** Green (complete), teal (processing), red (error), ocker (warning).
- **Drop zone:** GARBE-Blau-60 dashed border, transitions to GARBE-Grün on drag-over.
- **Landing page:** Green dot accent on "RentRoll." headline.

Build verified clean (all 4 routes compile, 47 backend tests pass).

---

## Phase 2: Inconsistency Detection & Resolution

**Status:** Complete  
**Date:** 2026-04-24

### What was built

- **Detection engine** (`backend/app/core/inconsistency_detector.py`): Top-level `detect_inconsistencies(db, upload_id)` function that idempotently detects 4 categories of data quality issues:
  - `aggregation_mismatch` (warning): Compares SUM of data/orphan rows per property against summary row values for area, annual/monthly rent, parking, market rent, ERV. Tolerance >1%. Summary rows have property_id in the `fund` field (col[0]) extracted via regex `^\d{2,4}\s*-\s*`.
  - `unmapped_tenant` (error): Tenants with no entry in `tenant_name_alias`. LEERSTAND excluded.
  - `unmapped_fund` (error): Funds with no entry in `fund_mapping`.
  - `missing_metadata` (warning): Properties with no entry in `property_master`.
- **Upload integration** (`backend/app/api/upload.py`): Detection runs automatically after CSV parsing in `_process_upload()`.
- **Pydantic schemas** (`backend/app/models/schemas.py`): `InconsistencyListItem`, `InconsistencyUpdate`, `InconsistencySummary`.
- **REST API** (`backend/app/api/inconsistencies.py`): `GET /inconsistencies` (paginated, filterable by upload_id/category/severity/status), `GET /inconsistencies/summary` (counts + has_blocking_errors), `GET /inconsistencies/{id}`, `PATCH /inconsistencies/{id}` (resolve/acknowledge/ignore), `POST /inconsistencies/{upload_id}/recheck`.
- **Frontend quality page** (`frontend/src/app/inconsistencies/page.tsx`): Upload selector, 4 summary cards (errors/warnings/info/resolved), export readiness banner, filter dropdowns (category/severity/status), paginated table with severity/category/status badges, resolution modal with action selector and note field.
- **Frontend API client** (`frontend/src/lib/api.ts`): Added `InconsistencyItem`, `InconsistencySummary` interfaces and `listInconsistencies`, `getInconsistencySummary`, `updateInconsistency`, `recheckInconsistencies` functions.
- **Nav link** (`frontend/src/app/layout.tsx`): Added "Quality" link after "Data".

### Codex review findings (fixed)

| Finding | Severity | Fix |
|---|---|---|
| Zero-vs-nonzero aggregation mismatches silently skipped | P1 | Now flagged with 100% deviation instead of being skipped |
| Pagination order non-deterministic when `created_at` ties | P2 | Added secondary sort by `id DESC` |

### Test coverage

**73 tests passing** (47 existing + 26 new):

- `test_inconsistency_detector.py` (11 tests): No false positives on real data, unmapped tenants/funds/properties detected, LEERSTAND excluded, mapped entities not flagged, re-run idempotency, synthetic aggregation mismatch, zero-vs-nonzero mismatch.
- `test_inconsistency_api.py` (15 tests): List/filter/summary endpoints, get single/not-found, resolve/acknowledge/ignore actions, invalid status rejection, blocking errors cleared after resolve, recheck endpoint, pagination.

### Files changed

```
backend/app/core/inconsistency_detector.py    (new)
backend/app/api/inconsistencies.py            (new)
backend/tests/test_inconsistency_detector.py  (new)
backend/tests/test_inconsistency_api.py       (new)
frontend/src/app/inconsistencies/page.tsx     (new)
backend/app/api/upload.py                     (modified — detection call)
backend/app/main.py                           (modified — router registration)
backend/app/models/schemas.py                 (modified — 3 new schemas)
frontend/src/lib/api.ts                       (modified — 4 functions, 2 interfaces)
frontend/src/app/layout.tsx                   (modified — Quality nav link)
planning/reviews/codex-review-20260424-101031.md (new — Codex review report)
```

### Deferred to later

- Cross-upload diff detection (new/removed tenants, rent changes) — requires multiple uploads of different periods.
- Side-by-side DiffPreview component for resolution workflow.

---

## Phase 3A: CRUD APIs + Mapping UI

**Status:** Complete  
**Date:** 2026-04-24

### What was built

- **Audit utility** (`backend/app/core/audit.py`): Field-level change tracking via `MasterDataAudit` table. Functions: `log_changes` (compares old/new dicts, creates entry per changed field), `log_creation`, `log_deletion`, `snapshot` (extracts field dict from ORM object). Serializes None/datetime/date/Decimal to strings.
- **Pydantic schemas** (`backend/app/models/schemas.py`): 15 new schema classes — Fund (Create/Update/Response), Tenant (AliasCreate/AliasResponse, MasterCreate with `initial_alias` convenience field, MasterUpdate, MasterResponse with nested aliases), Property (Create with ~40 optional fields, Update, Response), UnmappedItem.
- **CRUD API** (`backend/app/api/master_data.py`): Single router for all three entity types. Fund endpoints (list/create/update/delete), Tenant endpoints (list with alias join search, create with optional initial_alias, detail, update, delete with cascade, add/remove alias), Property endpoints (list/create/detail/partial update/delete), Unmapped endpoint (groups open inconsistencies by entity_id).
- **Auto-resolution**: Creating a fund mapping auto-resolves `unmapped_fund` inconsistencies. Adding a tenant alias auto-resolves `unmapped_tenant`. Creating a property auto-resolves `missing_metadata`. Uses `_resolve_inconsistencies(db, category, entity_id)` bulk-update helper.
- **Frontend API client** (`frontend/src/lib/api.ts`): 5 interfaces + 15 fetch functions for all CRUD operations.
- **Frontend page** (`frontend/src/app/master-data/page.tsx`): Tab bar (Funds/Tenants/Properties) with GARBE styling. Each tab has unmapped banner (garbe-rot for errors, garbe-ocker for warnings, quick-create buttons), search, data table, create/edit modals, inline alias management for tenants.
- **Nav link** (`frontend/src/app/layout.tsx`): Added "Master Data" link after "Quality".
- **Form styling** (`frontend/src/app/globals.css`): Added `.form-input` CSS class.

### Codex review findings (fixed)

| Finding | Severity | Fix |
|---|---|---|
| Duplicate initial aliases not rejected in `create_tenant` | P1 | Added alias uniqueness check before insert |
| Duplicate BVI tenant IDs cause unhandled 500 | P2 | Added `IntegrityError` handling with rollback and 400 response |
| Edit forms can't clear optional fields (blank → `undefined` → dropped) | P2 | Changed update handlers to send `null` instead of `undefined`; updated TypeScript types to accept `string \| null` |
| Alias creations not audited (only deletions were) | P3 | Added `log_creation` call for both `add_alias` and `initial_alias` paths |

### Test coverage

**111 tests passing** (73 existing + 38 new):

- `test_audit.py` (6 tests): log_changes detects diffs, ignores unchanged, handles types (date/Decimal/None), log_creation records non-None, log_deletion records non-None, snapshot captures fields.
- `test_master_data_api.py` (32 tests): Fund CRUD (create, duplicate rejection, list, search, update, update_not_found, delete, auto-resolve inconsistency), Tenant CRUD (create, create with alias, duplicate initial alias rejection, duplicate BVI ID rejection, list, search canonical, search by alias, detail, update, delete cascades, add/remove alias, alias duplicate rejection, auto-resolve inconsistency), Property CRUD (create, duplicate, list, search city, partial update, delete, auto-resolve inconsistency), Unmapped (grouped, filter by type), Audit (update creates entries with correct old/new values).

### Files changed

```
backend/app/core/audit.py                     (new)
backend/app/api/master_data.py                (new)
backend/tests/test_audit.py                   (new)
backend/tests/test_master_data_api.py         (new)
frontend/src/app/master-data/page.tsx         (new)
backend/app/models/schemas.py                 (modified — 15 new schemas)
backend/app/main.py                           (modified — master_data router)
frontend/src/lib/api.ts                       (modified — 5 interfaces, 15 functions)
frontend/src/app/layout.tsx                   (modified — Master Data nav link)
frontend/src/app/globals.css                  (modified — .form-input class)
CLAUDE.md                                     (modified — Review.md mandatory update rule)
planning/reviews/codex-review-20260424-phase3a.md (new — Codex review report)
```

### Deferred to Phase 3B

- BVI G2 XLSX importer
- AG Grid for data browser
- Excel roundtrip (export/import)
- Completeness dashboard
- Fuzzy tenant/fund matching suggestions
- Single-property detail form (full 40-field editing)
