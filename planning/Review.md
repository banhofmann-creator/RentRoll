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

---

## Phase 3B: BVI Import, Completeness, Fuzzy Matching, Detail Form, AG Grid, Excel Roundtrip

**Status:** Complete  
**Date:** 2026-04-25

### What was built

**Step 1 — BVI G2 Importer (Backend)**

- **Parser** (`backend/app/parsers/bvi_g2_importer.py`): Reads `G2_Property_data` sheet from BVI XLSX via openpyxl. `COL_MAP` maps ~40 column indices (1-indexed) to PropertyMaster field names. `CRREM_COLS` maps cols 120-130 to CRREM sub-field keys assembled into a JSON dict. `_coerce_value()` handles datetime→date, int/float coercion, string cleanup. `parse_bvi_g2(file_bytes)` returns `(properties, warnings)`, deduplicating by property_id (merges non-null values across period rows). BVI fund ID from col 2 stored as `_bvi_fund_id` metadata.
- **API** (`backend/app/api/bvi_import.py`): `POST /api/bvi-import/preview` returns properties_found, new/existing counts, field_coverage, bvi_fund_ids, warnings. `POST /api/bvi-import/execute?mode=fill_gaps|overwrite` upserts properties with audit logging, auto-resolves `missing_metadata` inconsistencies.
- **Test helper** (`backend/tests/conftest.py`): `make_test_bvi_xlsx(rows)` generates minimal G2 XLSX for tests.

**Step 2 — Completeness + Fuzzy Matching (Backend)**

- **Completeness endpoint** (`GET /api/master-data/completeness`): Returns fill rates per field group (`core_location`, `green_building`, `financial_valuation`, `esg_sustainability`, `technical_specs`) and per tenant field. `PROPERTY_FIELD_GROUPS` constant defines grouping.
- **Fuzzy matching endpoints**: `GET /api/master-data/tenants/suggest?q=<name>&limit=5` and `GET /api/master-data/funds/suggest?q=<name>&limit=5` using `difflib.SequenceMatcher` (threshold 0.4). Registered before `{id}` routes to avoid path conflict.
- **New schemas** (`backend/app/models/schemas.py`): `FieldStat`, `FieldGroupStats`, `CompletenessResponse`, `FuzzyMatch`.

**Step 3 — Frontend: Completeness + BVI Import + Fuzzy Match UI**

- **CompletenessDashboard**: Collapsible panel above tabs, per field group: horizontal bar with fill rate %, colored garbe-grun (>80%), garbe-ocker (40-80%), garbe-rot (<40%). Tenant fields shown separately.
- **BVI Import modal**: "Import BVI" button in header. Modal with file input → preview summary (properties/new/existing counts, fund IDs) → mode radio (fill_gaps/overwrite) → execute → result summary.
- **Fuzzy match in TenantsTab**: When creating a tenant, debounced `suggestTenants()` call shows "Similar existing tenants" badges with match percentage above the create form.
- **API client** (`frontend/src/lib/api.ts`): Added `getCompleteness()`, `suggestTenants()`, `suggestFunds()`, `previewBviImport()`, `executeBviImport()`. Expanded `PropertyMaster` interface to all 44 fields.

**Step 4 — Single-Property Detail Form**

- **Detail page** (`frontend/src/app/master-data/properties/[id]/page.tsx`): Fetches property via `GET /api/master-data/properties/{id}`. Horizontal tab bar for 5 field groups (Core/Location, Green Building, Financial, ESG with CRREM sub-editor, Technical). 2-column grid layout. Dirty tracking: only PATCH changed fields. Sticky Save/Cancel bar. Breadcrumb navigation.
- **Property links**: Property ID in table is now a `<Link>` to `/master-data/properties/{id}`.
- **API**: Added `getProperty(id)` function.

**Step 5 — AG Grid for Multi-Property Editing**

- **Dependencies**: `ag-grid-community@35.2.1`, `ag-grid-react@35.2.1`.
- **Grid page** (`frontend/src/app/master-data/properties/grid/page.tsx`): AG Grid with Quartz theme, column groups matching field groups, property_id + city pinned left, editable cells with immediate `PATCH` per cell. Breadcrumb navigation.
- **Grid Editor link**: Added to PropertiesTab toolbar.

**Step 6 — Excel Roundtrip**

- **Backend** (`backend/app/api/excel_roundtrip.py`): `GET /api/master-data/properties/export` generates XLSX with grouped headers (row 1: group names, row 2: field names, row 3+: data). `POST /api/master-data/properties/import/preview` parses XLSX and returns diff list `[{property_id, field, current_value, new_value, change_type}]`. `POST /api/master-data/properties/import/apply?mode=fill_gaps|overwrite` applies changes with audit trail.
- **Frontend**: "Download XLSX" link and "Upload & Diff" button on PropertiesTab. Diff preview modal with color-coded table (green=add, yellow=update), mode selection, result summary.

### Codex review findings (fixed)

| Finding | Severity | Fix |
|---|---|---|
| XLSX roundtrip false diffs for date/numeric fields (openpyxl datetime vs ORM date/Decimal) | P1 | Added `_normalize()` for type-aware comparison in both preview and apply |
| CRREM keys in property detail form don't match BVI parser keys | P1 | Updated frontend CRREM_KEYS to match parser output (`retail_high_street`, `industrial_warehouse`, etc.) |
| BVI import update path doesn't resolve missing_metadata inconsistencies | P2 | Added `_resolve_missing_metadata` to update branch + new test |
| Excel import creation path has no audit trail or auto-resolve | P2 | Added `log_creation`, `snapshot`, `_resolve_missing_metadata` to creation path |

### Test coverage

**137 tests passing** (111 existing + 26 new):

- `test_bvi_import.py` (10 tests): Preview, preview with existing, fill_gaps creates new, fill_gaps preserves existing, overwrite replaces, empty rows skipped, deduplication, audit entries, resolves missing metadata, invalid mode rejected.
- `test_master_data_api.py` (40 tests, +8 new): completeness empty/with data/tenant fields, suggest tenants exact/partial/no match, suggest funds partial/no match.
- `test_excel_roundtrip.py` (7 tests): Export valid XLSX, roundtrip no changes, roundtrip with changes, apply fill_gaps, apply overwrite, apply creates new, apply audit entries.

### Files changed

```
backend/app/parsers/bvi_g2_importer.py           (new)
backend/app/api/bvi_import.py                    (new)
backend/app/api/excel_roundtrip.py               (new)
backend/tests/test_bvi_import.py                 (new)
backend/tests/test_excel_roundtrip.py            (new)
frontend/src/app/master-data/properties/[id]/page.tsx  (new)
frontend/src/app/master-data/properties/grid/page.tsx  (new)
backend/app/main.py                              (modified — 2 new routers)
backend/app/api/master_data.py                   (modified — completeness + fuzzy endpoints)
backend/app/models/schemas.py                    (modified — 4 new schemas)
backend/tests/test_master_data_api.py            (modified — 8 new tests)
backend/tests/conftest.py                        (modified — BVI XLSX fixture)
frontend/src/lib/api.ts                          (modified — 12 new functions/interfaces)
frontend/src/app/master-data/page.tsx            (modified — dashboard, import, fuzzy, links)
frontend/package.json                            (modified — ag-grid deps)
```

### Deferred

- AG Grid batch PATCH endpoint (per-cell PATCH works for MVP)
- CRREM tab in property detail form has basic numeric inputs; could use dedicated area editor later
- Excel roundtrip selective apply (checkbox per change) — currently applies all changes

---

## Phase 4: Transformation & Validation

**Status:** Complete  
**Date:** 2026-04-25

### What was built

**Z1 Aggregation Engine** (`backend/app/core/aggregation.py`)
- Groups CSV data rows by (fund, property_id, tenant_name), excluding LEERSTAND
- Sums annual_net_rent per group to produce one Z1 row per tenant per property
- Joins fund_mapping for BVI fund IDs, tenant_master + aliases for BVI tenant IDs, NACE sectors, PD values
- Sorted output by fund → property → tenant

**G2 Aggregation Engine** (`backend/app/core/aggregation.py`)
- Full 144-column aggregation from raw_rent_roll data per (fund, property_id):
  - Floor areas by unit type (10 types: Büro, Halle, Empore/Mezzanine, Freifläche, Gastronomie, Einzelhandel, Hotel, Rampe, Wohnen, Sonstige)
  - Parking totals (let vs total) from Stellplätze rows
  - Rent by use type (total, let, vacant) — 33 rent columns
  - ERV by use type (12 columns)
  - Lease expiry bucketing: year(lease_end) - year(stichtag) → buckets 0-9, 10+, open-ended
  - Market rental value from summary row × 12
  - Reversion = (market - contractual) / contractual
  - Rent per sqm
  - WAULT from summary row
  - USE_TYPE_PRIMARY via 75% rule
  - ESG + technical specs passthrough from property_master
- LEERSTAND exclusions: not counted in tenant count, floorspace_let, let_rent; included in rentable_area, vacant_rent (using market_rent_monthly × 12)

**USE_TYPE_PRIMARY Derivation** (`derive_use_type()`)
- If any single type ≥ 75% of total area → that type
- If no type ≥ 75% but only one type > 25% → largest type
- If multiple types > 25% → MISCELLANEOUS
- Empty → OTHER

**Validation Engine** (`validate_aggregation()`)
- Compares aggregated values vs property summary rows for: rentable_area, annual_net_rent, parking_count, market_rent
- Flags discrepancies > 1%
- Returns sorted by deviation (highest first)

**Transform API** (`backend/app/api/transform.py`)
- `GET /api/transform/z1/preview?upload_id=` — Z1 aggregation preview
- `GET /api/transform/g2/preview?upload_id=` — G2 aggregation preview
- `GET /api/transform/validation?upload_id=` — validation check results
- Upload status validation (must be "complete")

**Frontend Transform Preview** (`frontend/src/app/transform/page.tsx`)
- Upload selector (filters to complete uploads)
- Z1 tab: full tenant/lease table with fund, property, tenant, NACE, PD, rent
- G2 tab: sub-grouped columns (Identity, Areas, Rent, Lease Expiry, Valuation) with toggleable column groups
- Validation tab: green/red status indicator, issue table with property, field, expected, actual, deviation %
- German number formatting, alternating row colors, GARBE design system

### Codex review findings (fixed)

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | P1 | `gross_potential_income` excluded vacant market rent | Changed to `contractual_rent + sum(vacant_rent_*)` |
| 2 | P2 | Reversion = -100% when no summary row (market_rental_value=0) | Added `market_rental_value` guard, returns `None` when unknown |
| 3 | P2 | Truthiness checks on numeric fields turned zeros into `None` | Changed to `is not None` checks |

### Test coverage

- 34 new tests in `test_aggregation.py`
- 171 total backend tests pass
- Frontend builds clean (9 routes)

Tests cover:
- USE_TYPE_PRIMARY: dominant, threshold, single above 25%, miscellaneous, empty
- Z1: basic aggregation, LEERSTAND exclusion, multiple tenants, tenant alias lookup
- G2: areas, tenant count, rent by type, ERV, let vs vacant, floorspace_let, use_type_primary, lease expiry bucketing (0-9, 10+, open-ended), property_master field passthrough, market rental/reversion, rent_per_sqm, parking let/total
- Validation: no issues, area mismatch, rent mismatch, within tolerance
- API endpoints: z1/g2 preview, validation, upload not found, upload not ready

### Files changed

| File | Action |
|---|---|
| `backend/app/core/aggregation.py` | Created — Z1/G2 aggregation, USE_TYPE_PRIMARY, validation |
| `backend/app/api/transform.py` | Created — 3 preview/validation endpoints |
| `backend/app/main.py` | Modified — registered transform router |
| `backend/app/models/schemas.py` | Modified — Z1/G2/Validation response schemas |
| `backend/tests/test_aggregation.py` | Created — 31 tests |
| `frontend/src/app/transform/page.tsx` | Created — transform preview UI |
| `frontend/src/app/layout.tsx` | Modified — added Transform nav link |
| `frontend/src/lib/api.ts` | Modified — transform API client functions |

### Deferred

- G2 column sub-groups in frontend (rent by type, ERV breakdown) — only showing summary columns in preview; full 144-column view deferred to export phase
- Validation auto-creation of DataInconsistency records — currently returns issues but doesn't persist them; will integrate with inconsistency workflow in Phase 5

---

## Phase 5: Reporting Period Management & BVI Export

**Status:** Complete  
**Date:** 2026-04-25

### What was built

- **Reporting Period API** (`backend/app/api/periods.py`): Full CRUD for reporting periods plus finalization workflow:
  - `POST /api/periods` — create draft period from a completed upload (enforces one period per stichtag)
  - `GET /api/periods` / `GET /api/periods/{id}` — list and detail
  - `DELETE /api/periods/{id}` — delete draft periods only (finalized periods protected)
  - `GET /api/periods/{id}/finalize-check` — pre-flight check: counts blocking errors, unmapped tenants/funds, property field completeness percentage, returns warnings list and `can_finalize` boolean
  - `POST /api/periods/{id}/finalize` — snapshots all master data (property, tenant, alias, fund) into snapshot tables, sets status to "finalized" with timestamp
  - `GET /api/periods/{id}/export` — streams BVI XLSX (draft or finalized), filename includes DRAFT suffix for unfinalised periods

- **Snapshot engine** (`_create_snapshot()` in periods.py): Copies all `PropertyMaster`, `TenantMaster`, `TenantNameAlias`, and `FundMapping` records into their snapshot counterparts, preserving all fields and creating `tenant_id_map` for alias FK remapping. Returns counts per entity type.

- **BVI XLSX export engine** (`backend/app/core/bvi_export.py`): Generates the exact BVI Target Tables format:
  - Z1 sheet: 11-row header block with BVI codes, type annotations, and group headers; data from row 12
  - G2 sheet: 144-column layout with all field groups (identity, address, green building, ownership, valuation, floor area, parking, debt, rents by type, ERV, let/vacant rent, lease expiry, ESG/CRREM, tech specs, reversion)
  - Draft watermark ("PROVISIONAL - NOT FINALIZED") in row 1 for unfinalised periods
  - Proper openpyxl 1-based column indexing throughout (off-by-one bug identified and fixed)
  - Special handling for lease expiry buckets, open-ended leases, and CRREM floor area sub-fields

- **Frontend periods page** (`frontend/src/app/periods/page.tsx`): Full period management UI with:
  - Period table showing stichtag, status badge (draft/finalized), upload reference, timestamps
  - "New Period" modal with upload selector (filters to available completed uploads)
  - "Finalize" flow: runs finalize-check first, shows blocking errors/unmapped counts/completeness with color-coded pass/fail indicators, warnings panel, then confirm button (disabled if can_finalize is false)
  - "Delete" confirmation modal for draft periods
  - "Export" download link for any period
  - GARBE design system throughout (garbe-blau, garbe-grun, garbe-ocker, garbe-rot)

- **API client** (`frontend/src/lib/api.ts`): Added `Period`, `FinalizeCheck`, `FinalizeResult` interfaces and 7 functions: `listPeriods`, `createPeriod`, `getPeriod`, `deletePeriod`, `getFinalizeCheck`, `finalizePeriod`, `periodExportUrl`

### Key technical decisions

| Decision | Rationale |
|---|---|
| 0-indexed field map arrays with `col_idx + 1` for openpyxl | Matches G2_LABELS/G2_FIELD_MAP structure (index 0 = None placeholder for col A); consistent with header writing loops |
| CRREM key lookup via `col_idx - 120` (0-based) | CRREM fields start at G2_FIELD_MAP[120]; indexes directly into 0-based CRREM_KEYS array |
| Finalize-check as separate GET endpoint | Allows preview before committing; frontend can show warnings without triggering snapshot |
| Snapshot copies all fields dynamically | `PropertyMaster.__table__.columns` iteration avoids manual field listing; future fields auto-included |
| Period-per-stichtag uniqueness | Prevents duplicate periods; enforced at API level with 409 response |

### Bug fixes

- **Off-by-one in G2 data writing**: `enumerate(G2_FIELD_MAP)` produces 0-based indices but openpyxl cells are 1-based. Fixed by using `col_idx + 1` in both header loops and data writing loop.

### Test coverage

16 tests in `test_periods.py` — all passing:
- Period CRUD: create, duplicate (409), incomplete upload (400), list, get, delete draft, delete finalized rejected (400)
- Finalization: check clean (can_finalize=True), check with errors (can_finalize=False), creates snapshots (verifies counts + DB records), finalize twice rejected (400)
- Export: draft (PROVISIONAL watermark, correct data cells), finalized (no watermark), G2 headers (correct labels at expected columns), lease expiry columns, not found (404)

Full suite: 187 tests passing, no regressions.

### Files changed

| File | Action |
|---|---|
| `backend/app/api/periods.py` | Created — period CRUD, finalize-check, finalize, export, snapshot engine |
| `backend/app/core/bvi_export.py` | Created — BVI XLSX generation (Z1 + G2 sheets, 144 columns) |
| `backend/app/main.py` | Modified — registered periods router |
| `backend/tests/test_periods.py` | Created — 16 tests |
| `frontend/src/app/periods/page.tsx` | Created — period management UI |
| `frontend/src/app/layout.tsx` | Modified — added Periods nav link |
| `frontend/src/lib/api.ts` | Modified — period API client types and functions |

### Deferred

- Snapshot-based export (using frozen snapshot data instead of live master data for finalized periods) — currently both draft and finalized exports use live aggregation
- Period notes editing — field exists in model but no UI to edit
- Period comparison view — comparing two periods side by side

---

## Test Suite Optimization

**Status:** Complete  
**Date:** 2026-04-25

Refactored backend test infrastructure for speed and maintainability:

- **Centralized conftest.py**: All test files now share `test_engine`, `TestSession`, `setup_db` (autouse), `client`, `db` fixtures. Eliminated ~120 lines of duplicated boilerplate across 9 test files.
- **Table truncation instead of drop/create**: `setup_db` truncates all tables between tests instead of `Base.metadata.drop_all() / create_all()`. Tables created once per session via `_ensure_tables()`.
- **Cached CSV parse**: `test_inconsistency_detector.py` caches the parsed CSV result in a module-level global, eliminating redundant re-parsing.
- **Test consolidation**: Merged read-only tests that share the same setup into single test functions (e.g., list/browse/filter → single `test_upload_csv`).

**Result:** 92s → 20s (78% reduction), 192 tests (down from 196 via consolidation, same assertion coverage).

---

## Phase 6: Time-Series Analysis

**Status:** Complete  
**Date:** 2026-04-25

### What was built

**Analytics API** (`backend/app/api/analytics.py`)
- `GET /api/analytics/kpis?status=finalized|all` — cross-period portfolio KPIs: total_rent, total_area, vacant_area, vacancy_rate, tenant_count, property_count, fair_value, total_debt, wault_avg. Separate helpers `_csv_kpis()` (from raw_rent_roll via upload_id) and `_snapshot_kpis()` (from snapshot_property_master).
- `GET /api/analytics/compare?period_a=&period_b=` — side-by-side period comparison with absolute and percentage deltas for all metrics.
- `GET /api/analytics/properties/{property_id}/history` — per-property time series across finalized periods.
- Parking (Stellplätze) excluded from area calculations, LEERSTAND excluded from tenant counts, WAULT computed from property_summary rows.

**Frontend Analytics Page** (`frontend/src/app/analytics/page.tsx`)
- KPI summary cards (8 cards showing latest period values)
- Rent & Fair Value area chart (dual Y-axis, GARBE-Blau for rent, GARBE-Grün for fair value)
- Vacancy Rate trend chart (GARBE-Ocker)
- Period Comparison: dropdown selectors for two periods, comparison table with color-coded deltas (green positive, red negative)
- Property History: lookup by property ID, bar chart (rent + vacancy), detail table
- "Include draft periods" toggle
- Built with Recharts (recharts@2.x)

**API Client** (`frontend/src/lib/api.ts`): Added `PeriodKPI`, `PeriodComparisonMetric`, `ComparisonResponse`, `PropertySnapshot` interfaces and `getPortfolioKPIs()`, `comparePeriods()`, `getPropertyHistory()` functions.

### Test coverage

12 new tests in `test_analytics.py`:
- KPIs: single period (all fields), multiple periods, draft excluded, draft included with `status=all`, empty, parking excluded from area, WAULT from summary rows
- Comparison: period-to-period deltas and percentages, not found (404)
- Property history: multi-period with vacancy, empty property, draft excluded

Full suite: **192 tests passing** in ~20s, no regressions.

### Files changed

| File | Action |
|---|---|
| `backend/app/api/analytics.py` | Created — 3 analytics endpoints with KPI helpers |
| `backend/tests/test_analytics.py` | Created — 12 tests |
| `backend/app/main.py` | Modified — registered analytics router |
| `frontend/src/app/analytics/page.tsx` | Created — Recharts dashboard with charts and comparison |
| `frontend/src/app/layout.tsx` | Modified — added Analytics nav link |
| `frontend/src/lib/api.ts` | Modified — analytics API types and functions |
| `frontend/package.json` | Modified — added recharts dependency |

### Deferred

- Fund-level filtering on KPI endpoints (currently portfolio-wide only)
- Property-level fair value / debt in property history (currently only portfolio-level in KPIs)
- Exportable chart images / PDF reports

---

## Phase 7: AI Chatbot

**Status:** Complete  
**Date:** 2026-04-26

### What was built

**Chat Tool System** (`backend/app/core/chat_tools.py`)
- 11 tool definitions for the Claude API tool_use interface:
  - **Read tools** (execute immediately): `query_raw_data` (filtered rent roll rows), `query_portfolio_summary` (aggregated KPIs), `search_tenants` (by canonical name or alias), `list_properties` (with search), `list_inconsistencies` (filtered by category/severity/status), `list_periods`, `compare_periods` (cross-period deltas)
  - **Write tools** (require user confirmation): `update_tenant`, `update_property`, `update_fund_mapping`, `resolve_inconsistency`
- All write tools use the audit system (`log_changes` with `changed_by="chatbot"`) for full traceability
- Field validation for property updates (rejects unknown column names)
- `WRITE_TOOLS` set for confirmation gating; `execute_tool()` dispatcher

**Chat API** (`backend/app/api/chat.py`)
- `GET /api/chat/sessions` — list recent sessions
- `GET /api/chat/sessions/{id}/messages` — get conversation history
- `DELETE /api/chat/sessions/{id}` — delete session
- `POST /api/chat/message` — send message, returns response with tool results and pending confirmations
- Domain-specific system prompt with GARBE/BVI terminology and safety instructions
- Multi-turn tool loop: up to 10 iterations of Claude calling tools and receiving results
- Confirmation workflow: write tool calls are blocked until the user sends `confirmed_tool_calls` IDs
- Messages persisted in `chat_sessions` + `chat_messages` tables (already existed from Phase 1 schema)
- Uses `claude-sonnet-4-6` model via Anthropic SDK

**Frontend Chat UI** (`frontend/src/app/chat/page.tsx`)
- Sidebar with session list, new chat button, session delete
- Chat area with message history, user/assistant/system message bubbles
- Tool usage indicators showing which tools were called
- Confirmation bar for write operations: shows pending changes with Approve/Cancel buttons
- "Thinking..." indicator during API calls
- Responsive layout (sidebar + chat split)
- GARBE design system throughout

**API Client** (`frontend/src/lib/api.ts`): Added `ChatSession`, `ChatMessageItem`, `PendingConfirmation`, `ChatResponse` interfaces and `listChatSessions()`, `getChatMessages()`, `deleteChatSession()`, `sendChatMessage()` functions.

### Key technical decisions

| Decision | Rationale |
|---|---|
| Synchronous (non-streaming) API | Simpler implementation; streaming can be added later. Tool loop completes server-side. |
| Confirmation via `confirmed_tool_calls` IDs | Frontend holds pending IDs, re-sends them on confirm. Clean round-trip without server-side state. |
| `claude-sonnet-4-6` model | Fast enough for interactive use; cheaper than Opus for high-volume chat |
| Separate `chat_tools.py` from `chat.py` | Tool definitions and executors are testable independently without mocking the Claude API |
| Max 10 tool iterations per request | Prevents runaway loops while allowing multi-step reasoning |

### Test coverage

24 new tests in `test_chat.py`:
- **Tool execution (16 tests)**: Tool definitions valid, query_raw_data (basic + filter + no upload), portfolio_summary, search_tenants (canonical + alias), list_properties, list_inconsistencies, update_tenant (success + not found), update_property (success + invalid field), update_fund_mapping, resolve_inconsistency, unknown tool
- **API endpoints (8 tests)**: Session create (mocked Claude), read tool executed, write tool needs confirmation, confirmed write executes, session continuity, session list/delete, session not found, chat session not found

Full suite: **216 tests passing** in ~21s, no regressions.

### Files changed

| File | Action |
|---|---|
| `backend/app/core/chat_tools.py` | Created — 11 tool definitions + executors |
| `backend/app/api/chat.py` | Created — chat API with Claude integration |
| `backend/tests/test_chat.py` | Created — 24 tests |
| `backend/app/main.py` | Modified — registered chat router |
| `backend/requirements.txt` | Modified — added anthropic==0.52.0 |
| `frontend/src/app/chat/page.tsx` | Created — chat UI with confirmation workflow |
| `frontend/src/app/layout.tsx` | Modified — added Chat nav link |
| `frontend/src/lib/api.ts` | Modified — chat API types and functions |

### Deferred

- Streaming responses (SSE) for real-time token display
- "Ask the chatbot" button on inconsistency page (pre-fill context)
- Chat message search / export
- Rate limiting on write operations
- Context window management for long conversations

---

## Phase 8: Reporting & Slides

**Status:** Complete  
**Date:** 2026-04-26

### What was built

**PPTX Slide Generation Engine** (`backend/app/core/slides.py`)
- GARBE-branded presentations with custom colors (GARBE_BLAU, GARBE_GRUN, GARBE_OCKER, GARBE_ROT, GARBE_TURKIS)
- Helper functions: `_new_pres()`, `_add_title_slide()`, `_add_content_slide()`, `_add_kpi_box()`, `_add_table()`, `_chart_to_image()` (matplotlib pie charts), `_add_bar_chart()` (pptx native charts)
- **`generate_property_factsheet(db, upload_id, property_id)`**: 2-3 slide factsheet with KPI boxes (area, rent, vacancy, WAULT, tenants), pie chart (area by unit type via matplotlib), top tenants table
- **`generate_portfolio_overview(db, upload_id)`**: Multi-slide overview with portfolio KPIs, fund rent breakdown (native bar chart), top 10 tenants by rent (native bar chart), full property summary table
- **`generate_lease_expiry_profile(db, upload_id)`**: Lease expiry waterfall chart (native column chart) bucketed by year, plus summary table
- **`generate_fund_summary(db, upload_id, fund_name)`**: Fund-level KPIs with property summary table

**Reports API** (`backend/app/api/reports.py`)
- `GET /api/reports/property-factsheet?upload_id=&property_id=` — StreamingResponse PPTX download
- `GET /api/reports/portfolio-overview?upload_id=` — StreamingResponse PPTX download
- `GET /api/reports/lease-expiry?upload_id=` — StreamingResponse PPTX download
- `GET /api/reports/fund-summary?upload_id=&fund=` — StreamingResponse PPTX download
- `GET /api/reports/available-funds?upload_id=` — list distinct funds for picker
- `GET /api/reports/available-properties?upload_id=` — list distinct property IDs for picker
- All endpoints validate upload exists and is "complete"; property/fund endpoints return 404 if no matching data

**Frontend Reports Page** (`frontend/src/app/reports/page.tsx`)
- Upload selector (filters to complete uploads)
- Portfolio Reports section: Portfolio Overview and Lease Expiry Profile download cards
- Fund Summary section: fund dropdown selector + download button
- Property Factsheet section: property dropdown selector + download button
- Downloads open in new tab (browser handles PPTX download via Content-Disposition)
- Auto-loads available funds and properties when upload changes

**API Client** (`frontend/src/lib/api.ts`): Added `getAvailableFunds()`, `getAvailableProperties()`, `getPropertyFactsheetUrl()`, `getPortfolioOverviewUrl()`, `getLeaseExpiryUrl()`, `getFundSummaryUrl()` functions.

### Key technical decisions

| Decision | Rationale |
|---|---|
| python-pptx native charts for bar/column charts | matplotlib 3.10.3 has infinite recursion bug (`copy.deepcopy` in `Path.__deepcopy__`) on Python 3.14 for bar/barh charts |
| matplotlib only for pie charts | Pie charts work fine on Python 3.14; matplotlib pie → image → slide is simpler than pptx native pie |
| `_add_bar_chart()` using `XL_CHART_TYPE.BAR_CLUSTERED` / `COLUMN_CLUSTERED` | Reliable across Python versions, rendered natively by PowerPoint |
| Lazy imports in API endpoints (`from app.core.slides import ...`) | Avoids importing matplotlib at module load time; reduces startup cost for non-report requests |

### Bug fixes

| Bug | Root cause | Fix |
|---|---|---|
| `RecursionError` in matplotlib bar/barh charts | Python 3.14 `copy.deepcopy` incompatibility in matplotlib 3.10.3 `MarkerStyle._set_marker` → `Path.__deepcopy__` | Replaced matplotlib bar charts with python-pptx native charts (`_add_bar_chart()` helper) |

### Test coverage

10 new tests in `test_reports.py`:
- Property factsheet: generates valid PPTX (2+ slides), 404 for missing property, content verification (property_id + city in slide text)
- Portfolio overview: generates valid PPTX (3+ slides)
- Lease expiry profile: generates valid PPTX (2+ slides)
- Fund summary: generates valid PPTX (2+ slides), 404 for missing fund
- Available funds/properties: returns correct distinct values
- Upload not found: 404

Full suite: **226 tests passing** in ~21s, no regressions.

### Files changed

| File | Action |
|---|---|
| `backend/app/core/slides.py` | Created — PPTX generation engine with 4 report types |
| `backend/app/api/reports.py` | Created — 6 report API endpoints |
| `backend/tests/test_reports.py` | Created — 10 tests |
| `backend/app/main.py` | Modified — registered reports router |
| `backend/requirements.txt` | Modified — added python-pptx==1.0.2, matplotlib==3.10.3 |
| `frontend/src/app/reports/page.tsx` | Created — reports download UI |
| `frontend/src/app/layout.tsx` | Modified — added Reports nav link |
| `frontend/src/lib/api.ts` | Modified — report API URL builders and fetch functions |

### Deferred

- Custom slide templates (user-uploadable .pptx template files)
- PDF export alternative to PPTX
- Comparison reports (two periods side by side)
- Chart color customization per fund/property
- Batch report generation (all properties at once)

---

## Phase 9: Output Channels & Integrations

**Status:** Complete  
**Date:** 2026-05-04

### What was built

**Output channel plugin system** (`backend/app/channels/`)
- `base.py`: Added the Phase 9 channel contract from `spec-architecture.md` §4:
  - `OutputChannel` abstract base with `push(files, metadata)` and `test_connection()`
  - dataclasses `ExportFile`, `ExportMetadata`, and `PushResult`
- `local_filesystem.py`: Implemented `LocalFilesystemChannel`, which writes generated files into `exports/{fund}/{stichtag}/` and reports structured push results.
- `registry.py`: Added channel registration and lookup helpers (`register_channel`, `get_channel`, `list_channels`) with `local_filesystem` pre-registered.
- `channels/__init__.py`: Exported the channel types and registry helpers for consistent imports.

**Investor reporting pack generator** (`backend/app/core/investor_pack.py`)
- Added `generate_investor_pack(db, period_id, fund=None) -> (zip_bytes, filename, list[ExportFile])`.
- Resolves the `ReportingPeriod` and its `CsvUpload`, determines fund/property scope, and assembles:
  - BVI XLSX via `generate_bvi_xlsx(...)`
  - portfolio overview PPTX
  - lease expiry profile PPTX
  - one fund summary PPTX per included fund
  - one property factsheet PPTX per included property
- Wraps every generated asset as an `ExportFile`, then bundles the pack into a ZIP archive for API download or channel push.
- Supports all-fund packs and fund-filtered packs without touching the existing slide/BVI generators.

**Export API** (`backend/app/api/export.py`)
- Added `GET /api/export/channels` to surface available channels and descriptions.
- Added `POST /api/export/investor-pack?period_id=&fund=` to generate and stream the investor-pack ZIP.
- Added `POST /api/export/investor-pack/preview?period_id=&fund=` to return the pack manifest (`filename`, `file_count`, `files`).
- Added `POST /api/export/push` to generate the pack, resolve a channel via the registry, and return the `PushResult`.
- Registered the router in `backend/app/main.py` under `/api`.

**Frontend export dashboard** (`frontend/src/app/export/page.tsx`)
- Added a new App Router client page for the export workflow:
  - reporting period selector using `GET /api/periods`
  - optional fund selector driven by `GET /api/reports/available-funds?upload_id=...`
  - preview action showing a file manifest table
  - download action that submits a `POST` request in a new tab for the ZIP response
  - push-to-channel section with result feedback
- Styled to match the existing GARBE pages and inserted an `Export` nav link between `Reports` and `Chat`.

**Frontend API client** (`frontend/src/lib/api.ts`)
- Added `ChannelInfo`, `InvestorPackPreview`, and `PushResult` interfaces.
- Added `getExportChannels()`, `previewInvestorPack()`, `investorPackUrl()`, and `pushToChannel()` following the existing `API_BASE` + fetch/error-handling pattern.

### Test coverage

13 new tests in `backend/tests/test_export.py`:
- Channel registry coverage for `list_channels`, valid lookup, and invalid lookup.
- Local filesystem channel coverage for `test_connection()`, directory creation, file writes, file contents, pushed-file count, and destination reporting.
- Investor pack coverage for ZIP generation, expected BVI/PPTX filenames, fund-filtered output, and missing-period error handling.
- Export API coverage for channel discovery, ZIP download, preview manifest, successful local filesystem push, missing period (404), and invalid channel (400).

Validation run:
- `cd backend && python -m pytest tests/test_export.py -v` → 13 passed
- `cd backend && python -m pytest --tb=short -q` → 239 passed, ~20s
- `cd frontend && npx next build` → clean (15 routes)

### Files changed

| File | Action |
|---|---|
| `backend/app/channels/base.py` | Created — output channel ABC and dataclasses |
| `backend/app/channels/local_filesystem.py` | Created — local filesystem output channel |
| `backend/app/channels/registry.py` | Created — channel registry and pre-registration |
| `backend/app/channels/__init__.py` | Modified — exported channel types/helpers |
| `backend/app/core/investor_pack.py` | Created — investor pack assembly and ZIP bundling |
| `backend/app/api/export.py` | Created — export channel listing, preview, download, push endpoints |
| `backend/app/main.py` | Modified — registered export router |
| `backend/tests/test_export.py` | Created — 13 Phase 9 tests |
| `frontend/src/app/export/page.tsx` | Created — export dashboard UI |
| `frontend/src/app/layout.tsx` | Modified — added Export nav link |
| `frontend/src/lib/api.ts` | Modified — export API types and client helpers |

### Codex review findings (fixed by Claude Code)

| Finding | Severity | Fix |
|---|---|---|
| `tmp_path` fixture fails on Windows with `PermissionError` on `C:\Users\...\AppData\Local\Temp\pytest-of-*` | P1 (2 tests erroring) | Replaced pytest's `tmp_path` with a custom fixture using `Path.cwd() / ".tmp_export_tests"` + `uuid4` subdirs + `shutil.rmtree` cleanup |
| Review.md reported "12 tests / 238 passed" but actual count was 13 tests / 239 passed | P3 | Corrected counts |

### Deferred

- SharePoint / Box / Drooms output channel plugins
- Celery job queue migration for export and push workflows
- Additional parser plugins for non-GARBE rent roll formats
- Scheduled / automated exports

---

## Codex Workflow Lessons Learned

**Accumulated across Phases 2–9. Kept here so future sessions can reuse the workflow without re-deriving it.**

### Running Codex from Claude Code

- **CLI**: `codex exec -s workspace-write -C "C:/projects/RentRoll" -o "<output-file>" < <prompt-file>`
- **Prompt via stdin**: Codex reads from stdin when no positional prompt is given. Write the prompt to a file first, then pipe it with `cat prompt.txt | codex exec ...`. Heredocs in Bash tool calls are unreliable (Codex hangs on "Reading additional input from stdin...").
- **Do not use `--approval-mode`** — that flag does not exist. The correct flag is `-s workspace-write` (sandbox policy). Available values: `read-only`, `workspace-write`, `danger-full-access`.
- **Output file** (`-o`): Codex writes its final summary to this file. Useful for review reports but not essential — the real deliverables are the file changes on disk.
- **Timeout**: Codex implementations typically take 3–8 minutes. Use `run_in_background: true` with a 600s timeout.

### Prompt design

- **Write the prompt to a file** (`planning/codex-<phase>-prompt.txt`) rather than inline. This makes it reviewable, rerunnable, and avoids shell escaping issues.
- **Be explicit about file paths and function signatures.** Codex follows instructions literally — vague descriptions lead to structural mismatches. Name every file to create, every function signature, every endpoint path.
- **Reference existing code by path for patterns.** "Follow the pattern in test_reports.py" works better than describing the pattern abstractly.
- **List constraints explicitly.** Python version, test runner expectations, "do not modify existing files" — Codex respects these when stated clearly.
- **Split implementation and tests into separate prompts** if the implementation is large (6+ files). Codex sometimes skips tests or Review.md when the main implementation is complex. A focused second prompt for tests + docs is more reliable.

### Review checklist (Claude Code after Codex)

1. `git status` — verify expected files were created/modified, no unexpected changes
2. Run existing tests (`pytest --tb=short -q`) — check for regressions before looking at new code
3. Read every new file Codex created — check for:
   - Correct imports and no circular dependencies
   - Proper error handling (HTTPException codes match spec)
   - Windows compatibility (file paths, temp directories, permissions)
   - Pattern consistency with existing codebase
4. Run new tests in isolation (`pytest tests/test_<new>.py -v`) — identify failures
5. Fix platform-specific issues (Windows `tmp_path`, path separators, encoding)
6. Run full suite again to confirm fix doesn't regress
7. Verify frontend builds (`npx next build`) — Codex sometimes generates TSX that fails type-checking
8. Update Review.md with accurate test counts and fix Codex's self-reported numbers if they're wrong

### Common Codex issues on this project

| Issue | Frequency | Workaround |
|---|---|---|
| Skips tests when implementation prompt is large | 2/4 phases | Send a separate test-focused prompt |
| Skips Review.md update | 1/4 phases | Include in test prompt as fallback |
| `tmp_path` pytest fixture fails on Windows | Every phase with filesystem tests | Use custom fixture with `tempfile.mkdtemp()` or project-local `.tmp_*` dir |
| Self-reports wrong test counts in Review.md | 2/4 phases | Always verify with actual `pytest` run and correct |
| Uses sample CSV data in tests instead of synthetic | First attempt on 2 phases | Explicitly say "create synthetic test data, do NOT use sample files" |

---

## 2026-05-04 Frontend Hotfix: Data Page Header Keys

**Status:** Complete  
**Date:** 2026-05-04

### What changed

- Fixed the React duplicate-key warning in `frontend/src/app/data/page.tsx` caused by rendering two table headers with the same `"Type"` key.
- Changed the header mapping to use `key={`${h}-${index}`}` so duplicate labels no longer collide.
- Simplified the row-loading logic by inlining the async fetch inside the `useEffect`, removing the extra `useCallback` wrapper.

### Why this was needed

- The data browser renders two columns labeled `"Type"` (row type and unit type), and the previous `key={h}` implementation produced non-unique React keys.
- ESLint also flagged the previous `useEffect(() => loadRows(), [loadRows])` pattern in this file with `react-hooks/set-state-in-effect`.

### Verification

- `cmd /c npx eslint src/app/data/page.tsx` â†’ passed
- Full frontend lint was not used for verification because the current repo-level ESLint run hits an unrelated permission error while scanning `frontend/.pytest_cache`.

---

## 2026-05-04 G2 Targeted Net Rent: Fallback Chain for Vacancies

**Status:** Complete
**Date:** 2026-05-04

### What changed

- **Aggregation** (`backend/app/core/aggregation.py`): Vacant units now contribute an *imputed* targeted net rent computed via a fallback chain — AM-ERV (col 36 × 12) → Market rent (col 35 × 12) → unit's own contract rent (col 30, typically 0). Previously vacant units used market rent only with no ERV preference and no fallback.
- **Per-use-type targeted columns (54–65)** are now consistent with their let / vacant breakdown. Previously `rent_*` accumulated contract rent for all rows (so vacant office contributed 0 even when market or ERV existed), meaning col 54 = col 78 (let), independent of col 89 (vacant). Now col 54 = col 78 + col 89 by construction.
- `g2.gross_potential_income` recomputed as `sum(rent_* across use types)` instead of `contractual_rent + total_vacant_rent`. Mathematically equivalent under the new semantics, but avoids confusion if a vacant row ever carries a non-zero contract rent (no double counting).
- **Spec updates**:
  - `planning/spec-columns.md` cols 51–65 and 89–99: documented the fallback chain and the per-use-type identity (`col 54 = col 78 + col 89`).
  - `planning/spec-transforms.md`: rewrote the rent-by-use-type pseudocode to define `targeted_per_unit` and use it for cols 53, 54–65, 89–99.

### Why this was needed

User flagged that "Targeted Net Rent" should reflect the asset manager's targeted rental value for vacant space, not just market rent. The original spec (and code) used market rent for vacancy only, and never consulted AM-ERV — even though AM-ERV (the asset manager's expected rental value) is the more authoritative target. The fallback chain preserves robustness when ERV or market rent is missing.

### Domain rules preserved

- `CONTRACTUAL_RENT` (col 51) still uses actual contract rent only — unchanged.
- `let_rent_*` (cols 78–88) still uses contract rent for occupied units — unchanged.
- `LEERSTAND` exclusion from tenant counts, lease-expiry buckets, parking_let — unchanged.
- ERV totals (cols 66–77) — unchanged (still SUM erv × 12 for all rows).

### Test coverage

**242 backend tests passing** (`pytest --tb=short -q`, 22.4 s).

New tests in `backend/tests/test_aggregation.py`:
- `test_g2_gross_potential_income_vacant_uses_market_when_no_erv` — fallback step 2 (no ERV → market).
- `test_g2_gross_potential_income_vacant_prefers_erv_over_market` — fallback step 1 (ERV beats market).
- `test_g2_gross_potential_income_vacant_falls_back_to_contract` — fallback step 3 (no ERV, no market → contract, typically 0).
- `test_g2_targeted_rent_by_use_type_equals_let_plus_vacant` — verifies the `rent_* = let_rent_* + vacant_rent_*` identity.

Existing test `test_g2_let_vs_vacant_rent` (market-only fallback) continues to pass under the new semantics.

### Files changed

- `backend/app/core/aggregation.py` — vacant-row branch + `gross_potential_income` recomputation.
- `backend/tests/test_aggregation.py` — renamed existing GPI test, added 3 new tests for fallback chain.
- `planning/spec-columns.md` — col 51–65 and 89–99 derivation rules.
- `planning/spec-transforms.md` — rent-by-use-type pseudocode.

### Codex review findings (2026-05-04, `planning/reviews/codex-review-20260504-211125.md`)

- **[P2] GPI dropped rows with unmapped `unit_type`** — fixed by accumulating `g2.gross_potential_income` directly inside the per-row loop instead of summing `_RENT_ATTR.values()` afterward. The summation approach silently dropped any row whose `unit_type` was not a key in `_RENT_ATTR` (defensive against future CSV variants); the new direct accumulation includes them and remains identity-equal to `let + vacant` for mapped types. New test `test_g2_gross_potential_income_includes_unmapped_unit_type` guards the regression. Final test count: **243 passing**.
- **[P1] Untracked CSV `backend/uploads/Mieterliste_1-Garbe (2).csv`** — pre-existing untracked file in the workspace, not introduced by this change. Flagged so it is not accidentally committed; recommend extending `.gitignore` to cover `/backend/uploads` (currently only `/uploads`) before any commit.

### Deferred items

- Existing real-data exports (if any have been generated) will not match new outputs — re-export expected after this change.
- `.gitignore` does not cover `backend/uploads/` (only `uploads/`); raw rent-roll CSVs dropped there are not auto-ignored. Worth tightening separately.
---

## 2026-05-04 RR-1 Phase A: PPTX Refresh — token-mode infrastructure

**Status:** Complete (Phase A)  
**Date:** 2026-05-04

### What was built

- **Data model** (`backend/app/models/database.py`): Added `PptxRefreshJob` using the existing SQLAlchemy `Base`, JSON columns for proposals/confirmed mappings, audit fields, period linkage, source/output blob paths, and status lifecycle fields.
- **KPI catalog** (`backend/app/core/kpi_catalog.py`): Added closed Phase A KPI enumeration for the nine portfolio KPIs exposed by analytics, German-locale deterministic formatting, and resolver logic that combines the existing `_csv_kpis()` and `_snapshot_kpis()` helpers for a reporting period.
- **PPTX ingest** (`backend/app/parsers/pptx_ingestor.py`): Added run-level text extraction for text frames and table cells, best-effort font metadata capture, deterministic `{{kpi_id}}` token detection, and separate unknown-token surfacing.
- **PPTX patcher** (`backend/app/core/pptx_patcher.py`): Added single-run token replacement that preserves run formatting by changing only `run.text`; documented the Phase C multi-run token strategy with a TODO.
- **PPTX API** (`backend/app/api/pptx_refresh.py`, `backend/app/main.py`): Added `/api/pptx/upload`, `/api/pptx/{id}`, `/api/pptx/{id}/apply`, and `/api/pptx/{id}/download`. Upload persists source decks under `uploads/pptx_refresh/{id}/source.pptx`, background ingest stores token proposals, apply synchronously resolves/formats KPI values and writes `refreshed.pptx`, and download streams the refreshed deck.
- **Frontend API + page** (`frontend/src/lib/api.ts`, `frontend/src/app/decks/page.tsx`, `frontend/src/app/layout.tsx`): Added typed PPTX refresh client functions, a GARBE-styled deck upload/token review/period selection/download page, draft-period DD-4 warnings, and a `Decks` nav link.
- **Test collection guard** (`backend/pytest.ini`) and `.gitignore`: Restricted backend pytest collection to `tests/` so runtime upload/temp/export folders are not collected on Windows, and ignored backend runtime scratch/upload/log artifacts.

### Test coverage

**258 backend tests passing** (`cd backend && python -m pytest --tb=short -q`) — 243 existing + 15 new RR-1 Phase A tests.

New coverage in `backend/tests/test_pptx_refresh.py`:
- KPI catalog key coverage and deterministic formatting for money, percent, and integer values.
- Synthetic PPTX ingest for text-frame tokens, table-cell tokens, and unknown out-of-catalog tokens.
- Token patching for text frames and table cells, including preservation of surrounding text.
- API upload/status flow, apply completion, draft period status audit capture, unknown KPI error state, and PPTX download response.

Frontend validation:
- `cd frontend && cmd /c npx tsc --noEmit` passed.
- `cmd /c npx next build` was attempted but blocked by the environment's inability to fetch `Open Sans` from Google Fonts via `next/font`; no TypeScript errors were found.

### Files changed

```
.gitignore
backend/pytest.ini
backend/app/models/database.py
backend/app/core/kpi_catalog.py
backend/app/core/pptx_patcher.py
backend/app/parsers/pptx_ingestor.py
backend/app/api/pptx_refresh.py
backend/app/main.py
backend/tests/test_pptx_refresh.py
frontend/src/lib/api.ts
frontend/src/app/decks/page.tsx
frontend/src/app/layout.tsx
planning/Review.md
```

### Codex review findings (2026-05-04, `planning/reviews/codex-review-20260504-220356.md`)

- **[P2] `vacancy_rate` percent unit mismatch** — fixed. `_csv_kpis()` and `_snapshot_kpis()` return `vacancy_rate` already as a percent value (e.g. `5.32` for 5.32%). The original `format_value("percent")` auto-multiplied any input ≤ 1 by 100, so vacancy rates below 1% were inflated 100× (e.g. 0.5% rendered as `50,00 %`). The misleading test `test_format_value_percent` used `0.0532 → "5,32 %"`, which masked the bug. **Fix:** removed the auto-detection from `format_value`; `percent` now unambiguously expects a 0–100 value. Updated existing test to use `5.32 → "5,32 %"` (matching production data flow) and added `test_format_value_percent_below_one` (`0.5 → "0,5 %"`) as a regression guard. Final test count: **259 passing**.

### Deferred items

- Phase B: Claude resolver, scan endpoint, AI proposal review flow, and any Anthropic integration.
- Phase C: chart data refresh, multi-run token repair, group-shape recursion, output-channel push integration, bulk endpoints, comparison slides, and multi-period deck support.
- Trailing-zero stripping on percent (`5.00 %` becomes `5 %`). Cosmetic; revisit if it surfaces in real decks.
- Per-token accept/reject UI on `/decks` page. Phase A auto-applies all detected `{{token}}` placeholders when the user clicks "Refresh deck"; the per-token UI lands with Phase B's proposal review screen (see DD-1 acceptance criterion partial in the RR-1 comment).

### Pickup notes for next session

- RR-1 is **In Arbeit** in Jira with Phase A done. Comment on the ticket lists which acceptance criteria are met vs. deferred.
- Phase A prompt template lives at `planning/codex-rr1-phaseA-prompt.txt` — use as a structural reference when writing the Phase B prompt.
- Phase B scope: `backend/app/core/pptx_kpi_resolver.py` (Claude tool-use), `POST /api/pptx/{id}/scan` endpoint, proposal review screen on `/decks` page, mocked-Anthropic tests. Existing token-mode path must keep working.
- DD-1 (always confirm), DD-2 (no portfolio fallback for ambiguous scope), DD-3 (closed catalog, surface unknowns), DD-4 (draft banner) are anchored in the RR-1 ticket description and must guide Phase B implementation.
- Uncommitted state at handoff: see `git status`. Phase A changes are not yet committed.

Reference: https://banhofmann.atlassian.net/browse/RR-1
