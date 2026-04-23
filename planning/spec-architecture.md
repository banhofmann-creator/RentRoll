# Webapp Architecture

Tech stack, application modules, background jobs, and plugin systems. Referenced from [PLAN.md](PLAN.md).

---

## 1. Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Backend** | **Python / FastAPI** | Native pandas for CSV parsing; openpyxl/python-pptx for Office exports; async endpoints for chat streaming; auto-generated OpenAPI docs |
| **Database** | **PostgreSQL** (dev + prod, via Docker locally) | JSON fields (CRREM floor areas), full-text search (chatbot), robust concurrent access. SQLAlchemy ORM. No SQLite — avoids dev/prod divergence with snapshots and JSON queries. |
| **Frontend** | **Next.js (App Router)** | File-based routing scales as pages grow; server components for data-heavy grids; built-in streaming for chat; easy to add read-only shared views (investor dashboards, export previews) later |
| **Data Grid** | **AG Grid (Community)** | Spreadsheet-like editing for property/tenant master data; clipboard paste, column grouping, inline validation |
| **Charts** | **Recharts** or **Tremor** | Time-series trend charts for the History page and Dashboard |
| **XLSX Export** | **openpyxl** | Generate BVI-compliant XLSX with exact 144-column header structure |
| **Slides** | **python-pptx** + **PPTX template system** | Template-based slide generation: master PPTX files with placeholder tokens, so layouts are editable without code changes. Chart images via matplotlib/plotly embedded in slides. |
| **AI Chatbot** | **Claude API** (Anthropic) | Natural language queries, data editing, explanations; tool_use for structured DB operations |
| **Job Queue** | **Celery + Redis** (or FastAPI `BackgroundTasks` as a stepping stone) | CSV parsing, snapshot creation, XLSX/PPTX generation, and dataroom pushes all take seconds-to-minutes. Running them async with progress tracking avoids HTTP timeouts and lets the UI show real-time status. |
| **Output Channels** | **Plugin interface** | Abstraction layer for pushing generated files to different destinations: local filesystem, SharePoint, Box, Drooms, etc. |

## 2. Application Modules

```
backend/
├── api/
│   ├── upload.py            # CSV upload + parsing + schema validation endpoint
│   ├── transform.py         # Trigger transformation, view results
│   ├── export.py            # XLSX export, slide generation, dataroom push
│   ├── mappings.py          # CRUD for fund/tenant/property master tables
│   ├── master_data.py       # Asset base data: import, export-template, bulk update
│   ├── validation.py        # Data quality checks
│   ├── inconsistencies.py   # CRUD for inconsistency review/resolution
│   ├── periods.py           # Reporting period lifecycle: create, finalize, compare
│   ├── history.py           # Time-series queries across finalized snapshots
│   └── chat.py              # AI chatbot endpoint (streaming)
├── core/
│   ├── csv_parser.py        # Parse GARBE CSV format (encoding, number format, row types)
│   ├── schema_validator.py  # Column fingerprinting + drift detection
│   ├── aggregator.py        # Z1 + G2 aggregation logic (all 144 columns)
│   ├── snapshot_engine.py   # Freeze/read master data snapshots per reporting period
│   ├── validators.py        # Cross-check aggregations vs summary rows
│   ├── inconsistency_detector.py  # Detect & classify data issues
│   ├── use_type.py          # USE_TYPE_PRIMARY derivation (75% rule)
│   ├── lease_expiry.py      # Lease expiry schedule bucketing (cols 100–112)
│   ├── bvi_g2_importer.py   # Import property_master base data from existing BVI G2 XLSX
│   └── master_data_io.py    # Excel roundtrip: generate template, parse filled template
├── chat/
│   ├── agent.py             # Claude-powered chat agent with tool use
│   ├── tools.py             # Tool definitions: query DB, edit records, explain data
│   └── prompts.py           # System prompts with schema context
├── parsers/                 # Source format plugins
│   ├── base.py              # Abstract parser interface: parse(file) → normalized rows
│   └── garbe_mieterliste.py # Current GARBE rent roll parser
├── models/
│   ├── database.py          # SQLAlchemy models for all tables + snapshots
│   └── schemas.py           # Pydantic schemas for API
├── export/
│   ├── bvi_xlsx.py          # Generate BVI-compliant XLSX (144 columns) with header structure
│   ├── slides.py            # Template-based PPTX generation
│   └── templates/           # PPTX master templates with placeholder tokens
├── channels/                # Output channel plugins
│   ├── base.py              # Abstract channel interface: push(files, metadata)
│   ├── local_filesystem.py  # Save to structured folder tree
│   └── sharepoint.py        # (future) Push to SharePoint/OneDrive
├── jobs/
│   ├── tasks.py             # Celery task definitions (parse, snapshot, export, push)
│   └── progress.py          # Progress tracking for long-running jobs
└── config/
    ├── column_schema.json   # Expected CSV column fingerprint
    ├── bvi_g2_template.json # 144-column G2 header template
    └── bvi_z1_template.json # Z1 header template

frontend/                    # Next.js App Router
├── app/
│   ├── upload/              # CSV upload + schema validation status
│   ├── data/                # Browse raw data, summaries, validation warnings
│   ├── mappings/            # Edit fund/tenant/property master tables
│   ├── assets/              # Spreadsheet-like editor for property base data
│   ├── inconsistencies/     # Guided dialogue for resolving data issues
│   ├── transform/           # Preview Z1/G2 output, resolve unmapped items
│   ├── periods/             # Finalize reporting periods, view snapshot history
│   ├── export/              # Download XLSX, generate slides, push to channels
│   ├── history/             # Time-series analysis across finalized periods
│   ├── chat/                # AI chatbot interface
│   └── dashboard/           # Portfolio overview, KPIs
├── components/
│   ├── PropertyGrid.tsx     # AG Grid wrapper for property_master editing
│   ├── TenantGrid.tsx       # AG Grid wrapper for tenant_master editing
│   ├── DiffPreview.tsx      # Side-by-side diff for Excel imports, cross-upload changes
│   ├── TrendChart.tsx       # Recharts time-series component
│   ├── ChatPanel.tsx        # Streaming chat with tool-call display
│   └── JobProgress.tsx      # Real-time progress bar for background tasks
└── lib/
    └── api.ts               # Typed API client (generated from OpenAPI spec)
```

## 3. Background Jobs & Progress Tracking

Several operations are too slow for synchronous HTTP requests:

| Operation | Typical Duration | Trigger |
|---|---|---|
| CSV parse + store | 2–10s (3,500 rows) | Upload |
| Inconsistency detection | 1–5s | Post-upload |
| Snapshot creation | 1–3s (~1,200 rows copied) | Finalize period |
| BVI XLSX generation | 5–15s (144 cols × 221 rows + headers) | Export |
| Slide generation | 5–30s (depends on property count) | Export |
| Dataroom push | 10s–5min (depends on target system) | Export |

**Architecture:**

```
Frontend                    Backend (FastAPI)              Worker (Celery)
   │                             │                             │
   ├─ POST /api/upload ─────────►│                             │
   │                             ├─ create job ────────────────►│
   │◄── 202 {job_id} ───────────┤                             │
   │                             │                             ├─ parse CSV
   ├─ GET /api/jobs/{id} ──────►│◄── progress updates ────────┤
   │◄── {status, progress, …} ──┤                             │
   │  (poll or SSE stream)       │                             ├─ done
   │                             │                             │
```

- Jobs are tracked in a `jobs` table with status (`queued`, `running`, `completed`, `failed`), progress percentage, and result payload
- The frontend shows a `JobProgress` component with real-time updates (via SSE or polling)
- Failed jobs surface the error in the UI with retry option
- **Stepping stone:** Start with FastAPI's `BackgroundTasks` for simplicity. Migrate to Celery + Redis when concurrent users or longer-running jobs (dataroom pushes) demand it.

## 4. Output Channels (Plugin System)

Generated files (XLSX, PPTX, PDFs) need to go somewhere. Today that's a browser download, but the roadmap includes dataroom feeds, SharePoint, and potentially investor portals.

**Interface:**

```python
class OutputChannel(ABC):
    @abstractmethod
    def push(self, files: list[ExportFile], metadata: ExportMetadata) -> PushResult:
        """Push generated files to the destination."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify credentials and connectivity."""

@dataclass
class ExportFile:
    filename: str          # e.g., "BVI_GLIF3_2025-Q3.xlsx"
    content: bytes
    file_type: str         # 'xlsx' | 'pptx' | 'pdf'
    category: str          # 'bvi_export' | 'slide_deck' | 'factsheet'

@dataclass
class ExportMetadata:
    stichtag: date
    fund: str
    properties: list[int]  # Property IDs included
    reporting_period_id: int
```

**Built-in channels:**

| Channel | Description | Status |
|---|---|---|
| `LocalFilesystem` | Save to structured folder: `exports/{fund}/{stichtag}/` | Phase 5 |
| `BrowserDownload` | Direct download via API response | Phase 5 |
| `SharePoint` | Push to SharePoint/OneDrive via Microsoft Graph API | Future |
| `Drooms` / `Box` | Virtual dataroom integration | Future |

## 5. Parser Plugin System

**Interface:**

```python
class RentRollParser(ABC):
    name: str              # e.g., "GARBE Mieterliste"
    file_types: list[str]  # e.g., [".csv"]

    @abstractmethod
    def detect(self, file: UploadedFile) -> float:
        """Return confidence 0–1 that this parser handles the file."""

    @abstractmethod
    def extract_metadata(self, file: UploadedFile) -> ParseMetadata:
        """Extract stichtag, fund label, column headers without full parse."""

    @abstractmethod
    def parse(self, file: UploadedFile) -> ParseResult:
        """Full parse → list of normalized RentRollRow objects."""
```

- On upload, the system runs `detect()` on all registered parsers and picks the highest-confidence match
- If no parser matches with confidence > 0.8, the user is prompted to select manually
- New parsers are added as Python modules in `backend/parsers/` — no changes to the rest of the system

## 6. Slide Template System

Slides are generated from **PPTX master templates** rather than code-constructed layouts:

```
backend/export/templates/
├── property_factsheet.pptx    # Single-property overview (1–2 slides)
├── fund_summary.pptx          # Fund-level KPIs + property table
├── portfolio_overview.pptx    # Full portfolio dashboard
└── lease_expiry_profile.pptx  # Lease expiry waterfall chart
```

Each template contains **placeholder tokens** in text boxes:

```
{{property_name}}          → "Rheinberg"
{{rentable_area}}          → "22,303 m²"
{{vacancy_rate}}           → "0.0%"
{{annual_rent}}            → "€1,274,884"
{{wault}}                  → "3.6 years"
{{use_type_primary}}       → "INDUSTRY"
{{chart:lease_expiry}}     → Replaced with matplotlib chart image
{{table:tenant_list}}      → Replaced with formatted table
```

## 7. User Workflow

```
1. UPLOAD
   └─ CSV → parser validates schema → extracts data → auto-detects inconsistencies

2. REVIEW INCONSISTENCIES
   └─ Guided resolution grouped by severity (errors → warnings → info)

3. MAP & EDIT BASE DATA
   └─ Unmapped tenants/funds → assign IDs. Property metadata via grid/form/Excel roundtrip.

4. TRANSFORM
   └─ Generate Z1 + G2 views (144 cols). Preview side-by-side.

5. FINALIZE & EXPORT
   └─ Snapshot master data → download BVI XLSX → generate slides → push to channels.

6. HISTORICAL ANALYSIS
   └─ Compare metrics across finalized periods. Trend charts.

7. CHAT (available at any step)
   └─ Natural-language queries, data editing, explanations.
```
