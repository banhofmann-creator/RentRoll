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
