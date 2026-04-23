# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RentRoll transforms GARBE-format Mieterliste CSV files (`;`-delimited, `latin-1`, 61 columns, apostrophe thousands separators) into BVI-compliant XLSX exports with two sheets: Z1_Tenants_Leases (10 columns, one row per tenant per property) and G2_Property_data (144 columns, one row per property per reporting period). The full specification is in `planning/PLAN.md`.

## Architecture

**Backend:** Python/FastAPI in `backend/`. **Frontend:** Next.js App Router in `frontend/`. **Database:** PostgreSQL (Docker), SQLAlchemy ORM.

Key architectural concepts:
- **Parser plugin system** (`backend/parsers/`): each source format implements `detect()`, `extract_metadata()`, `parse()`. Currently only GARBE Mieterliste. The parser normalizes rows into `raw_rent_roll` records.
- **Reporting period snapshots** (`reporting_periods` + `snapshot_*` tables): master data (property, tenant, fund) is frozen when a period is finalized. Computed views join live tables for drafts, snapshot tables for finalized periods. This ensures reproducible exports.
- **Background jobs**: long-running operations (CSV parse, XLSX export, snapshot creation) run async via FastAPI BackgroundTasks (later Celery). Frontend polls for progress.
- **Output channel plugins** (`backend/channels/`): abstract `push(files, metadata)` interface for export destinations.

Data flow: CSV upload → parse + store in `raw_rent_roll` → detect inconsistencies → user maps tenants/funds/properties → aggregate into Z1/G2 views → finalize period (snapshot) → export XLSX.

## Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Database (Docker)
docker compose up -d postgres

# Tests
cd backend
pytest                          # all tests
pytest tests/test_parser.py     # single file
pytest -k "test_orphan"         # by name pattern
pytest --tb=short -q            # compact output

# Frontend tests
cd frontend
npm test
```

## Collaboration Workflow

Use this file as the shared repo contract across coding agents. Keep durable project rules here, and keep task-specific intent in the active prompt.

Recommended split when multiple agents are involved:
- Claude Code: shape the approach, handle repo-native workflows, and implement when appropriate.
- Codex: perform focused review, run targeted validation, inspect diffs for regressions, and handle precise follow-up fixes.

When Claude Code completes a non-trivial change, explicitly call on Codex for review before treating the work as done. That review should focus on:
- behavioral regressions
- edge cases and missing validation
- tests that should be added or updated
- multi-file consistency with the architecture and domain rules in this file

When both agents are used in the same task:
- avoid editing the same files concurrently unless ownership is explicit
- keep one agent in implementation mode and the other in review mode
- record any durable workflow changes back into this file rather than only in chat

### Plan/Review Status Baseline (as of 2026-04-23)

- `planning/PLAN.md` is the target blueprint and phase definition (Phases 1-9).
- `planning/Review.md` is the execution log. It currently marks:
  - `Phase 1: Foundation & CSV Ingestion` as `Complete` (dated 2026-04-23)
  - `Design System: GARBE Industrial Branding` as `Complete` (dated 2026-04-23)
- Treat phases 2-9 as not yet complete unless `planning/Review.md` says otherwise.

### Post-Codex Review Checklist (Claude Code)

After Codex completes a change, Claude Code should review and confirm:
- The change maps to one or more explicit bullets in the relevant phase in `planning/PLAN.md`.
- `planning/Review.md` is updated with status, date, changed files, and validation/test evidence for the phase work that was done.
- Domain-rule compliance for CSV handling and aggregations in this file (orphan inheritance, LEERSTAND handling, PV handling, USE_TYPE_PRIMARY logic, lease-expiry bucketing).
- Snapshot/reporting-period behavior is preserved when touching export or historical data paths.
- Tests are added/updated for behavior changes, and commands/results are recorded in the review notes.
- Remaining gaps are listed as concrete follow-up items tied to a PLAN.md phase.

### Automatic Handoff Command (Claude Code -> Codex)

After non-trivial code changes are applied, run:

```bash
cmd /c .claude\codex-post-change-review.cmd
```

Behavior:
- Skips review when there are no uncommitted changes.
- Runs `codex review --uncommitted`.
- Writes a timestamped review report to `planning/reviews/codex-review-YYYYMMDD-HHMMSS.md`.

Review focus guidance is maintained in `.claude/codex-review-prompt.txt` for Claude/Codex handoff consistency, even though this Codex CLI path does not accept a custom prompt together with `--uncommitted`.

Claude Code should treat this handoff as required before declaring implementation complete.

## CSV Parsing Rules

The GARBE CSV has 10 header rows before data. Row types are classified by `col[0]`:
- **Data rows**: `col[0]` matches a known fund name (e.g., `GLIF`, `GLIFPLUSII`)
- **Summary rows**: `col[0]` matches `^\d{2,4}\s*-\s*` (e.g., `"7042 - Almere, ..."`)
- **Orphan rows**: `col[0]` is empty but `col[1]` has a property_id → inherit fund from **most recent data row above** (not same property_id — orphans have new property IDs)
- **Total row**: `col[0]` starts with `"Total"`

Numbers use `'` (apostrophe) as thousands separator — strip before parsing. Dates are `dd.mm.yyyy`. Booleans are `"true"`/`"false"` strings. Percentages are strings like `"37.9%"`.

## Key Domain Rules

- `LEERSTAND` = vacancy. Excluded from tenant counts and Z1 export, but included in rentable area and vacant-rent breakdowns.
- `USE_TYPE_PRIMARY`: if one unit type ≥75% of total area → that type; else if only one type >25% → largest; else `MISCELLANEOUS`.
- G2 lease expiry bucketing: `year(lease_end) - year(stichtag)` → bucket 0–9, or 10 for 10+ years, or open-ended if no end date.
- Photovoltaik tenants (41 rows): type `Sonstige`, zero area. Included in Z1, configurable exclusion from G2 tenant counts.

## Testing

Test everything. If errors occur, reproduce and fix until tests come back clean. Sample data files are in `samples/` for use in tests.

@planning/PLAN.md
