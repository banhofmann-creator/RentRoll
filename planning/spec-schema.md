# Database Schema

All table definitions for the RentRoll application. Referenced from [PLAN.md](PLAN.md).

---

## Design Principles

- Store **all raw CSV data** losslessly in normalized tables
- Maintain **mapping/master tables** for data not in the CSV (tenant IDs, NACE sectors, property metadata)
- Generate BVI target views via **SQL views or query logic**, not by duplicating data
- Support **multiple reporting dates** (Stichtag) for time-series analysis
- **Preserve historical state** via reporting-period snapshots: raw CSV data is retained per upload; master data (property, tenant, fund) is frozen into a snapshot when a reporting period is finalized, enabling reproducible exports and time-series analysis across all fields
- Track **data inconsistencies** with resolution status for manual review workflow
- Store **column schema fingerprints** to detect CSV structural changes

## 1. Core Tables

```
┌──────────────────────────┐
│ csv_uploads              │  Track uploaded files
├──────────────────────────┤
│ id (PK)                  │
│ filename                 │
│ upload_date              │
│ stichtag (reporting_date)│
│ fund_label               │  ("1 - GARBE")
│ status                   │  (processing, complete, error)
│ row_count                │
│ column_fingerprint       │  Hash of column headers for schema validation
│ column_headers_json      │  Actual headers as JSON (for diff on mismatch)
│ parser_warnings_json     │  Any warnings from parsing (orphan rows, number format issues)
└──────────────────────────┘

┌──────────────────────────┐
│ raw_rent_roll            │  ALL data rows from CSV, 1:1
├──────────────────────────┤
│ id (PK)                  │
│ upload_id (FK)           │
│ row_number               │  Original CSV row position
│ row_type                 │  'data' | 'property_summary' | 'orphan' | 'total'
│ fund                     │  col[0] — fund identifier (for orphan rows: inherited value)
│ fund_inherited           │  Boolean — TRUE if fund was inherited for orphan row
│ property_id              │  col[1] — numeric property ID
│ property_name            │  col[2] — property description
│ garbe_office             │  col[3] — regional office
│ unit_id                  │  col[5] — rental unit ID
│ unit_type                │  col[6] — Art (Halle, Büro, etc.)
│ floor                    │  col[7] — Stockwerk
│ parking_count            │  col[8] — integer
│ area_sqm                 │  col[9] — numeric (after stripping ')
│ lease_id                 │  col[11]
│ tenant_name              │  col[12]
│ lease_start              │  col[13] — date
│ lease_end_agreed         │  col[14] — date
│ lease_end_termination    │  col[15] — date
│ lease_end_actual         │  col[16] — date
│ special_termination_notice│ col[17]
│ special_termination_date │  col[18]
│ notice_period            │  col[19]
│ notice_date              │  col[20]
│ option_duration_months   │  col[21] — integer
│ option_exercise_deadline │  col[22] — date
│ lease_end_after_option   │  col[23] — date
│ additional_options       │  col[24] — integer
│ max_lease_term           │  col[25]
│ wault                    │  col[26] — numeric (years)
│ waulb                    │  col[27] — numeric (years)
│ waule                    │  col[28] — numeric (years)
│ annual_net_rent          │  col[30] — numeric
│ monthly_net_rent         │  col[31] — numeric
│ investment_rent          │  col[32] — numeric
│ rent_free_end            │  col[33] — date
│ rent_free_amount         │  col[34] — numeric
│ market_rent_monthly      │  col[35] — numeric
│ erv_monthly              │  col[36] — numeric
│ reversion_potential_pct  │  col[37] — numeric (%)
│ net_rent_per_sqm_pa      │  col[38] — numeric
│ market_rent_per_sqm_pa   │  col[39] — numeric
│ erv_per_sqm_pa           │  col[40] — numeric
│ service_charge_advance   │  col[42] — numeric
│ service_charge_lumpsum   │  col[43] — numeric
│ sc_advance_per_sqm_pa    │  col[44] — numeric
│ sc_lumpsum_per_sqm_pa    │  col[45] — numeric
│ total_gross_rent_monthly │  col[46] — numeric
│ total_gross_rent_per_sqm │  col[47] — numeric
│ vat_liable               │  col[48] — text/boolean
│ pct_rent_increase        │  col[50] — boolean
│ increase_percentage      │  col[51] — numeric
│ next_increase_date       │  col[52] — date
│ escalation_cycles        │  col[53] — text
│ index_escalation         │  col[55] — boolean
│ index_type               │  col[56] — text
│ threshold                │  col[57] — text
│ index_ref_date           │  col[58] — date
│ passthrough_pct          │  col[59] — numeric (%)
│ green_lease              │  col[60] — integer (0/1)
└──────────────────────────┘
```

## 2. Mapping / Master Tables (manually maintained, UI-editable)

```
┌──────────────────────────┐
│ fund_mapping             │  CSV fund name → BVI fund ID
├──────────────────────────┤
│ id (PK)                  │
│ csv_fund_name            │  e.g., "GLIFPLUSIII"
│ bvi_fund_id              │  e.g., "GLIF3LUF"
│ description              │
└──────────────────────────┘

┌──────────────────────────┐
│ tenant_master            │  Canonical tenant registry
├──────────────────────────┤
│ id (PK)                  │
│ bvi_tenant_id            │  e.g., "C04.000858" (UNIQUE)
│ tenant_name_canonical    │  Official name
│ nace_sector              │  e.g., "MANUFACTURING"
│ pd_min                   │  Probability of default min (decimal, e.g., 0.0075)
│ pd_max                   │  Probability of default max (decimal)
│ notes                    │
└──────────────────────────┘

┌──────────────────────────┐
│ tenant_name_alias        │  Fuzzy name matching
├──────────────────────────┤
│ id (PK)                  │
│ tenant_master_id (FK)    │
│ csv_tenant_name          │  As it appears in CSV (exact match key)
│ property_id              │  Scoped to property (same name, different entity)
└──────────────────────────┘

┌──────────────────────────┐
│ property_master          │  Property-level metadata not in CSV
├──────────────────────────┤
│ id (PK)                  │
│ property_id              │  Numeric ID from CSV col[1]
│ fund_csv_name            │  Fund association
│ predecessor_id           │  Hierarchical predecessor (e.g., "GLIF3LU12")
│ prop_state               │  HELD_PROPERTY | DEVELOPMENT | LAND
│ ownership_type           │  DIRECT | INDIRECT
│ land_ownership           │  Freehold | Leasehold
│ country                  │  ISO 3166 Alpha-2
│ region                   │  Regional classification
│ zip_code                 │
│ city                     │
│ street                   │
│ location_quality         │  1A, 1B, 2A, 2B, 3A, 3B
│ green_building_vendor    │  DGNB, BREEAM, etc.
│ green_building_cert      │  Gold, Very good, etc.
│ green_building_from      │  Date
│ green_building_to        │  Date
│ ownership_share          │  Decimal 0–1
│ purchase_date            │  Date
│ construction_year        │  Integer
│ risk_style               │  CORE, CORE_PLUS, VALUE_ADDED, OPPORTUNISTIC
│ fair_value               │  Numeric
│ market_net_yield         │  Numeric (decimal)
│ last_valuation_date      │  Date
│ next_valuation_date      │  Date
│ plot_size_sqm            │  Numeric
│ debt_property            │  Numeric
│ shareholder_loan         │  Numeric
│ — ESG / Sustainability fields —
│ co2_emissions            │  kg CO2/m²/year
│ co2_measurement_year     │  Integer
│ energy_intensity         │  kWh/m²/year
│ energy_intensity_normalised│ Numeric
│ data_quality_energy      │  COLLECTED_DATA | NOT_AVAILABLE | etc.
│ energy_reference_area    │  m²
│ crrem_floor_areas_json   │  JSON: {office: 0.03, industrial: 0.97, ...}
│ exposure_fossil_fuels    │  Numeric
│ exposure_energy_inefficiency│ Numeric
│ waste_total              │  Tonnes
│ waste_recycled_pct       │  Decimal
│ epc_rating               │  Text (A+++ through G)
│ — Technical Specifications —
│ tech_clear_height        │  Numeric (m)
│ tech_floor_load_capacity │  Numeric
│ tech_loading_docks       │  Integer
│ tech_sprinkler           │  Text/Boolean
│ tech_lighting            │  Text
│ tech_heating             │  Text
│ maintenance              │  Text
└──────────────────────────┘
```

## 3. Inconsistency Tracking Table

```
┌──────────────────────────┐
│ data_inconsistencies     │  Track detected issues for manual review
├──────────────────────────┤
│ id (PK)                  │
│ upload_id (FK)           │
│ category                 │  'aggregation_mismatch' | 'unmapped_tenant' | 'unmapped_fund' |
│                          │  'orphan_row' | 'name_variation' | 'schema_drift' |
│                          │  'missing_metadata' | 'cross_upload_change'
│ severity                 │  'error' | 'warning' | 'info'
│ entity_type              │  'property' | 'tenant' | 'fund' | 'row'
│ entity_id                │  Property ID, tenant name, etc.
│ field_name               │  Specific field with issue (if applicable)
│ expected_value           │  What was expected (e.g., summary row total)
│ actual_value             │  What was found (e.g., computed aggregate)
│ deviation_pct            │  Percentage deviation (for numeric mismatches)
│ description              │  Human-readable description of the issue
│ status                   │  'open' | 'acknowledged' | 'resolved' | 'ignored'
│ resolution_note          │  User's explanation when resolving/ignoring
│ resolved_by              │  Username
│ resolved_at              │  Timestamp
│ created_at               │  Timestamp
└──────────────────────────┘
```

## 4. Chat History Table

```
┌──────────────────────────┐
│ chat_sessions            │  AI chatbot conversation sessions
├──────────────────────────┤
│ id (PK)                  │
│ user_id                  │
│ title                    │  Auto-generated or user-set title
│ created_at               │
│ last_message_at          │
└──────────────────────────┘

┌──────────────────────────┐
│ chat_messages            │  Individual messages in a chat session
├──────────────────────────┤
│ id (PK)                  │
│ session_id (FK)          │
│ role                     │  'user' | 'assistant' | 'system'
│ content                  │  Message text
│ tool_calls_json          │  Any SQL queries or edits the assistant executed
│ created_at               │
└──────────────────────────┘
```

## 5. Master Data Audit Table

```
┌──────────────────────────┐
│ master_data_audit        │  Change history for all master data edits
├──────────────────────────┤
│ id (PK)                  │
│ table_name               │  'property_master' | 'tenant_master' | 'fund_mapping'
│ record_id                │  PK of the edited record
│ field_name               │  Which field changed
│ old_value                │  Previous value (as text)
│ new_value                │  New value (as text)
│ change_source            │  'form' | 'grid' | 'excel_import' | 'bvi_import' | 'chatbot'
│ changed_by               │  Username
│ changed_at               │  Timestamp
│ session_id               │  Chat session ID (if change_source = 'chatbot')
└──────────────────────────┘
```

## 6. Reporting Period Snapshots

```
┌───────────────────────────────┐
│ reporting_periods             │  One row per finalized reporting period
├───────────────────────────────┤
│ id (PK)                       │
│ stichtag                      │  Reporting date (e.g., 2025-03-31). UNIQUE.
│ upload_id (FK)                │  Which csv_upload this period is based on
│ status                        │  'draft' | 'finalized' | 'superseded'
│ finalized_by                  │  Username who finalized
│ finalized_at                  │  Timestamp
│ notes                         │  User notes (e.g., "Q1 2025 BVI submission")
│ created_at                    │
└───────────────────────────────┘

┌───────────────────────────────┐
│ snapshot_property_master      │  Frozen copy of property_master at finalization
├───────────────────────────────┤
│ id (PK)                       │
│ reporting_period_id (FK)      │
│ property_id                   │  — all fields identical to property_master —
│ fund_csv_name                 │
│ predecessor_id                │
│ ... (all ~40 fields)          │  Full copy, no foreign keys back to live table
│ maintenance                   │
└───────────────────────────────┘

┌───────────────────────────────┐
│ snapshot_tenant_master        │  Frozen copy of tenant_master at finalization
├───────────────────────────────┤
│ id (PK)                       │
│ reporting_period_id (FK)      │
│ bvi_tenant_id                 │  — all fields identical to tenant_master —
│ tenant_name_canonical         │
│ nace_sector                   │
│ pd_min                        │
│ pd_max                        │
│ notes                         │
└───────────────────────────────┘

┌───────────────────────────────┐
│ snapshot_tenant_name_alias    │  Frozen copy of alias mappings
├───────────────────────────────┤
│ id (PK)                       │
│ reporting_period_id (FK)      │
│ snapshot_tenant_master_id (FK)│
│ csv_tenant_name               │
│ property_id                   │
└───────────────────────────────┘

┌───────────────────────────────┐
│ snapshot_fund_mapping         │  Frozen copy of fund_mapping
├───────────────────────────────┤
│ id (PK)                       │
│ reporting_period_id (FK)      │
│ csv_fund_name                 │
│ bvi_fund_id                   │
│ description                   │
└───────────────────────────────┘
```

## 7. Computed Views (SQL or application logic)

The views accept a `reporting_period_id` parameter. For **draft** periods they join the live master tables; for **finalized** periods they join the snapshot tables. This ensures finalized exports are reproducible even after master data has been edited for a later period.

```
┌─────────────────────────────────┐
│ VIEW: v_z1_tenants_leases       │  Generates Z1 output
├─────────────────────────────────┤
│ Parameters: reporting_period_id │
│ SELECT                          │
│   fm.bvi_fund_id,               │  Fund mapping (live or snapshot)
│   u.stichtag,                   │  From upload
│   'EUR',                        │  Constant
│   tm.bvi_tenant_id,             │  From tenant master via alias (live or snapshot)
│   r.property_id,                │  Acts as DUNS_ID
│   tm.tenant_name_canonical,     │  Label
│   tm.nace_sector,               │  Sector
│   tm.pd_min, tm.pd_max,        │  Risk
│   SUM(r.annual_net_rent)        │  Aggregated rent
│ FROM raw_rent_roll r            │
│ JOIN csv_uploads u ON r.upload_id = u.id
│ JOIN reporting_periods rp ON rp.upload_id = u.id
│ JOIN (live OR snapshot) fm, tm  │  ← based on rp.status
│ GROUP BY fund, property_id, tenant
│ WHERE tenant_name != 'LEERSTAND'│
│   AND row_type = 'data'         │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ VIEW: v_g2_property_data        │  Generates G2 output (144 columns)
├─────────────────────────────────┤
│ Parameters: reporting_period_id │
│ Aggregates from raw_rent_roll:  │
│ — Floor areas (cols 33–46) —    │
│ - SUM(area) by unit_type        │
│ - SUM(parking_count)            │
│ - COUNT(DISTINCT tenant) excl LEERSTAND
│ - SUM(area) WHERE let           │
│ — Rent by type (cols 51–65) —   │
│ - SUM(annual_net_rent) by unit_type
│ — ERV by type (cols 66–77) —    │
│ - SUM(erv_monthly) × 12 by unit_type
│ — Rent-let (cols 78–88) —       │
│ - Same as rent by type, WHERE non-LEERSTAND
│ — Rent-vacant (cols 89–99) —    │
│ - SUM(market_rent × 12) WHERE LEERSTAND, by type
│ — Lease expiry (cols 100–112) — │
│ - Bucket annual_net_rent by lease_end_actual year
│ — From summary row —            │
│ - Market rental value (col 35 × 12)
│ - WAULT (col 26)                │
│ Joins property_master OR        │
│   snapshot_property_master for:  │  ← based on rp.status
│ - All external metadata fields  │
│ - ESG, technical specs          │
│ Joins fund_mapping OR           │
│   snapshot_fund_mapping for:     │  ← based on rp.status
│ - BVI fund ID                   │
│ Derives:                        │
│ - USE_TYPE_PRIMARY (75% rule)   │
│ - rent / sqm (col 52)          │
│ - Reversion (col 144)          │
└─────────────────────────────────┘
```
