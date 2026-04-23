# Feature Specifications

BVI export, external data fields, inconsistency resolution, AI chatbot, and asset base data management. Referenced from [PLAN.md](PLAN.md).

---

## 1. BVI XLSX Export Generation

The output XLSX must replicate the exact structure of `BVI_Target_Tables.xlsx`:

- **Row 1:** Empty
- **Row 2:** Module title + reporting date (e.g., `"Range 2: Property data"` + date at col 6)
- **Row 3:** Section subtitle
- **Row 4:** BVI field codes (COMPANY.OBJECT_ID_SENDER, etc.)
- **Row 5:** BVI numeric codes (102, 101, 100, etc.)
- **Row 6:** Field descriptions (long text)
- **Row 7:** Data types (Alpha-numerical, Date, Text, Numerical, Coding)
- **Row 8:** Example values
- **Row 9:** Empty
- **Row 10:** Category group headers (Data set, Currency, ID and WE status, Address, Percentage, Acquisition date, Allocation data, Survey, Floor area, Parking spots, Debt capital and SL, Contract and target rents, Rent by use type, Rent-let, Rent-vacant, Expiring leases, Number of tenants, Sustainability)
- **Row 11:** Human-readable column labels
- **Row 12+:** Data

Store the static header template as a JSON/YAML config so it can be version-controlled independently. The G2 template must cover all 144 columns.

**Snapshot-based export:** The export always reads from a **finalized reporting period**. This guarantees that re-exporting a past period produces identical output, even if master data has since been edited for a later period. Draft (not yet finalized) periods can also be exported for preview, but those pull from live master data and are marked as provisional.

---

## 2. Data Fields Requiring External Input

These fields **cannot** be derived from the CSV and must be maintained manually or imported from external sources:

### Per Tenant (tenant_master)
- `bvi_tenant_id` — BVI-internal reference ID (format: `C{nn}.{nnnnnn}` or `F{nn}.{nnnnnn}`)
- `nace_sector` — NACE Rev. 2 classification (e.g., `MANUFACTURING`, `TRANSPORTATION_STORAGE`)
- `pd_min` / `pd_max` — Probability of default (decimal, e.g., `0.0075`)

### Per Property (property_master)

**Core fields:** `predecessor_id`, `prop_state`, `ownership_type`, `land_ownership`, `country`, `region`, `zip`, `city`, `street`, `location_quality`, `green_building_*` (4 fields), `ownership_share`, `purchase_date`, `construction_year`, `risk_style`, `fair_value`, `market_net_yield`, `last_valuation_date`, `next_valuation_date`, `plot_size_sqm`, `debt_property`, `shareholder_loan`

**ESG / Sustainability fields (G2 cols 114–135):** `co2_emissions`, `co2_measurement_year`, `energy_intensity`, `energy_intensity_normalised`, `data_quality_energy`, `energy_reference_area`, `crrem_floor_areas` (JSON), `exposure_fossil_fuels`, `exposure_energy_inefficiency`, `waste_total`, `waste_recycled_pct`, `epc_rating`

**Technical specifications (G2 cols 136–142):** `tech_clear_height`, `tech_floor_load_capacity`, `tech_loading_docks`, `tech_sprinkler`, `tech_lighting`, `tech_heating`, `maintenance`

### Per Fund (fund_mapping)
- `bvi_fund_id` — BVI fund identifier

**Recommended:** Pre-populate the `property_master` table from the existing BVI target data (G2 sheet) using the BVI G2 importer, then only require updates going forward.

---

## 3. Inconsistency Detection & Manual Resolution

### 3.1 Inconsistency Categories

| Category | Trigger | Severity | Auto-detectable |
|---|---|---|---|
| `aggregation_mismatch` | Computed aggregate differs from summary row by >1% | warning | Yes |
| `unmapped_tenant` | Tenant name in CSV has no alias in tenant_name_alias | error | Yes |
| `unmapped_fund` | Fund name in CSV has no entry in fund_mapping | error | Yes |
| `orphan_row` | Row with empty fund was assigned an inherited fund | info | Yes |
| `name_variation` | Tenant name differs slightly from canonical name (fuzzy match >80%) | warning | Yes |
| `schema_drift` | Column headers don't match expected fingerprint | error | Yes |
| `missing_metadata` | Property in CSV has no/incomplete property_master record | warning | Yes |
| `cross_upload_change` | Significant difference vs previous upload for same fund | info | Yes |
| `manual_flag` | User or chatbot flags a data point as suspicious | warning | No |

### 3.2 Resolution Workflow

1. **Issue display:** Shows the inconsistency with full context (raw data, computed values, related records)
2. **Suggested action:** System proposes a resolution based on the category
3. **User decision:** Resolve, acknowledge (accept as-is with note), or ignore
4. **Audit trail:** All resolutions are recorded with user, timestamp, and notes
5. **Export gate:** Configurable — errors can block export until resolved; warnings allow export with flag

### 3.3 Dialogue Support

- **Drill-down:** Click an aggregation mismatch → see all contributing rows with individual values
- **Batch operations:** Select multiple similar issues and resolve together
- **AI assist:** "Ask the chatbot" button that pre-fills the chat with context about the inconsistency

---

## 4. AI Chatbot

### 4.1 Purpose

An integrated AI chatbot (powered by Claude) that can:
- **Query data:** Answer natural-language questions about the rent roll, aggregations, or BVI output
- **Edit data:** Update master tables (tenant, property, fund mappings) via conversational commands
- **Explain:** Describe transformation logic, highlight why certain values differ, trace data lineage
- **Investigate inconsistencies:** Help users understand and resolve flagged data issues

### 4.2 Architecture

```
User message → FastAPI /api/chat endpoint
  → Build system prompt (includes DB schema, current data summary)
  → Call Claude API with tool_use
  → Tools available to the model:
      ├── query_raw_data(sql_filter) → Read from raw_rent_roll with filters
      ├── query_aggregation(property_id, metric) → Run aggregation query
      ├── query_bvi_preview(sheet, property_id) → Show transformed output
      ├── search_tenants(name_pattern) → Search tenant_master + aliases
      ├── update_tenant(tenant_id, field, value) → Edit tenant_master (requires confirmation)
      ├── update_property(property_id, field, value) → Edit property_master (requires confirmation)
      ├── update_fund_mapping(fund_name, bvi_id) → Edit fund_mapping (requires confirmation)
      ├── list_inconsistencies(filters) → Show open data issues
      ├── resolve_inconsistency(id, resolution, note) → Resolve an issue (requires confirmation)
      ├── explain_transformation(property_id, field) → Trace how a BVI field value was derived
      ├── list_periods() → Show all finalized reporting periods
      └── compare_periods(period_a, period_b, metric, scope) → Cross-period delta for any metric
  → Stream response back to frontend
```

### 4.3 Safety Guardrails

- **Read queries** execute immediately
- **Write operations** require explicit user confirmation via a UI modal
- All chatbot actions are logged in `chat_messages.tool_calls_json` for audit
- The chatbot cannot delete records, only update or create
- SQL injection prevention: parameterized queries, never raw SQL
- Rate limiting on write operations

---

## 5. Asset Base Data Management

### 5.1 The Problem

The G2 target sheet has 144 columns. Roughly half (~70 columns) are **derivable** from the CSV through aggregation. The other half must come from **property_master**, which needs to be populated and kept current for 221+ properties.

### 5.2 Bootstrap: BVI G2 Import

Most of this data already exists in the current BVI target file. A one-time importer reads the G2 sheet and populates property_master:

```
BVI_Target_Tables.xlsx (G2 sheet)
  → For each data row with a non-empty property_id:
      → Map G2 columns back to property_master fields:
          col 6  (predecessor ID)     → predecessor_id
          col 8  (PROP_STATE)         → prop_state
          col 9  (ownership type)     → ownership_type
          col 10 (land ownership)     → land_ownership
          col 11–15 (address)         → country, region, zip_code, city, street
          col 16 (location quality)   → location_quality
          col 17–20 (green building)  → green_building_*
          col 21 (ownership share)    → ownership_share
          col 22 (purchase date)      → purchase_date
          col 23 (construction year)  → construction_year
          col 25 (risk style)         → risk_style
          col 26 (fair value)         → fair_value
          col 28 (market net yield)   → market_net_yield
          col 29–30 (valuation dates) → last/next_valuation_date
          col 32 (plot size)          → plot_size_sqm
          col 49–50 (debt/SL)        → debt_property, shareholder_loan
          col 114–135 (ESG)          → co2_*, energy_*, crrem_*, waste_*, epc_rating
          col 136–142 (tech specs)   → tech_*, maintenance
      → Upsert on property_id
```

**Import modes:** Initial bootstrap (overwrite all) | Fill gaps only (NULL fields) | Selective update (pick field groups)

### 5.3 Editing Interfaces

Four ways to edit property base data:

1. **Completeness Dashboard** — entry point showing fill rates per field group
2. **Inline Spreadsheet Grid** — AG Grid with column group tabs, inline editing, bulk paste, diff highlight
3. **Single-Property Detail Form** — tabbed form with CSV-derived read-only values alongside editable fields, change history, staleness indicators
4. **Excel Roundtrip** — download template → fill offline → re-upload with diff preview and conflict handling

### 5.4 Tenant Base Data Editing

Same patterns as property_master at smaller scale (~480 tenants): grid, detail view, Excel roundtrip, NACE auto-suggest based on fuzzy matching and keyword matching.

### 5.5 Change Tracking & Audit

All edits tracked in `master_data_audit` table with: table_name, record_id, field_name, old_value, new_value, change_source, changed_by, changed_at, session_id.

### 5.6 Staleness Detection

| Field Group | Staleness Threshold | Trigger |
|---|---|---|
| Fair value, market yield | 6 months | Valuation cycle |
| Valuation dates | 6 months | Calendar |
| Debt, shareholder loan | 3 months | Financing changes |
| ESG (CO2, energy, waste) | 12 months | Annual reporting |
| EPC rating | 24 months | Certificate refresh |
| Tech specs | 24 months | Rarely change |
| Address, ownership | Never | Stable unless transaction |
