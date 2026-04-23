# Plan: Mieterliste CSV → BVI Target Database Webapp

## 1. Project Overview

Build a web application that:

1. Accepts uploads of the **Mieterliste CSV** (GARBE rent roll format, `;`-delimited, `latin-1` encoded)
2. Stores **all raw data** in a normalized database (no detail loss)
3. Transforms and aggregates the raw data into two BVI-compliant target views:
   - **Z1_Tenants_Leases** — one row per tenant per property (aggregated from unit-level rows)
   - **G2_Property_data** — one row per property per reporting period (aggregated from all units + summary rows), with **144 columns** covering areas, rents by use type (total/let/vacant), lease expiry schedules, ESG metrics, and technical building specs
4. Supports export to `.xlsx` (BVI format), slide generation, and future reporting
5. **Detects and surfaces data inconsistencies** for manual resolution through a guided dialogue workflow
6. Provides an **AI-powered chatbot** that can query, explain, and edit data in the database via natural language

---

## 2. Detailed Specifications (separate files)

Each spec file covers a major topic in full detail. Read them on-demand when working on the relevant phase — they are NOT auto-included in context.

| File | Contents | When to read |
|---|---|---|
| [spec-columns.md](spec-columns.md) | CSV 61-column map, BVI Z1 (10 cols) and G2 (144 cols) target mappings, unit-type → BVI column cross-reference | Phases 1, 4, 5 (parsing, aggregation, export) |
| [spec-schema.md](spec-schema.md) | All database tables: core, mapping/master, inconsistency tracking, chat, audit, snapshots, computed views | Phases 1–5 (any DB work) |
| [spec-transforms.md](spec-transforms.md) | CSV parsing rules, Z1/G2 aggregation logic, USE_TYPE_PRIMARY derivation, validation checks, schema fingerprinting, cross-upload change detection | Phases 1, 2, 4 (parsing, validation, transformation) |
| [spec-architecture.md](spec-architecture.md) | Tech stack, application module tree, background jobs, output channel plugin system, parser plugin system, slide template system, user workflow | All phases (architectural decisions) |
| [spec-features.md](spec-features.md) | BVI XLSX export header structure, external data fields list, inconsistency categories & resolution workflow, AI chatbot architecture & tools, asset base data management (BVI import, editing interfaces, staleness) | Phases 2, 3, 5, 7 (features) |
| [spec-snapshots.md](spec-snapshots.md) | Temporal data model, snapshot-on-finalize lifecycle, what gets snapshotted, time-series SQL examples, finalization guardrails | Phases 5, 6 (periods, history) |
| [spec-design-system.md](spec-design-system.md) | GARBE Industrial color palette, typography, component patterns, layout principles | All frontend work |

---

## 3. Implementation Phases

### Phase 1: Foundation & CSV Ingestion
- **Infrastructure:** PostgreSQL (Docker), FastAPI project scaffold, Next.js frontend scaffold, background job runner (FastAPI BackgroundTasks initially)
- GARBE Mieterliste parser (via parser plugin interface)
- Column schema fingerprinting and drift detection
- Database setup (SQLAlchemy models for all tables including snapshots)
- Upload API endpoint with schema validation
- Row-type classification (data / summary / orphan / total)
- Orphan row fund inheritance (from most recent data row)
- Basic upload UI with job progress tracking

### Phase 2: Inconsistency Detection & Resolution
- Aggregation vs summary row cross-checks
- Unmapped entity detection (tenants, funds, properties)
- Cross-upload diff detection (new/removed tenants, rent changes)
- Inconsistency API (list, filter, resolve, acknowledge, ignore)
- Guided resolution UI with side-by-side comparisons (DiffPreview component)
- Severity-based prioritization (errors block export, warnings don't)

### Phase 3: Mapping UI & Asset Base Data Management
- CRUD API for fund_mapping, tenant_master, property_master
- **BVI G2 importer:** parse existing BVI XLSX → pre-populate property_master
- Mapping UI with unmapped-item highlighting
- Tenant name fuzzy-matching suggestions
- **Asset base data editor:**
  - Completeness dashboard showing fill rates per field group
  - AG Grid inline spreadsheet for multi-property quick edits
  - Single-property detail form with grouped tabs
  - Excel roundtrip: download template → fill offline → re-upload with diff preview
  - Change history / audit log for all edits

### Phase 4: Transformation & Validation
- Z1 aggregation logic
- G2 aggregation logic (all 144 columns):
  - Floor areas (cols 33–46)
  - Rent by use type: total, let, vacant (cols 51–99)
  - Lease expiry schedule (cols 100–112)
  - ESG + tech spec passthrough from property_master (cols 114–142)
  - Reversion computation (col 144)
- USE_TYPE_PRIMARY derivation (75% rule)
- Transform preview UI with full 144-column view

### Phase 5: Reporting Period Management & BVI Export
- **Reporting period lifecycle:** create draft → review → finalize (snapshot) → export
- Snapshot engine: freeze property_master, tenant_master, fund_mapping into snapshot tables on finalization
- XLSX generation with exact header structure (144 columns for G2, 10 columns for Z1)
- Template-driven header blocks (JSON config)
- Export reads from snapshot (finalized) or live tables (draft); draft exports watermarked
- Multi-period support (append to existing BVI file or generate new)
- Download endpoint + local filesystem output channel
- **Re-export** any finalized period from its snapshot
- Finalization guardrails (checklist, completeness threshold, confirmation dialog)

### Phase 6: Time-Series Analysis
- **Cross-period queries** over finalized snapshots
- Period-over-period comparison UI: select two periods, view delta for any metric
- Trend charts (Recharts) for key KPIs (total rent, vacancy rate, fair value, WAULT) across all periods
- Property-level time-series: drill down into a single property's history

### Phase 7: AI Chatbot
- Claude API integration with tool use
- Tool definitions for: querying raw data, querying aggregations, editing master tables, explaining inconsistencies, **cross-period comparisons**
- System prompt with database schema context
- Streaming chat endpoint
- Chat UI (ChatPanel component) with conversation history
- Safety: edits via chatbot require confirmation before committing

### Phase 8: Reporting & Slides
- PPTX template system: master templates with placeholder tokens
- Property factsheet slides
- Fund summary slides
- WAULT analysis / lease expiry profile slides (chart images via matplotlib)
- Dashboard with portfolio KPIs

### Phase 9: Output Channels & Integrations (Future)
- Migrate background jobs to Celery + Redis if concurrent users demand it
- SharePoint / OneDrive output channel (Microsoft Graph API)
- Virtual dataroom channel (Drooms, Box, or generic WebDAV)
- Additional parser plugins for non-GARBE rent roll formats
- Investor reporting packs (combined XLSX + PPTX + PDF bundles per fund)
- Automated scheduled exports (e.g., push BVI to SharePoint on finalization)

---

## 4. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Tenant name variations across CSVs | Broken tenant aggregation | Fuzzy matching + alias table + inconsistency flagging |
| New funds/properties in future CSVs | Unmapped data | Auto-detect & prompt for mapping; inconsistency workflow |
| Rounding differences CSV vs BVI | False validation errors | Allow configurable tolerance (default 2%) |
| Orphan rows (missing fund in col[0]) | Lost data | Inherit fund from most recent data row + flag for review |
| Photovoltaik tenant count ambiguity | Wrong G2 tenant counts | Configurable exclusion rules per tenant type |
| BVI spec changes | Header structure mismatch | Template-driven headers, easy to update |
| CSV column structure changes | Parser breaks silently | Column fingerprinting rejects/warns on schema drift |
| G2 144-column complexity | Incomplete export | Column-by-column test coverage; validate against sample BVI file |
| Master data edits retroactively change past exports | Non-reproducible BVI submissions | Snapshot-on-finalize freezes master data per period |
| Base data entry overhead (40+ fields × 221 properties) | Users skip fields, hollow G2 export | BVI G2 import bootstraps existing data; completeness dashboard + Excel roundtrip |
| AI chatbot hallucinations | Wrong data edits | All edits require explicit user confirmation; audit trail |
