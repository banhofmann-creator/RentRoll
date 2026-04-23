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
