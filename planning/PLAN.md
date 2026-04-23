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

## 2. Source Data Analysis

### 2.1 CSV Structure (`Mieterliste_1-Garbe (2).csv`)

- **Encoding:** `latin-1` (ISO 8859-1), Windows line endings (`\r\n`)
- **Delimiter:** Semicolon (`;`)
- **Number format:** Apostrophe as thousands separator (`1'234'567`), period as decimal (in some fields). Percentage values appear as `"100.00%"` or `"37.9%"` strings.
- **Header layout:** 10 non-data rows before actual data begins:
  - Row 0: Fund name (`"1 - GARBE"`)
  - Row 1: `"MIETERLISTE"`
  - Row 2: `"LISTE"`
  - Row 3: *(blank)*
  - Row 4: `"Stichtag"`
  - Row 5: `"22.04.2026"` (reporting date)
  - Row 6: *(blank)*
  - Row 7: Category group headers (4 groups: `allgemeine Informationen` at col 0, `Informationen Mieteinheit` at col 6, `Informationen Mietvertrag` at col 12, `Informationen Miete` at col 35)
  - Row 8: Column headers (61 columns). **Note:** col[1] header contains a typo: `"Immobilie\nNumer"` (should be `"Nummer"`) with embedded newline.
  - Row 9: Unit-of-measure row (includes `Stück` at col 8, `m²` at col 9, `Monate` at col 21, `Jahre` at cols 26–28)

**Column structure stability:** The 61-column layout is considered stable across uploads. Row counts will vary as tenants, units, and properties change. The parser should **fingerprint the column headers** on each upload and reject or warn if the structure deviates from the expected schema (see §10.1).

#### 2.1.1 Row Types (3,534 non-header rows in sample)

| Row Type | Count | Identification Rule |
|---|---|---|
| **Data rows** (unit-level) | 3,298 | `col[0]` matches a known fund name (e.g., `GLIF`, `GLIFPLUSII`) |
| **Property summary rows** | 221 | `col[0]` matches pattern `^\d{2,4}\s*-\s*` (e.g., `"7042 - Almere, ..."`) |
| **Orphan rows** (fund=NaN) | 14 | `col[0]` is empty but `col[1]` has a property ID; these belong to the preceding fund but lack the fund value — inherit from context (see §4.1 step 6) |
| **Grand total row** | 1 | `col[0]` = `"Total 481 Mieter"` |

#### 2.1.2 Funds in CSV (16 funds)

`ARES`, `BrookfieldJV`, `DEVFUND`, `EhemalsRasmala`, `GIANT`, `GIG`, `GLIF`, `GLIFPLUSII`, `GLIFPLUSIII`, `GUNIF`, `HPV`, `MATTERHORN`, `Pontegadea_Partler`, `TRIUVA`, `UIIGARBEGENO`, `UIIGARBENONGENO`

#### 2.1.3 Column Map (61 columns, 0-indexed)

**General Information (cols 0–4)**

| Col | Name | Notes |
|---|---|---|
| 0 | Fonds | Fund identifier |
| 1 | Immobilie Nummer | Property ID (numeric, e.g., `701`, `7042`). Header has typo `"Numer"`. |
| 2 | Immobilie Bezeichnung | Property name/description |
| 3 | GARBE Niederlassung | GARBE regional office |
| 4 | *(empty)* | Spacer column |

**Unit Information (cols 5–10)**

| Col | Name | Unit | Notes |
|---|---|---|---|
| 5 | Mieteinheit | — | Rental unit ID (e.g., `10100`, `20000`) |
| 6 | Art | — | Unit type: `Halle`, `Büro`, `Empore/Mezzanine`, `Stellplätze`, `Freifläche`, `Sonstige`, `Rampe`, `Wohnen`, `Gastronomie`, `Einzelhandel`, `Hotel` |
| 7 | Stockwerk | — | Floor level (e.g., `EG`, `OG1`) |
| 8 | Anzahl Stellplätze | Stück | Parking space count (only for Stellplätze rows) |
| 9 | Fläche | m² | Area of rental unit |
| 10 | *(empty)* | — | Spacer |

**Lease Contract (cols 11–28)**

| Col | Name | Unit | Notes |
|---|---|---|---|
| 11 | Lease ID | — | Format: `{property_id}.{sequence}` (e.g., `7104.00003`) |
| 12 | Mietername | — | Tenant name. `"LEERSTAND"` = vacancy |
| 13 | Mietbeginn | date | Lease start date (dd.mm.yyyy) |
| 14 | vereinbartes Vertragsende | date | Agreed lease end |
| 15 | Vertragsende (Kündigung) | date | Termination end |
| 16 | tatsächliches Vertragsende | date | Actual end date |
| 17 | Sonderkündigung Frist | date | Special termination notice period |
| 18 | Sonderkündigung zum | date | Special termination date |
| 19 | Kündigung Frist | — | Notice period |
| 20 | Kündigung zum | date | Notice date |
| 21 | Laufzeit Option | Monate | Option duration in months |
| 22 | Frist Optionsziehung | date | Option exercise deadline |
| 23 | MV-Ende nach Optionsziehung | date | Lease end after option exercise |
| 24 | Anzahl weiterer Optionen | — | Number of additional options |
| 25 | maximale Mietlaufzeit | date | Maximum lease term |
| 26 | WAULT | Jahre | Weighted average unexpired lease term (years) |
| 27 | WAULB | Jahre | WAULT to break (years) |
| 28 | WAULE | Jahre | WAULT to expiry (years) |

**Rent Information (cols 29–48)**

| Col | Name | Unit | Notes |
|---|---|---|---|
| 29 | *(empty)* | — | Spacer |
| 30 | Jahresnettomiete | €/year | Annual net contract rent |
| 31 | Nettomiete | €/month | Monthly net rent |
| 32 | Investitionsmiete | €/month | Investment rent |
| 33 | Ende mietfreie Zeit | date | End of rent-free period |
| 34 | Betrag mietfreie Zeit | €/month | Rent-free amount |
| 35 | Marktmiete | €/month | Market rent |
| 36 | AM-ERV | €/month | ERV (estimated rental value) |
| 37 | Potenzial | % | Reversion potential (string, e.g., `"37.9%"` or `"-2.1%"`) |
| 38 | Nettomiete | €/m²/a | Net rent per sqm per year |
| 39 | Marktmiete | €/m²/a | Market rent per sqm per year |
| 40 | AM-ERV | €/m²/a | ERV per sqm per year |
| 41 | *(empty)* | — | Spacer |
| 42 | NKVZ | €/month | Service charge (Vorauszahlung) |
| 43 | NK-Pauschale | €/month | Service charge (lump sum) |
| 44 | NKVZ | €/m²/a | Service charge per sqm/year |
| 45 | NK-Pauschale | €/m²/a | Lump sum per sqm/year |
| 46 | Gesamtnettomiete | €/month | Total gross rent monthly |
| 47 | Gesamtnettomiete | €/m²/a | Total gross rent per sqm/year |
| 48 | Mieter UST-pflichtig | — | VAT-liable (boolean-like: `"1"` or `"100.00%"` in summary rows) |

**Rent Escalation (cols 49–60)**

| Col | Name | Notes |
|---|---|---|
| 49 | *(empty)* | Spacer |
| 50 | proz. Mieterhöhung | Percentage rent increase (boolean: `"true"/"false"`) |
| 51 | Erhöhungs-Prozentsatz | Increase percentage |
| 52 | nächste Erhöhung | Next increase date |
| 53 | Erhöhungszyklen | Escalation cycles |
| 54 | *(empty)* | Spacer |
| 55 | Indexmieterhöhung | Index-linked escalation (boolean: `"true"/"false"`) |
| 56 | Wertsicherung Art | Index type (e.g., `"Datum"`) |
| 57 | Schwellwert | Threshold |
| 58 | Datum | Reference date |
| 59 | Weitergabe | Pass-through percentage (e.g., `"100%"`) |
| 60 | Green Lease | Green lease clause (`0`/`1`) |

#### 2.1.4 Special Data Patterns

- **LEERSTAND (vacancy):** 610 rows. These are rental units without a tenant. They are excluded from tenant counts but included in total rentable area. They are also needed to compute vacant-rent breakdowns in G2.
- **Photovoltaik tenants** (e.g., `PACE Photovoltaik 1 GmbH`, `PACE Photovoltaik 2 GmbH`, `PACE Photovoltaik 3 GmbH`): 41 rows. PV-system leases on building roofs. Typically type `Sonstige` with **zero/empty area**. Included in Z1 tenant export but often excluded from commercial tenant counts in G2.
- **Property summary rows:** Contain pre-aggregated totals in specific columns only: parking count (col 8), total area (col 9), WAULT (col 26), annual rent (col 30), monthly rent (col 31), market rent (col 35), ERV (col 36), reversion potential (col 37), rent per m² (cols 38–40), service charge (cols 42, 44), total gross rent (cols 46–47), VAT ratio (col 48). All other columns are empty. These serve as validation checksums. The summary row `col[0]` contains the full address string: `"{prop_id} - {city}, {street}"` (e.g., `"1001 - Essen, Essen - Bonifaciusstr./Rotth. Str.48, Bonifaciusstr/Rotthauser Str 1 / 48"`).
- **Number parsing:** All monetary and area values use `'` (apostrophe/U+0027) as thousands separator. Must strip before parsing to float.
- **Date format:** `dd.mm.yyyy` (German format).
- **Boolean fields:** cols 50 and 55 use string `"true"`/`"false"`, not `0`/`1`.
- **Percentage fields:** col 37 (`Potenzial`) and col 48 (`UST-pflichtig` in summary rows) and col 59 (`Weitergabe`) use string percent format (e.g., `"37.9%"`, `"100%"`).

### 2.2 Target XLSX Structure (`BVI_Target_Tables.xlsx`)

Two worksheets. Both start with a header block (rows 1–11) containing metadata, BVI field codes, descriptions, data types, and example values. Actual data begins at row 12. Column A is always empty (offset by 1).

The target file can contain **multiple reporting periods** (Stichtag values) in the same sheet. The sample contains periods `2025-03-31` and `2025-10-31`. This means each upload adds rows for its reporting date rather than replacing prior data.

#### 2.2.1 Sheet: Z1_Tenants_Leases

**Purpose:** One row per tenant per property (BVI "Add-on module 1: Tenants and Leases, Item 15").

| Column | BVI Field | Source | Derivation |
|---|---|---|---|
| B | COMPANY.OBJECT_ID_SENDER | Fund ID mapping | `GLIFPLUSIII` → `GLIF3LUF`; requires a **fund mapping table** |
| C | PERIOD.IDENTIFIER | Stichtag from CSV header | Date (Excel serial); e.g., `2025-03-31` |
| D | CURRENCY | Constant | `EUR` |
| E | OBJECT_ID_SENDER | **Tenant master table** | Composite ID like `C04.000858`; NOT derivable from CSV Lease ID — requires maintained mapping |
| F | DUNS_ID | Property ID | Repurposed: contains the property number (e.g., `7102`, `7042`) |
| G | LABEL | Tenant name | From CSV `col[12]`, de-duplicated per property |
| H | SECTOR | **NACE mapping table** | NACE Rev. 2 code (e.g., `MANUFACTURING`, `TRANSPORTATION_STORAGE`); requires external classification per tenant |
| I | PD_MIN | **External risk data** | Probability of default min (decimal, e.g., `0.0075`) |
| J | PD_MAX | **External risk data** | Probability of default max (decimal) |
| K | CONTRACTUAL_RENT_TENANT | **Aggregation** | Annual net contract rent summed across all units for this tenant at this property |

**Key aggregation rule:** Group CSV data rows by `(fund, property_id, tenant_name)` → sum `Jahresnettomiete (col 30)` → produces one Z1 row per group. LEERSTAND rows are **excluded**.

**Rent discrepancy note:** CSV annual rents and target values show ~1–2% differences (e.g., CSV sum `1,020,929` vs target `1,002,874`). This is likely due to reporting-date differences (CSV Stichtag = 22.04.2026 vs target Stichtag = 31.03.2025). The transformation should use the CSV values as the current truth.

**Sample data:** The sample Z1 sheet contains 33 tenant rows, all from fund `GLIF3LUF` with period `2025-03-31`. The full export would contain all funds.

#### 2.2.2 Sheet: G2_Property_data

**Purpose:** One row per property per reporting period, with physical, financial, area, rent-by-type, lease-expiry, sustainability, and technical data (BVI "Range 2: Property data"). **144 columns total.**

The sample G2 sheet contains 71 properties with actual data across 4 fund IDs (`GLIF`, `GLIF3`, `GLIF3LUF`, `GUNIF`) and 2 periods. The remaining ~1,505 rows are empty template placeholders.

##### G2 Columns: ID & Status (cols 2–10, BVI columns B–J)

| Col | BVI Field | Label | Source | Derivation |
|---|---|---|---|---|
| 2 | FUND_ID | Fund ID | Fund mapping | Same mapping as Z1 |
| 3 | PERIOD.IDENTIFIER | Key date | Stichtag | Reporting date |
| 4 | CURRENCY | Currency | Constant | `EUR` |
| 5 | OBJECT_ID_SENDER | Property ID | CSV `col[1]` | Numeric property ID |
| 6 | COMPANY.OBJECT_ID_SENDER | Hierarchical predecessor ID | **Hierarchy table** | Predecessor/holding company ID (e.g., `GLIF3LU12`); requires external data |
| 7 | LABEL | Property name | CSV `col[2]` or summary row | Property name/description |
| 8 | PROP_STATE | Status | **External data** | `HELD_PROPERTY`, `DEVELOPMENT`, `LAND` |
| 9 | PROP_OWNERSHIP_TYPE | Ownership type | **External data** | `DIRECT`, `INDIRECT` |
| 10 | *(no BVI code)* | Land Ownership | **External data** | `Freehold`, `Leasehold` |

##### G2 Columns: Address (cols 11–16)

| Col | BVI Field | Label | Source | Derivation |
|---|---|---|---|---|
| 11 | COUNTRY | Country | **Derivable** | From address/property name; most are `DE` |
| 12 | Region | Region | **External data** | Regional classification |
| 13 | ZIP | Postcode | **Derivable** | From summary row address parsing |
| 14 | CITY | City | **Derivable** | From summary row or `col[2]` |
| 15 | STREET | Street, address | **Derivable** | From summary row address |
| 16 | LOCATION_QUALITY | Quality of location | **External data** | `1A`, `1B`, `2A`, etc. |

##### G2 Columns: Green Building (cols 17–20)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 17 | GREEN_BUILDING_VENDOR | Green building provider | **External data** (`DGNB`, `BREEAM`, etc.) |
| 18 | GREEN_BUILDING_CERT | Green building certificate | **External data** (`Gold`, `Very good`, etc.) |
| 19 | GREEN_BUILDING_CERT_FROM | Certificate valid as of | **External data** |
| 20 | GREEN_BUILDING_CERT_TO | Certificate valid until | **External data** |

##### G2 Columns: Ownership & Classification (cols 21–25)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 21 | OWNERSHIP_SHARE | Percentage ownership | **External data** (decimal 0–1) |
| 22 | PURCHASE_DATE | Acquisition date | **External data** |
| 23 | ECONOMIC_CONSTRUCTION_DATE | Economic construction date | **External data** (year) |
| 24 | USE_TYPE_PRIMARY | Main use type | **Derivable** (75% rule, see §4.4) |
| 25 | RISK_STYLE | Risk segment | **External data** (`CORE`, `CORE_PLUS`, `VALUE_ADDED`, `OPPORTUNISTIC`) |

##### G2 Columns: Valuation (cols 26–30)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 26 | FAIR_VALUE | Fair market value | **External data** |
| 27 | MARKET_RENTAL_VALUE | Gross income at arm's length | **Aggregation**: summary row `Marktmiete (col 35)` × 12 |
| 28 | MARKET_NET_YIELD | Property yield | **External data / calculation** |
| 29 | LAST_VALUATION_DATE | Date of latest valuation | **External data** |
| 30 | NEXT_VALUATION_DATE | Scheduled date for next valuation | **External data** |

##### G2 Columns: Floor Areas (cols 31–46)

| Col | BVI Field | Label | Source | Derivation |
|---|---|---|---|---|
| 31 | AREA_MEASURE | Floor area unit of measurement | Constant | `M2` |
| 32 | *(no BVI code)* | Plot Size | **External data** | Total plot area (m²) |
| 33 | RENTABLE_AREA | Rentable area | **Aggregation** | SUM(`Fläche col[9]`) for all non-Stellplätze units |
| 34 | *(no BVI code)* | Area Check | **Derivable** | Validation flag |
| 35 | TENANT_COUNT | Number of Tenants | **Aggregation** | COUNT(DISTINCT tenant_name) excluding LEERSTAND |
| 36 | FLOORSPACE_LET | Let area | **Aggregation** | SUM(`Fläche col[9]`) for non-LEERSTAND, non-Stellplätze units |
| 37 | *(no BVI code)* | Office | **Aggregation** | SUM area WHERE `Art` = `Büro` |
| 38 | *(no BVI code)* | Mezzanine | **Aggregation** | SUM area WHERE `Art` = `Empore/Mezzanine` |
| 39 | *(no BVI code)* | Industrial (Storage, Warehouse) | **Aggregation** | SUM area WHERE `Art` = `Halle` |
| 40 | *(no BVI code)* | Freifläche | **Aggregation** | SUM area WHERE `Art` = `Freifläche` |
| 41 | *(no BVI code)* | Gastronomy | **Aggregation** | SUM area WHERE `Art` = `Gastronomie` |
| 42 | *(no BVI code)* | Retail | **Aggregation** | SUM area WHERE `Art` = `Einzelhandel` |
| 43 | *(no BVI code)* | Hotel | **Aggregation** | SUM area WHERE `Art` = `Hotel` |
| 44 | *(no BVI code)* | Rampe | **Aggregation** | SUM area WHERE `Art` = `Rampe` |
| 45 | *(no BVI code)* | Residential | **Aggregation** | SUM area WHERE `Art` = `Wohnen` |
| 46 | *(no BVI code)* | Other lettable Area | **Aggregation** | SUM area WHERE `Art` = `Sonstige` |

##### G2 Columns: Parking & Debt (cols 47–50)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 47 | PARKING_SPACE_COUNT | Number of parking spots | **Aggregation**: SUM(`Anzahl Stellplätze col[8]`) |
| 48 | PARKING_SPACE_COUNT_LET | Number of parking spots - let | **Aggregation**: SUM parking for non-LEERSTAND |
| 49 | DEBT_PROP | Property debt capital | **External data** |
| 50 | SHAREHOLDER_LOAN_PROP | Property shareholder loans | **External data** |

##### G2 Columns: Contract & Targeted Rent (cols 51–65)

| Col | BVI Field | Label | Source | Derivation |
|---|---|---|---|---|
| 51 | CONTRACTUAL_RENT | Contract rent | **Aggregation** | SUM(`annual_net_rent col[30]`) across all units in property |
| 52 | *(no BVI code)* | rent / sqm | **Derivable** | CONTRACTUAL_RENT / RENTABLE_AREA |
| 53 | GROSS_POTENTIAL_INCOME | Targeted net rent | **Aggregation** | SUM(`annual_net_rent col[30]`) — same as col 51 for fully let properties; for vacant units use market rent |
| 54 | GROSS_POTENTIAL_INCOME_OFFICE | Targeted net rent: Office | **Aggregation** | SUM annual rent WHERE `Art` = `Büro` |
| 55 | *(no BVI code)* | Targeted net rent: Mezzanine | **Aggregation** | SUM annual rent WHERE `Art` = `Empore/Mezzanine` |
| 56 | *(no BVI code)* | Targeted net rent: Industrial, outdoor | **Aggregation** | (combined industrial sub-type) |
| 57 | GROSS_POTENTIAL_INCOME_INDUSTRY | Targeted net rent: Industrial (storage, warehouses) | **Aggregation** | SUM annual rent WHERE `Art` = `Halle` |
| 58 | *(no BVI code)* | Targeted net rent: Freifläche | **Aggregation** | SUM annual rent WHERE `Art` = `Freifläche` |
| 59 | GROSS_POTENTIAL_INCOME_HOTEL | Targeted net rent: gastronomy | **Aggregation** | SUM annual rent WHERE `Art` = `Gastronomie` |
| 60 | GROSS_POTENTIAL_INCOME_LEISURE | Targeted net rent: Retail | **Aggregation** | SUM annual rent WHERE `Art` = `Einzelhandel` |
| 61 | *(no BVI code)* | Targeted net rent: Hotel | **Aggregation** | SUM annual rent WHERE `Art` = `Hotel` |
| 62 | *(no BVI code)* | Targeted net rent: Rampe | **Aggregation** | SUM annual rent WHERE `Art` = `Rampe` |
| 63 | *(no BVI code)* | Targeted net rent: Residential | **Aggregation** | SUM annual rent WHERE `Art` = `Wohnen` |
| 64 | GROSS_POTENTIAL_INCOME_PARKING | Targeted net rent: Parking | **Aggregation** | SUM annual rent WHERE `Art` = `Stellplätze` |
| 65 | GROSS_POTENTIAL_INCOME_OTHER | Targeted net rent: Other | **Aggregation** | SUM annual rent WHERE `Art` = `Sonstige` |

##### G2 Columns: AM-ERV by Use Type (cols 66–77)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 66 | *(no BVI code)* | AM ERV: Total | **Aggregation**: SUM(`erv_monthly col[36]`) × 12 across all units |
| 67–77 | *(various)* | AM ERV: Office, Mezzanine, Industrial, Freifläche, Gastronomy, Retail, Hotel, Rampe, Residential, Parking, Other | **Aggregation**: SUM(`erv_monthly col[36]`) × 12 grouped by `Art` |

##### G2 Columns: Targeted Net Rent — Let (cols 78–88)

Same use-type breakdown as cols 54–65, but **only for let units** (tenant_name != `LEERSTAND`).

| Col | BVI Field | Label |
|---|---|---|
| 78 | GROSS_POTENTIAL_INCOME_OFFICE_LET | Targeted net rent: Office - let |
| 79 | *(no BVI code)* | Targeted net rent: Mezzanine - let |
| 80 | GROSS_POTENTIAL_INCOME_INDUSTRY_LET | Targeted net rent: Industrial - let |
| 81–88 | *(various)* | Freifläche, Gastronomy, Retail, Hotel, Rampe, Residential, Parking, Other — let |

##### G2 Columns: Targeted Net Rent — Vacant (cols 89–99)

Same use-type breakdown, but **only for vacant units** (tenant_name = `LEERSTAND`). Uses market rent (`col[35]` × 12) for vacant units.

| Col | BVI Field | Label |
|---|---|---|
| 89 | GROSS_POTENTIAL_INCOME_OFFICE_VACANT | Targeted net rent: Office - vacant |
| 90–99 | *(various)* | Mezzanine, Industrial, Freifläche, Gastronomy, Retail, Hotel, Rampe, Residential, Parking, Other — vacant |

##### G2 Columns: Lease Expiry Schedule (cols 100–112)

| Col | BVI Field | Label | Derivation |
|---|---|---|---|
| 100 | CONTRACTUAL_RENT_EXP_0 | Contract rent expiring year (t) | SUM annual_net_rent WHERE lease ends in current reporting year |
| 101 | CONTRACTUAL_RENT_EXP_1 | Contract rent expiring year (t+1) | SUM annual_net_rent WHERE lease ends in year t+1 |
| 102–109 | CONTRACTUAL_RENT_EXP_2 to _9 | Years (t+2) through (t+9) | Same pattern |
| 110 | CONTRACTUAL_RENT_EXP_10 | Contract rent expiring year (t+10) | SUM annual_net_rent WHERE lease ends in year t+10 **or later** |
| 111 | CONTRACTUAL_RENT_OPEN_ENDED | Contract rent of open-ended leases | SUM annual_net_rent WHERE no lease end date |
| 112 | LEASE_TERM_AVRG | Weighted remaining lease terms | WAULT from summary row `col[26]` or rent-weighted average of remaining lease terms |

##### G2 Columns: Tenant Count (col 113)

| Col | BVI Field | Label | Note |
|---|---|---|---|
| 113 | TENANT_COUNT | Number of tenants | Duplicate of col 35 — BVI spec places it here again within the "Number of tenants" group |

##### G2 Columns: Sustainability / ESG (cols 114–135)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 114 | CARBON_DIOXIDE_EMISSION | CO2 emissions | **External data** (kg CO2/m²/year) |
| 115 | CARBON_DIOXIDE_EMISSION_CALCULATION_YEAR | CO2 measurement year | **External data** |
| 116 | ENERGY_INTENSITY | Energy consumption intensity | **External data** (kWh/m²/year) |
| 117 | ENERGY_INTENSITY_NORMALISED | Energy consumption intensity normalised | **External data** |
| 118 | DATA_QUALITY_ENERGY_INTENSITY | Data quality on energy consumption | **External data** (`COLLECTED_DATA`, `NOT_AVAILABLE`, etc.) |
| 119 | ENERGY_REFERENCE_AREA | Energy reference area | **External data** (m²) |
| 120–130 | FLOOR_AREA_CRREM_* | Floor area percentage by CRREM type | **External / derivable** (Office, Retail-high street, Retail-shopping centre, Retail-warehouse, Industrial-warehouse, Multi-family, Single-family, Hotel, Leisure, Health, Medical office) — decimal percentages summing to 1.0 |
| 131 | EXPOSURE_FOSSIL_FUELS | Exposure to fossil fuels | **External data** |
| 132 | EXPOSURE_ENERGY_INEFFICIENCY | Exposure to energy-inefficient assets | **External data** |
| 133 | WASTE_TOTAL | Total waste volume | **External data** (tonnes) |
| 134 | WASTE_RECYCLED | Percentage of recycled waste | **External data** (decimal) |
| 135 | EPC_RATING | Energy performance certificate rating | **External data** (e.g., `A+++`, `B`, `C`) |

##### G2 Columns: Technical Specifications (cols 136–142)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 136 | TECH_CLEAR_HEIGHT | Max. clear height | **External data** (logistics building spec) |
| 137 | TECH_FLC | Floor load capacity | **External data** |
| 138 | TECH_DOCKS | Loading docks | **External data** |
| 139 | TECH_SPRINKLER | Sprinkler system | **External data** |
| 140 | TECH_LIGHT | Lighting | **External data** |
| 141 | TECH_HEAT | Heating | **External data** |
| 142 | MAINTENANCE | Maintenance | **External data** |

##### G2 Column: Reversion (col 144)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 144 | Reversion | Reversion | **Derivable**: `(MARKET_RENTAL_VALUE - CONTRACTUAL_RENT) / CONTRACTUAL_RENT` or **External data** |

**Unit type → BVI column mapping (areas, rent, ERV):**

| CSV `Art` | G2 Area Col | G2 Rent Col | G2 ERV Col | G2 Rent-Let Col | G2 Rent-Vacant Col |
|---|---|---|---|---|---|
| Halle | 39 | 57 | 69 | 80 | 91 |
| Büro | 37 | 54 | 67 | 78 | 89 |
| Empore/Mezzanine | 38 | 55 | 68 | 79 | 90 |
| Freifläche | 40 | 58 | 70 | 81 | 92 |
| Gastronomie | 41 | 59 | 71 | 82 | 93 |
| Einzelhandel | 42 | 60 | 72 | 83 | 94 |
| Hotel | 43 | 61 | 73 | 84 | 95 |
| Rampe | 44 | 62 | 74 | 85 | 96 |
| Wohnen | 45 | 63 | 75 | 86 | 97 |
| Sonstige | 46 | 65 | 77 | 88 | 99 |
| Stellplätze | → Parking (47/48) | 64 | 76 | 87 | 98 |

---

## 3. Database Schema

### Design Principles
- Store **all raw CSV data** losslessly in normalized tables
- Maintain **mapping/master tables** for data not in the CSV (tenant IDs, NACE sectors, property metadata)
- Generate BVI target views via **SQL views or query logic**, not by duplicating data
- Support **multiple reporting dates** (Stichtag) for time-series analysis
- **Preserve historical state** via reporting-period snapshots: raw CSV data is retained per upload; master data (property, tenant, fund) is frozen into a snapshot when a reporting period is finalized, enabling reproducible exports and time-series analysis across all fields (see §14)
- Track **data inconsistencies** with resolution status for manual review workflow
- Store **column schema fingerprints** to detect CSV structural changes

### 3.1 Core Tables

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

### 3.2 Mapping / Master Tables (manually maintained, UI-editable)

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

### 3.3 Inconsistency Tracking Table

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

### 3.4 Chat History Table

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

### 3.5 Master Data Audit Table

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

### 3.6 Reporting Period Snapshots (see §14)

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

### 3.7 Computed Views (SQL or application logic)

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

---

## 4. Transformation Rules (Critical Logic)

### 4.1 CSV Parsing

1. Skip first 10 rows (metadata + headers parsed separately)
2. **Extract metadata from header rows:**
   - Row 0 → fund label
   - Row 5 → Stichtag (reporting date)
   - Row 8 → column headers (store for fingerprinting)
3. **Fingerprint column headers:** Hash the column header row and compare against the expected schema. If mismatch: reject upload with diff showing which columns changed (see §10.1).
4. Read data area with `sep=';'`, `encoding='latin-1'`
5. Strip `'` (apostrophe) from all numeric fields before casting to float. Strip `%` from percentage fields.
6. Parse dates from `dd.mm.yyyy` format
7. Classify each row by type (data / summary / orphan / total)
8. **For orphan rows** (`col[0]` is empty but `col[1]` has a property_id): inherit fund from the **most recent data row above** (not the most recent row with the same property_id — orphan rows have new property IDs that don't appear in prior data rows). Mark these rows with `fund_inherited = TRUE`. In the sample data, all 14 orphan rows appear in the DEVFUND/GIG fund sections (properties 350, 360, 5053).

### 4.2 Z1 Aggregation (CSV → Tenants & Leases)

```
FOR EACH (fund, property_id, tenant_name) WHERE tenant_name != 'LEERSTAND'
                                           AND row_type = 'data':
  → CONTRACTUAL_RENT = SUM(annual_net_rent) across all units
  → Look up tenant_master for BVI tenant ID, NACE sector, PD values
  → Look up fund_mapping for BVI fund ID
  → DUNS_ID = property_id (repurposed field)
```

### 4.3 G2 Aggregation (CSV → Property Data)

```
FOR EACH (fund, property_id) WHERE row_type = 'data':

  — Floor areas —
  → RENTABLE_AREA = SUM(area_sqm) WHERE unit_type != 'Stellplätze'
  → Area by type: SUM(area_sqm) grouped by unit_type mapping (cols 37–46)
  → TENANT_COUNT = COUNT(DISTINCT tenant_name) WHERE tenant_name != 'LEERSTAND'
  → FLOORSPACE_LET = SUM(area_sqm) WHERE tenant != 'LEERSTAND' AND unit_type != 'Stellplätze'
  → PARKING_TOTAL = SUM(parking_count) across all units
  → PARKING_LET = SUM(parking_count) WHERE tenant != 'LEERSTAND'

  — Rent by use type (cols 51–65) —
  → CONTRACTUAL_RENT = SUM(annual_net_rent) across all units
  → rent_per_sqm = CONTRACTUAL_RENT / RENTABLE_AREA
  → For each unit_type: SUM(annual_net_rent) → targeted rent column

  — ERV by use type (cols 66–77) —
  → For each unit_type: SUM(erv_monthly) × 12

  — Let rent (cols 78–88) —
  → Same as rent by type, filtered to tenant != 'LEERSTAND'

  — Vacant rent (cols 89–99) —
  → For LEERSTAND units: SUM(market_rent_monthly) × 12, grouped by unit_type

  — Lease expiry schedule (cols 100–112) —
  → For each non-LEERSTAND unit with lease_end_actual:
      year_offset = year(lease_end_actual) - year(stichtag)
      if year_offset < 0: bucket to year (t)
      elif year_offset <= 9: bucket to CONTRACTUAL_RENT_EXP_{year_offset}
      else: bucket to CONTRACTUAL_RENT_EXP_10 (10+ years)
  → Units with no lease_end_actual: CONTRACTUAL_RENT_OPEN_ENDED
  → LEASE_TERM_AVRG = from summary row WAULT (col 26)

  — From summary row —
  → MARKET_RENTAL_VALUE = summary_row.market_rent_monthly × 12
  → Reversion = (MARKET_RENTAL_VALUE - CONTRACTUAL_RENT) / CONTRACTUAL_RENT

  → USE_TYPE_PRIMARY = apply_75pct_rule(area_by_type)
  → Join property_master for all external fields (incl. ESG + tech specs)
```

### 4.4 USE_TYPE_PRIMARY Derivation

```python
def derive_use_type(area_by_type: dict) -> str:
    total = sum(area_by_type.values())
    if total == 0:
        return "OTHER"
    for use_type, area in area_by_type.items():
        if area / total >= 0.75:
            return use_type
    # No single type >= 75%
    types_above_25 = [t for t, a in area_by_type.items() if a / total > 0.25]
    if len(types_above_25) <= 1:
        return max(area_by_type, key=area_by_type.get)
    return "MISCELLANEOUS"
```

### 4.5 Validation

- Compare aggregated `RENTABLE_AREA` against property summary row `col[9]`
- Compare aggregated `annual_net_rent` against summary row `col[30]`
- Compare aggregated `PARKING_SPACE_COUNT` against summary row `col[8]`
- Compare aggregated `market_rent` against summary row `col[35]`
- Flag discrepancies > 1% for manual review → create `data_inconsistencies` records
- Cross-upload validation: compare new upload against previous upload for the same fund to detect unexpected changes (tenants appearing/disappearing, large rent swings, property count changes)

---

## 5. Webapp Architecture

### 5.1 Tech Stack

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
| **Output Channels** | **Plugin interface** (see §5.4) | Abstraction layer for pushing generated files to different destinations: local filesystem, SharePoint, Box, Drooms, etc. |

### 5.2 Application Modules

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
├── parsers/                 # Source format plugins (see §5.5)
│   ├── base.py              # Abstract parser interface: parse(file) → normalized rows
│   └── garbe_mieterliste.py # Current GARBE rent roll parser
├── models/
│   ├── database.py          # SQLAlchemy models for all tables + snapshots
│   └── schemas.py           # Pydantic schemas for API
├── export/
│   ├── bvi_xlsx.py          # Generate BVI-compliant XLSX (144 columns) with header structure
│   ├── slides.py            # Template-based PPTX generation
│   └── templates/           # PPTX master templates with placeholder tokens
├── channels/                # Output channel plugins (see §5.4)
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
│   ├── assets/              # Spreadsheet-like editor for property base data (see §13)
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

### 5.3 Background Jobs & Progress Tracking

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
   │                             ├─ create job ─────────────���─►│
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

### 5.4 Output Channels (Plugin System)

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

**Configuration:** Channels are registered in settings. The Export page lets the user select destination(s) per export. Multiple channels can be triggered in parallel (e.g., download + push to SharePoint).

### 5.5 Parser Plugin System

The current CSV parser is GARBE Mieterliste-specific. Future sources (other asset managers' rent rolls, valuation reports, ESG provider CSVs) will have different formats but should feed into the same normalized `raw_rent_roll` schema.

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
- The `GarbeMieterliste` parser implements all the GARBE-specific logic (encoding, apostrophe numbers, orphan row handling)
- New parsers are added as Python modules in `backend/parsers/` — no changes to the rest of the system

### 5.6 Slide Template System

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

**Benefits:**
- Non-developers can adjust layouts, fonts, colors, logos by editing the PPTX template in PowerPoint
- New report types are added by creating a new template file — no backend code changes
- Chart placeholders (`{{chart:...}}`) are replaced with matplotlib/plotly-generated images at the correct size
- Table placeholders (`{{table:...}}`) are expanded into native PPTX table objects

### 5.7 User Workflow

```
1. UPLOAD
   └─ User uploads CSV → parser validates schema fingerprint → extracts data
       ├─ If schema matches: stores in raw_rent_roll
       │   └─ System reports: X data rows, Y properties, Z funds found
       ├─ If schema drifts: shows column diff, asks user to confirm or reject
       └─ System auto-detects inconsistencies → creates review items

2. REVIEW INCONSISTENCIES
   ├─ System surfaces issues grouped by severity (errors → warnings → info)
   ├─ Each issue shows: what was expected, what was found, suggested resolution
   ├─ User can: resolve (explain), acknowledge (accept as-is), or ignore
   ├─ For aggregation mismatches: side-by-side comparison with drill-down
   ├─ For name variations: fuzzy-match suggestions with merge/split options
   └─ For cross-upload changes: highlight diffs vs previous reporting period

3. MAP & EDIT BASE DATA
   ├─ System shows unmapped tenants → user assigns BVI tenant IDs, NACE sectors
   ├─ System shows unmapped funds → user maps to BVI fund IDs
   ├─ System shows properties missing metadata → completeness dashboard (see §13)
   ├─ User edits property base data via:
   │   ├─ Inline spreadsheet grid (quick multi-property edits)
   │   ├─ Single-property detail form (grouped tabs for core/ESG/tech)
   │   ├─ Excel roundtrip (download template → fill offline → re-upload)
   │   └─ Chatbot ("set fair value for property 7042 to 25,000,000")
   └─ Tenant name fuzzy-matching with alias suggestions

4. TRANSFORM
   └─ User triggers transformation → system generates Z1 + G2 views (144 cols)
       └─ Preview shows side-by-side: raw aggregation vs target structure

5. FINALIZE & EXPORT (see §14)
   ├─ User finalizes the reporting period → system snapshots all master data
   │   └─ Snapshot is immutable — future edits to master data don't affect it
   ├─ Download BVI XLSX (Z1 + G2 sheets with full 144-column header block)
   ├─ Generate slides from templates (property factsheets, fund summaries)
   ├─ Push to output channels (local folder, SharePoint, dataroom — see §5.4)
   └─ Custom reports (tenant analysis, WAULT reports, vacancy analysis)

6. HISTORICAL ANALYSIS (see §14)
   ├─ Compare any metric across finalized reporting periods
   ├─ "How has vacancy rate changed over the last 4 quarters?"
   ├─ "Show fair value trend for property 7102"
   └─ Re-export any past period from its frozen snapshot

7. CHAT (available at any step)
   └─ User asks natural-language questions about the data
       ├─ "What is the total vacant area in the GLIF fund?"
       ├─ "Which properties have WAULT < 3 years?"
       ├─ "Update the NACE sector for BGS technic KG to MANUFACTURING"
       ├─ "Show me the lease expiry profile for property 7102"
       ├─ "Compare total rent Q1 2025 vs Q3 2025"
       └─ "Why does the rent aggregation for property 1004 not match?"
```

---

## 6. Export: BVI XLSX Generation

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

**Snapshot-based export:** The export always reads from a **finalized reporting period** (see §14). This guarantees that re-exporting a past period produces identical output, even if master data has since been edited for a later period. Draft (not yet finalized) periods can also be exported for preview, but those pull from live master data and are marked as provisional.

---

## 7. Data Fields Requiring External Input

These fields **cannot** be derived from the CSV and must be maintained manually or imported from external sources:

### Per Tenant (tenant_master)
- `bvi_tenant_id` — BVI-internal reference ID (format: `C{nn}.{nnnnnn}` or `F{nn}.{nnnnnn}`)
- `nace_sector` — NACE Rev. 2 classification (e.g., `MANUFACTURING`, `TRANSPORTATION_STORAGE`, `WHOLESALE_RETAIL_REPAIR_MOTOR_VEHICLES_MOTORCYCLES`, `ELECTRICITY_GAS_STEAM_AIR-CONDITIONING`, `INFORMATION_COMMUNICATION`)
- `pd_min` / `pd_max` — Probability of default (decimal, e.g., `0.0075`)

### Per Property (property_master)

**Core fields:**
- `predecessor_id` — Holding company in hierarchy
- `prop_state` — HELD_PROPERTY / DEVELOPMENT / LAND
- `ownership_type` — DIRECT / INDIRECT
- `land_ownership` — Freehold / Leasehold
- `country`, `region`, `zip`, `city`, `street` — Address (partially derivable from summary row parsing)
- `location_quality` — Rating (1A–3B)
- `green_building_*` — Certification details (4 fields)
- `ownership_share` — Percentage (decimal)
- `purchase_date` — Acquisition date
- `construction_year` — Economic construction date
- `risk_style` — CORE / CORE_PLUS / VALUE_ADDED / OPPORTUNISTIC
- `fair_value` — Fair market value
- `market_net_yield` — Property yield
- `last_valuation_date`, `next_valuation_date` — Valuation schedule
- `plot_size_sqm` — Plot area
- `debt_property`, `shareholder_loan` — Financing data

**ESG / Sustainability fields (G2 cols 114–135):**
- `co2_emissions`, `co2_measurement_year` — Carbon data
- `energy_intensity`, `energy_intensity_normalised`, `data_quality_energy`, `energy_reference_area` — Energy data
- `crrem_floor_areas` — JSON object mapping CRREM categories to decimal percentages
- `exposure_fossil_fuels`, `exposure_energy_inefficiency` — Risk exposure
- `waste_total`, `waste_recycled_pct` — Waste metrics
- `epc_rating` — Energy performance certificate (A+++ through G)

**Technical specifications (G2 cols 136–142):**
- `tech_clear_height`, `tech_floor_load_capacity`, `tech_loading_docks` — Logistics specs
- `tech_sprinkler`, `tech_lighting`, `tech_heating` — Building systems
- `maintenance` — Maintenance status

### Per Fund (fund_mapping)
- `bvi_fund_id` — BVI fund identifier

**Recommended:** Pre-populate the `property_master` table from the existing BVI target data (G2 sheet) using the BVI G2 importer (see §13.1), then only require updates going forward.

---

## 8. Implementation Phases

### Phase 1: Foundation & CSV Ingestion
- **Infrastructure:** PostgreSQL (Docker), FastAPI project scaffold, Next.js frontend scaffold, background job runner (FastAPI BackgroundTasks initially)
- GARBE Mieterliste parser (via parser plugin interface §5.5)
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
- **BVI G2 importer:** parse existing BVI XLSX → pre-populate property_master (see §13.1)
- Mapping UI with unmapped-item highlighting
- Tenant name fuzzy-matching suggestions
- **Asset base data editor (see §13):**
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
- **Reporting period lifecycle** (see §14): create draft → review → finalize (snapshot) → export
- Snapshot engine: freeze property_master, tenant_master, fund_mapping into snapshot tables on finalization
- XLSX generation with exact header structure (144 columns for G2, 10 columns for Z1)
- Template-driven header blocks (JSON config)
- Export reads from snapshot (finalized) or live tables (draft); draft exports watermarked
- Multi-period support (append to existing BVI file or generate new)
- Download endpoint + local filesystem output channel
- **Re-export** any finalized period from its snapshot
- Finalization guardrails (checklist, completeness threshold, confirmation dialog)

### Phase 6: Time-Series Analysis
- **Cross-period queries** over finalized snapshots (see §14.4)
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
- PPTX template system (see §5.6): master templates with placeholder tokens
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

## 9. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Tenant name variations across CSVs | Broken tenant aggregation | Fuzzy matching + alias table + inconsistency flagging |
| New funds/properties in future CSVs | Unmapped data | Auto-detect & prompt for mapping; inconsistency workflow |
| Rounding differences CSV vs BVI | False validation errors | Allow configurable tolerance (default 2%) |
| Orphan rows (missing fund in col[0]) | Lost data | Inherit fund from most recent data row + flag for review |
| Photovoltaik tenant count ambiguity | Wrong G2 tenant counts | Configurable exclusion rules per tenant type |
| BVI spec changes | Header structure mismatch | Template-driven headers, easy to update |
| Multi-currency properties | Wrong aggregations | Respect `CURRENCY` field; current data is all EUR |
| CSV column structure changes | Parser breaks silently | Column fingerprinting rejects/warns on schema drift |
| Large row count changes between uploads | Undetected data quality issues | Cross-upload diff with anomaly detection |
| G2 144-column complexity | Incomplete export | Column-by-column test coverage; validate against sample BVI file |
| AI chatbot hallucinations | Wrong data edits | All edits require explicit user confirmation; audit trail in chat_messages |
| ESG/tech spec data gaps | Incomplete G2 export | Clearly mark missing fields; allow partial export with warnings |
| Base data entry overhead (40+ fields × 221 properties) | Users skip fields, G2 export is hollow | BVI G2 import bootstraps existing data; completeness dashboard + Excel roundtrip reduce friction |
| Stale base data across reporting periods | Fair values, valuations, ESG metrics go out of date | Staleness flags on fields older than configurable threshold; prompt for review on each upload |
| Master data edits retroactively change past exports | Historical BVI submissions become non-reproducible | Snapshot-on-finalize freezes master data per period; re-exports always pull from frozen snapshot |
| Snapshot storage growth | DB size grows with each period × all master tables | Snapshots are denormalized copies of ~300 records; negligible vs raw_rent_roll (3,500+ rows/period) |
| Forgotten finalization step | User exports without snapshotting, loses ability to reproduce | Draft exports are watermarked; finalization is required before "official" export download |

---

## 10. Input Stability & Change Detection

### 10.1 Column Schema Fingerprinting

The Mieterliste CSV has a stable 61-column structure. The parser should:

1. On each upload, read row 8 (column headers) and compute a hash fingerprint
2. Compare against the expected fingerprint stored in config
3. **If exact match:** proceed normally
4. **If mismatch:** compute a column-by-column diff showing:
   - Added columns (new headers not in expected schema)
   - Removed columns (expected headers missing)
   - Renamed columns (fuzzy match of moved/renamed headers)
   - Reordered columns
5. Present the diff to the user with options:
   - **Accept & update schema:** update the expected fingerprint, adjust column mappings
   - **Reject upload:** abort with explanation
   - **Force parse with current schema:** try to parse using existing column positions (risky)

Store the expected column schema as a versioned JSON config:
```json
{
  "version": "2026-04-22",
  "columns": [
    {"index": 0, "name": "Fonds", "type": "text"},
    {"index": 1, "name": "Immobilie Numer", "type": "integer"},
    ...
  ],
  "fingerprint": "sha256:abc123..."
}
```

### 10.2 Row-Level Change Detection (Cross-Upload)

When a new CSV is uploaded for a fund that already has data:

1. Compare property counts: flag if properties appeared or disappeared
2. Compare tenant rosters per property: flag new/removed tenants
3. Compare unit counts per property: flag structural changes
4. Compare key numeric values (rent, area) per property: flag large deviations (>5%)
5. Compare LEERSTAND counts: flag vacancy changes

Present these as `cross_upload_change` inconsistencies in the review workflow.

---

## 11. Inconsistency Detection & Manual Resolution

### 11.1 Inconsistency Categories

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

### 11.2 Resolution Workflow

The InconsistencyPage provides a guided dialogue for each issue:

1. **Issue display:** Shows the inconsistency with full context (raw data, computed values, related records)
2. **Suggested action:** System proposes a resolution based on the category:
   - `aggregation_mismatch` → "Accept computed value" or "Override with summary row value"
   - `unmapped_tenant` → "Create new tenant record" or "Link to existing tenant" (with fuzzy suggestions)
   - `name_variation` → "Merge into existing tenant" or "Keep as separate entity"
3. **User decision:** Resolve, acknowledge (accept as-is with note), or ignore
4. **Audit trail:** All resolutions are recorded with user, timestamp, and notes
5. **Export gate:** Configurable — errors can block export until resolved; warnings allow export with flag

### 11.3 Dialogue Support

For complex inconsistencies, the system supports multi-step resolution:

- **Drill-down:** Click an aggregation mismatch → see all contributing rows with individual values
- **Batch operations:** Select multiple similar issues (e.g., all unmapped tenants for a property) and resolve together
- **AI assist:** "Ask the chatbot" button that pre-fills the chat with context about the inconsistency for AI-assisted investigation

---

## 12. AI Chatbot

### 12.1 Purpose

An integrated AI chatbot (powered by Claude) that can:
- **Query data:** Answer natural-language questions about the rent roll, aggregations, or BVI output
- **Edit data:** Update master tables (tenant, property, fund mappings) via conversational commands
- **Explain:** Describe transformation logic, highlight why certain values differ, trace data lineage
- **Investigate inconsistencies:** Help users understand and resolve flagged data issues

### 12.2 Architecture

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

### 12.3 Safety Guardrails

- **Read queries** execute immediately
- **Write operations** (update, resolve) require explicit user confirmation via a UI modal before committing
- All chatbot actions are logged in `chat_messages.tool_calls_json` for audit
- The chatbot cannot delete records, only update existing ones or create new mapping entries
- SQL injection prevention: chatbot tools use parameterized queries, never raw SQL
- Rate limiting on write operations

### 12.4 Example Interactions

**Data query:**
> User: "What is the total annual rent for all GLIF properties?"
> Bot: Queries `raw_rent_roll` with `fund='GLIF'`, sums `annual_net_rent`, returns formatted answer with property breakdown.

**Inconsistency investigation:**
> User: "Why does property 1004 show a rent mismatch?"
> Bot: Queries the summary row and unit-level rows, computes the aggregate, shows the 1.2% difference, explains it's likely due to a rounding difference in the Photovoltaik unit.

**Data editing:**
> User: "Set the NACE sector for DHL Supply Chain GmbH to TRANSPORTATION_STORAGE"
> Bot: Finds the tenant in tenant_master, shows current value, proposes the update, asks for confirmation. On confirm, executes the update.

**Transformation explanation:**
> User: "How is USE_TYPE_PRIMARY determined for property 7102?"
> Bot: Queries area by unit type, shows the breakdown (Halle: 85%, Büro: 12%, Sonstige: 3%), explains the 75% rule, concludes → `INDUSTRY`.

---

## 13. Asset Base Data Management

### 13.1 The Problem

The G2 target sheet has 144 columns. Roughly half (~70 columns) are **derivable** from the CSV through aggregation. The other half — ownership details, address, green building, valuation, ESG, technical specs — must come from **property_master**, which needs to be populated and kept current for 221+ properties.

Without a practical editing workflow, users will either skip these fields (producing a hollow G2 export) or maintain them in a separate spreadsheet that drifts out of sync.

### 13.2 Bootstrap: BVI G2 Import

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
      → Insert or update property_master (upsert on property_id)
      → Log which fields were populated vs already present
```

**Import modes:**
- **Initial bootstrap:** Import all fields, overwriting any existing values
- **Fill gaps only:** Only populate fields that are currently NULL in property_master
- **Selective update:** User picks which field groups to import (e.g., "only ESG fields")

The importer handles multiple reporting periods in the G2 sheet by taking the most recent period's values.

### 13.3 Editing Interfaces

There are four ways to edit property base data, suited to different situations:

#### 13.3.1 Completeness Dashboard

The entry point. Shows at a glance what's missing.

```
┌──────────────────────────────────────────────────────────────┐
│  Asset Base Data — 221 properties                            │
│                                                              │
│  Overall completeness: ████████████░░░░░ 73%                 │
│                                                              │
│  By field group:                                             │
│  ├─ Core (state, ownership, risk)    ████████████████ 98%    │
│  ├─ Address                          █████████████░░░ 85%    │
│  ├─ Green Building                   ██████░░░░░░░░░ 42%    │
│  ├─ Valuation (FV, yield, dates)     █████████████░░░ 84%    │
│  ├─ Financial (debt, SL)             ████████████░░░░ 79%    │
│  ├─ ESG / Sustainability             ████░░░░░░░░░░░ 31%    │
│  └─ Technical Specs                  ██░░░░░░░░░░░░░ 18%    │
│                                                              │
│  Properties with no base data at all: 12  [View list]        │
│  Properties 100% complete: 38             [View list]        │
│                                                              │
│  [Open Grid Editor]  [Download Excel Template]  [Import BVI] │
└──────────────────────────────────────────────────────────────┘
```

Clicking a field group filters the grid to show only that group's columns for properties where data is missing.

#### 13.3.2 Inline Spreadsheet Grid

A filterable, sortable, editable data grid (React component, e.g., AG Grid or TanStack Table) showing property_master rows as a spreadsheet.

**Key features:**
- **Column groups as tabs/toggles:** User switches between field groups (Core | Address | Green Building | Valuation | ESG | Tech Specs) instead of seeing all 40+ columns at once
- **Empty-first sorting:** Click a column header to sort NULL values to the top for filling
- **Inline editing:** Click a cell to edit. Dropdowns for enum fields (prop_state, risk_style, ownership_type, etc.), date pickers for dates, numeric inputs with validation for numbers
- **Bulk paste:** Select a column range, paste from clipboard (Excel copy-paste workflow)
- **Fund/property filter:** Filter by fund, search by property name/ID
- **Diff highlight:** Cells changed in the current session are highlighted; user reviews and saves as batch
- **Validation:** Red borders on invalid values (e.g., ownership_share > 1, non-ISO country code). Prevent save until fixed.

**API:** `PATCH /api/master-data/properties/bulk` — accepts a list of `{property_id, field, old_value, new_value}` changes. Validates, applies, returns success/error per change. Logs all changes to audit table.

#### 13.3.3 Single-Property Detail Form

For editing one property in depth. Accessed by clicking a property row in the grid, or from any property reference elsewhere in the app.

**Layout:** Tabbed form with field groups:

```
┌─────────────────────────────────────────────────────┐
│ Property 7102 — Rheinberg                           │
│ Fund: GLIFPLUSIII  │  Last updated: 2026-03-15      │
├─────────────────────────────────────────────────────┤
│ [Core] [Address] [Green Building] [Valuation]       │
│ [Financial] [ESG] [Tech Specs]                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ── Core ──                                          │
│ Predecessor ID:    [GLIF3LU12        ]              │
│ Status:            [HELD_PROPERTY ▼  ]              │
│ Ownership type:    [DIRECT ▼         ]              │
│ Land ownership:    [Freehold ▼       ]              │
│ Risk segment:      [CORE ▼           ]              │
│                                                     │
│ ── Derived from CSV (read-only) ──                  │
│ Rentable area:     22,303 m²                        │
│ Tenant count:      2                                │
│ Annual rent:       €1,274,884                       │
│ WAULT:             3.64 years                       │
│ Primary use type:  INDUSTRY (Halle 97%)             │
│                                                     │
│ [Save]  [Reset]  [View change history]              │
└─────────────────────────────────────────────────────┘
```

**Notable design choices:**
- Shows **CSV-derived values** (read-only) alongside editable fields so the user has full context
- **Change history** per property: who changed what, when, with old/new values
- **Staleness indicators:** Fields with `last_updated` older than a configurable threshold (e.g., 6 months for fair_value, 12 months for ESG) show a warning icon prompting the user to review
- **Copy from another property:** For portfolio acquisitions where multiple properties share the same fund, ownership type, risk style — copy a template from an existing property and override specifics

#### 13.3.4 Excel Roundtrip

For offline bulk editing — the most practical path for initial data entry or periodic mass updates (e.g., annual ESG reporting, new valuation cycle).

**Download template:**

`GET /api/master-data/export-template?fund=GLIFPLUSIII&groups=esg,tech`

Generates an XLSX with:
- Row 1: Column headers (property_id, property_name, fund, then the requested field group columns)
- Row 2: Field descriptions / allowed values (as a helper row, frozen)
- Row 3+: One row per property, pre-filled with current values (empty cells for missing data)
- Data validation in Excel: dropdowns for enum fields, date format constraints

The user fills in the blanks or updates values offline, then re-uploads.

**Upload filled template:**

`POST /api/master-data/import-template`

The system:
1. Parses the uploaded XLSX
2. Computes a cell-by-cell diff against current database values
3. Presents a **diff preview**:
   ```
   Property 7102 — Rheinberg:
     co2_emissions:        NULL → 8.15
     epc_rating:           NULL → "B"
     waste_total:          NULL → 176.2
   
   Property 7103 — Buggingen:
     fair_value:           14,500,000 → 15,200,000  ⚠ changed
     co2_emissions:        NULL → 12.3
   
   Summary: 47 new values, 3 changed values, 0 conflicts
   ```
4. User reviews and confirms ("Apply all", "Apply selected", or "Cancel")
5. On confirm: applies changes, logs to audit table

**Conflict handling:** If a field was edited in the app between template download and re-upload, the system flags it as a conflict and shows both values for the user to choose.

### 13.4 Tenant Base Data Editing

The same patterns apply to tenant_master (BVI tenant IDs, NACE sectors, PD values), but at smaller scale (~480 tenants). The key interfaces:

- **Tenant list grid:** Sortable by unmapped-first, editable inline for nace_sector and PD values
- **Tenant detail view:** Shows all aliases, linked properties, current NACE sector, with edit + change history
- **Excel roundtrip:** Same download/upload/diff-preview flow as property_master
- **Auto-suggest:** When a new tenant appears in a CSV upload, the system suggests NACE sectors based on:
  - Fuzzy match to existing tenants with known sectors
  - Company name keyword matching (e.g., "Logistik" → TRANSPORTATION_STORAGE, "GmbH & Co. KG" patterns)

### 13.5 Fund Mapping Editing

Simple — only 16 funds, 2 fields each. A small inline table on the MappingPage is sufficient. No Excel roundtrip needed.

### 13.6 Change Tracking & Audit

All edits to master data (property_master, tenant_master, fund_mapping) are tracked:

```
┌──────────────────────────┐
│ master_data_audit        │
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

**Uses:**
- Per-property/per-tenant change history viewable in detail forms
- "Undo last change" for accidental edits
- Audit trail for compliance (who set fair_value, when)
- Diffing between reporting periods: "What changed in property_master since last export?"

### 13.7 Staleness Detection

Property base data can go stale between reporting periods. The system tracks when each field was last updated and warns when data may be out of date:

| Field Group | Staleness Threshold | Trigger |
|---|---|---|
| Fair value, market yield | 6 months | Valuation cycle |
| Valuation dates | 6 months | Calendar |
| Debt, shareholder loan | 3 months | Financing changes |
| ESG (CO2, energy, waste) | 12 months | Annual reporting |
| EPC rating | 24 months | Certificate refresh |
| Tech specs | 24 months | Rarely change |
| Address, ownership | Never | Stable unless transaction |

On each CSV upload, the system checks for stale fields and surfaces them as `missing_metadata` inconsistencies with severity `info`, prompting the user to review or confirm the values are still current.

---

## 14. Temporal Data Model & Reporting Period Snapshots

### 14.1 The Problem

Rent rolls are periodic snapshots. A new CSV is uploaded every reporting cycle (quarterly or semi-annually), and the BVI export must reflect the state of the world **at that reporting date** — not the current state of the database. Without temporal handling:

- Editing master data for Q3 2025 silently corrupts the Q1 2025 export
- There's no way to answer "how has fair value changed over the last 4 quarters?"
- Re-exporting a past BVI submission produces different numbers than the original

Two categories of data have different temporal characteristics:

| Data Type | Storage | Temporal Handling |
|---|---|---|
| **CSV-derived** (rent, area, vacancy, tenants, WAULT, lease expiry) | `raw_rent_roll` linked to `csv_uploads` via `upload_id` | Already multi-period: each upload is a separate snapshot. Query by `upload_id` to get any period. |
| **External/master data** (fair value, debt, ESG, ownership, address, risk style, NACE sectors, PD values, fund mappings) | `property_master`, `tenant_master`, `fund_mapping` | **Single mutable record** — no history. This is the gap. |

### 14.2 Solution: Snapshot-on-Finalize

The system introduces a **reporting period lifecycle** with a snapshot mechanism:

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│  DRAFT   │ ──→ │ FINALIZED│ ──→ │ SUPERSEDED   │
│          │     │          │     │ (optional)    │
│ Edits go │     │ Snapshot  │     │ Replaced by   │
│ to live  │     │ is frozen │     │ corrected     │
│ tables   │     │           │     │ snapshot      │
└──────────┘     └──────────┘     └──────────────┘
```

**Lifecycle:**

1. **Create draft:** When a CSV is uploaded, a `reporting_periods` record is created in `draft` status, linked to the upload.
2. **Work in draft:** The user reviews inconsistencies, edits master data, previews the transformation. All edits go to the live `property_master` / `tenant_master` / `fund_mapping` tables. Transform preview reads from live tables.
3. **Finalize:** User clicks "Finalize period" → the system:
   - Copies the current state of `property_master` → `snapshot_property_master`
   - Copies `tenant_master` → `snapshot_tenant_master`
   - Copies `tenant_name_alias` → `snapshot_tenant_name_alias`
   - Copies `fund_mapping` → `snapshot_fund_mapping`
   - All snapshot rows are linked to this `reporting_period_id`
   - Sets status to `finalized`
   - Records who finalized and when
4. **Export:** BVI XLSX generation reads from the snapshot tables (not the live tables). This is reproducible forever.
5. **Continue editing:** After finalization, the user can keep editing live master data for the next period. The snapshot is immutable.
6. **Supersede (correction):** If a finalized snapshot needs correction (e.g., wrong fair value was submitted), the user can create a new snapshot for the same Stichtag. The old one is marked `superseded` and the new one becomes the active finalized version.

### 14.3 What Gets Snapshotted

| Table | Snapshot Table | Record Count per Period | Rationale |
|---|---|---|---|
| `property_master` | `snapshot_property_master` | ~221 | Fair value, debt, ESG change every cycle |
| `tenant_master` | `snapshot_tenant_master` | ~480 | PD values update; NACE could be reclassified |
| `tenant_name_alias` | `snapshot_tenant_name_alias` | ~500 | New aliases added as tenant names change in CSV |
| `fund_mapping` | `snapshot_fund_mapping` | ~16 | Rarely changes, but must be frozen for reproducibility |

**Not snapshotted** (already temporal or unnecessary):
- `raw_rent_roll` — already per-upload; linked to the period via `upload_id`
- `csv_uploads` — metadata, not mutable
- `data_inconsistencies` — per-upload, not mutable after resolution
- `master_data_audit` — append-only log, never needs snapshotting

**Storage impact:** ~1,200 rows per snapshot (221 + 480 + 500 + 16). With quarterly reporting that's ~5,000 rows/year — negligible.

### 14.4 Time-Series Queries

With snapshots in place, every metric can be queried across time:

**CSV-derived metrics** (rent, area, vacancy, tenant count, WAULT, lease expiry):
```sql
SELECT rp.stichtag,
       SUM(r.area_sqm) AS total_area,
       SUM(CASE WHEN r.tenant_name = 'LEERSTAND' THEN r.area_sqm ELSE 0 END) AS vacant_area
FROM reporting_periods rp
JOIN csv_uploads u ON u.id = rp.upload_id
JOIN raw_rent_roll r ON r.upload_id = u.id
WHERE r.row_type = 'data' AND r.unit_type != 'Stellplätze'
GROUP BY rp.stichtag
ORDER BY rp.stichtag
```

**Master-data metrics** (fair value, debt, ESG, yields):
```sql
SELECT rp.stichtag,
       SUM(sp.fair_value) AS portfolio_fair_value,
       SUM(sp.debt_property) AS portfolio_debt,
       AVG(sp.co2_emissions) AS avg_co2
FROM reporting_periods rp
JOIN snapshot_property_master sp ON sp.reporting_period_id = rp.id
WHERE rp.status = 'finalized'
GROUP BY rp.stichtag
ORDER BY rp.stichtag
```

**Combined metrics** (e.g., vacancy rate = vacant area / total area, with fair value overlay):
```sql
SELECT rp.stichtag,
       csv_agg.vacant_area / csv_agg.total_area AS vacancy_rate,
       snap_agg.portfolio_fair_value
FROM reporting_periods rp
JOIN (...csv aggregation...) csv_agg ON csv_agg.stichtag = rp.stichtag
JOIN (...snapshot aggregation...) snap_agg ON snap_agg.reporting_period_id = rp.id
WHERE rp.status = 'finalized'
```

### 14.5 UI: Period Management Page

```
┌───────────────────────────────────────────────────────���──────────┐
│  Reporting Periods                                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┬────────────┬──────────┬───���──────┬────────────┐  │
│  │ Stichtag   │ Status     │ Upload   │ Finalized│ Actions    │  │
│  ├────────────┼────────────┼──────────┼──────────┼────────────┤  │
│  │ 2026-04-22 │ ● DRAFT    │ 2026-04… │ —        │ [Finalize] │  │
│  │ 2025-10-31 │ ● FINALIZED│ 2025-11… │ 2025-11… │ [Export]   │  │
│  │            │            │          │          │ [Compare]  │  │
│  │ 2025-03-31 │ ● FINALIZED│ 2025-04… │ 2025-04… │ [Export]   │  │
│  │            │            │          │          │ [Compare]  │  │
│  └────────────┴────────────┴──────────┴──────────┴────────────┘  │
│                                                                  │
│  [Compare] opens period-over-period analysis:                    │
│  Select two periods → view delta for:                            │
│  - Total rent, vacancy rate, WAULT                               │
│  - Fair value, debt                                              │
│  - Tenant changes (new, removed, renamed)                        │
│  - Property changes (added, removed)                             │
│  - Per-property drill-down                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 14.6 UI: History / Trend Page

```
┌──────────────────────────────────────────────────────────────────┐
│  Portfolio Trends (across finalized periods)                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Metric: [Total Annual Rent ▼]   Scope: [All Funds ▼]           │
│                                                                  │
│  €120M ┤                                          ╭─            │
│  €115M ┤                               ╭──────────╯             │
│  €110M ┤                    ╭──────────╯                        │
│  €105M ┤         ╭──────────╯                                   │
│  €100M ┤─────────╯                                              │
│        └────┬─────────┬─────────┬─────────┬──���──────            │
│          Q1'24     Q3'24     Q1'25     Q3'25     Q1'26          │
│                                                                  │
│  Available metrics:                                              │
│  ├─ CSV-derived: Total rent, Vacancy rate, Avg WAULT,           │
│  │   Tenant count, Rentable area, Let area, Parking count       │
│  ├─ Master data: Portfolio fair value, Total debt, Avg CO2,     │
│  │   Avg energy intensity, Weighted yield                       │
│  └─ Drill-down: per fund, per property, per use type            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 14.7 Finalization Guardrails

To prevent accidental or premature finalization:

1. **Pre-finalization checklist:** The system blocks finalization if:
   - There are unresolved `error`-severity inconsistencies
   - There are unmapped tenants or funds
   - Property_master completeness is below a configurable threshold (default: core fields 100%, overall 70%)
2. **Confirmation dialog:** Shows a summary of what will be frozen:
   - "221 properties, 478 tenants, 16 fund mappings will be snapshotted"
   - "3 warnings remain unresolved (will be included as-is)"
   - Lists any stale fields that haven't been refreshed since last period
3. **Draft export watermark:** Exports from a draft period are marked "PROVISIONAL — NOT FINALIZED" in the XLSX header (row 2) so they can't be accidentally submitted as official BVI data
4. **Supersede, don't delete:** If a finalized snapshot needs correction, a new snapshot replaces it. The old one is preserved with status `superseded` for audit trail. No data is ever deleted.

---

## 15. Frontend Design System (GARBE Industrial)

Based on the GARBE Industrial Design Manual. All UI components follow these guidelines.

### 15.1 Color Palette

| Name | Hex | Usage |
|---|---|---|
| **GARBE-Blau** | `#003255` | Primary brand color. Nav bar, headings, primary buttons, dark backgrounds |
| GARBE-Blau 80% | `#224f71` | Hover states on primary elements |
| GARBE-Blau 60% | `#537392` | Secondary text, borders |
| GARBE-Blau 40% | `#879cb5` | Disabled states, muted elements |
| GARBE-Blau 20% | `#c0cada` | Light backgrounds, table header fills |
| **GARBE-Grün** | `#64B42D` | Accent color. Success states, CTAs, progress indicators, active navigation |
| GARBE-Grün 80% | `#99bf65` | Hover on green elements |
| GARBE-Grün 60% | `#b5cf8c` | Secondary green accents |
| GARBE-Grün 40% | `#d0e0b5` | Light green backgrounds |
| **GARBE-Ocker** | `#a48113` | Secondary accent. Warnings, inherited/orphan row highlights |
| **GARBE-Rot** | `#FF7276` | Error states, destructive actions |
| **GARBE-Türkis** | `#005555` | Tertiary accent. Info badges, chart alternative |
| GARBE-Türkis 80% | `#337777` | Hover on teal elements |
| GARBE-Türkis 60% | `#669999` | Muted teal |
| **Neutral Light** | `#ececec` | Borders, dividers |
| **Neutral Off-White** | `#f9f9f9` | Page background |

### 15.2 Typography

- **Font family:** Open Sans (Google Fonts), self-hosted via `next/font/google`
- **Headlines (h1, h2):** Open Sans Semibold, uppercase, letter-spacing `0.045em`, line-height 130%
- **Subheadings (h3, h4):** Open Sans Semibold, uppercase, letter-spacing `0.045em`, smaller size
- **Body text:** Open Sans Regular, normal case, letter-spacing `0.02em`, line-height 140%
- **Green dot accent:** Headlines may optionally end with a GARBE-Grün dot (`·`) for brand emphasis on hero/landing sections

### 15.3 Component Patterns

**Navigation bar:**
- Background: GARBE-Blau (`#003255`)
- Text: white, Open Sans Semibold
- Active link: GARBE-Grün underline or highlight
- Logo/brand mark: white text on GARBE-Blau

**Buttons:**
- Primary: GARBE-Grün background, white text, rounded. Hover: `#99bf65`
- Secondary: GARBE-Blau background, white text, rounded. Hover: `#224f71`
- Outline: transparent with GARBE-Blau border and text. Hover: GARBE-Blau fill
- Destructive: GARBE-Rot background, white text

**Tables:**
- Header: GARBE-Blau 20% (`#c0cada`) background, GARBE-Blau text, uppercase labels
- Rows: alternating white / `#f9f9f9`, hover `#ececec`
- Inherited/orphan highlight: GARBE-Ocker `#a48113` at 15% opacity background

**Status badges:**
- Complete/success: GARBE-Grün on light green
- Processing/info: GARBE-Türkis on light teal
- Error: GARBE-Rot on light red
- Warning: GARBE-Ocker on light amber

**Cards and panels:**
- White background, `#ececec` border, subtle shadow
- Section headings in GARBE-Blau, uppercase

**Drop zones:**
- Dashed border in GARBE-Blau 60%, transitions to GARBE-Grün on drag-over

### 15.4 Layout Principles

- Clean and structured — generous whitespace ("room to breathe")
- Max content width: `max-w-7xl` (1280px) centered
- Page background: `#f9f9f9`
- Headlines span full width at top of content area
- Charts and data visualizations use the primary color palette with 20% step gradations for series
