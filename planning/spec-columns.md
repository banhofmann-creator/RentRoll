# Source & Target Column Specifications

This file contains the detailed column mappings for the CSV source and BVI XLSX target. Referenced from [PLAN.md](PLAN.md).

---

## 1. CSV Structure (`Mieterliste_1-Garbe (2).csv`)

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

**Column structure stability:** The 61-column layout is considered stable across uploads. Row counts will vary as tenants, units, and properties change. The parser should **fingerprint the column headers** on each upload and reject or warn if the structure deviates from the expected schema.

### 1.1 Row Types (3,534 non-header rows in sample)

| Row Type | Count | Identification Rule |
|---|---|---|
| **Data rows** (unit-level) | 3,298 | `col[0]` matches a known fund name (e.g., `GLIF`, `GLIFPLUSII`) |
| **Property summary rows** | 221 | `col[0]` matches pattern `^\d{2,4}\s*-\s*` (e.g., `"7042 - Almere, ..."`) |
| **Orphan rows** (fund=NaN) | 14 | `col[0]` is empty but `col[1]` has a property ID; these belong to the preceding fund but lack the fund value — inherit from context |
| **Grand total row** | 1 | `col[0]` = `"Total 481 Mieter"` |

### 1.2 Funds in CSV (16 funds)

`ARES`, `BrookfieldJV`, `DEVFUND`, `EhemalsRasmala`, `GIANT`, `GIG`, `GLIF`, `GLIFPLUSII`, `GLIFPLUSIII`, `GUNIF`, `HPV`, `MATTERHORN`, `Pontegadea_Partler`, `TRIUVA`, `UIIGARBEGENO`, `UIIGARBENONGENO`

### 1.3 Column Map (61 columns, 0-indexed)

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

### 1.4 Special Data Patterns

- **LEERSTAND (vacancy):** 610 rows. These are rental units without a tenant. They are excluded from tenant counts but included in total rentable area. They are also needed to compute vacant-rent breakdowns in G2.
- **Photovoltaik tenants** (e.g., `PACE Photovoltaik 1 GmbH`, `PACE Photovoltaik 2 GmbH`, `PACE Photovoltaik 3 GmbH`): 41 rows. PV-system leases on building roofs. Typically type `Sonstige` with **zero/empty area**. Included in Z1 tenant export but often excluded from commercial tenant counts in G2.
- **Property summary rows:** Contain pre-aggregated totals in specific columns only: parking count (col 8), total area (col 9), WAULT (col 26), annual rent (col 30), monthly rent (col 31), market rent (col 35), ERV (col 36), reversion potential (col 37), rent per m² (cols 38–40), service charge (cols 42, 44), total gross rent (cols 46–47), VAT ratio (col 48). All other columns are empty. These serve as validation checksums. The summary row `col[0]` contains the full address string: `"{prop_id} - {city}, {street}"` (e.g., `"1001 - Essen, Essen - Bonifaciusstr./Rotth. Str.48, Bonifaciusstr/Rotthauser Str 1 / 48"`).
- **Number parsing:** All monetary and area values use `'` (apostrophe/U+0027) as thousands separator. Must strip before parsing to float.
- **Date format:** `dd.mm.yyyy` (German format).
- **Boolean fields:** cols 50 and 55 use string `"true"`/`"false"`, not `0`/`1`.
- **Percentage fields:** col 37 (`Potenzial`) and col 48 (`UST-pflichtig` in summary rows) and col 59 (`Weitergabe`) use string percent format (e.g., `"37.9%"`, `"100%"`).

---

## 2. Target XLSX Structure (`BVI_Target_Tables.xlsx`)

Two worksheets. Both start with a header block (rows 1–11) containing metadata, BVI field codes, descriptions, data types, and example values. Actual data begins at row 12. Column A is always empty (offset by 1).

The target file can contain **multiple reporting periods** (Stichtag values) in the same sheet. The sample contains periods `2025-03-31` and `2025-10-31`. This means each upload adds rows for its reporting date rather than replacing prior data.

### 2.1 Sheet: Z1_Tenants_Leases

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

### 2.2 Sheet: G2_Property_data

**Purpose:** One row per property per reporting period, with physical, financial, area, rent-by-type, lease-expiry, sustainability, and technical data (BVI "Range 2: Property data"). **144 columns total.**

The sample G2 sheet contains 71 properties with actual data across 4 fund IDs (`GLIF`, `GLIF3`, `GLIF3LUF`, `GUNIF`) and 2 periods. The remaining ~1,505 rows are empty template placeholders.

#### G2 Columns: ID & Status (cols 2–10, BVI columns B–J)

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

#### G2 Columns: Address (cols 11–16)

| Col | BVI Field | Label | Source | Derivation |
|---|---|---|---|---|
| 11 | COUNTRY | Country | **Derivable** | From address/property name; most are `DE` |
| 12 | Region | Region | **External data** | Regional classification |
| 13 | ZIP | Postcode | **Derivable** | From summary row address parsing |
| 14 | CITY | City | **Derivable** | From summary row or `col[2]` |
| 15 | STREET | Street, address | **Derivable** | From summary row address |
| 16 | LOCATION_QUALITY | Quality of location | **External data** | `1A`, `1B`, `2A`, etc. |

#### G2 Columns: Green Building (cols 17–20)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 17 | GREEN_BUILDING_VENDOR | Green building provider | **External data** (`DGNB`, `BREEAM`, etc.) |
| 18 | GREEN_BUILDING_CERT | Green building certificate | **External data** (`Gold`, `Very good`, etc.) |
| 19 | GREEN_BUILDING_CERT_FROM | Certificate valid as of | **External data** |
| 20 | GREEN_BUILDING_CERT_TO | Certificate valid until | **External data** |

#### G2 Columns: Ownership & Classification (cols 21–25)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 21 | OWNERSHIP_SHARE | Percentage ownership | **External data** (decimal 0–1) |
| 22 | PURCHASE_DATE | Acquisition date | **External data** |
| 23 | ECONOMIC_CONSTRUCTION_DATE | Economic construction date | **External data** (year) |
| 24 | USE_TYPE_PRIMARY | Main use type | **Derivable** (75% rule) |
| 25 | RISK_STYLE | Risk segment | **External data** (`CORE`, `CORE_PLUS`, `VALUE_ADDED`, `OPPORTUNISTIC`) |

#### G2 Columns: Valuation (cols 26–30)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 26 | FAIR_VALUE | Fair market value | **External data** |
| 27 | MARKET_RENTAL_VALUE | Gross income at arm's length | **Aggregation**: summary row `Marktmiete (col 35)` × 12 |
| 28 | MARKET_NET_YIELD | Property yield | **External data / calculation** |
| 29 | LAST_VALUATION_DATE | Date of latest valuation | **External data** |
| 30 | NEXT_VALUATION_DATE | Scheduled date for next valuation | **External data** |

#### G2 Columns: Floor Areas (cols 31–46)

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

#### G2 Columns: Parking & Debt (cols 47–50)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 47 | PARKING_SPACE_COUNT | Number of parking spots | **Aggregation**: SUM(`Anzahl Stellplätze col[8]`) |
| 48 | PARKING_SPACE_COUNT_LET | Number of parking spots - let | **Aggregation**: SUM parking for non-LEERSTAND |
| 49 | DEBT_PROP | Property debt capital | **External data** |
| 50 | SHAREHOLDER_LOAN_PROP | Property shareholder loans | **External data** |

#### G2 Columns: Contract & Targeted Rent (cols 51–65)

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

#### G2 Columns: AM-ERV by Use Type (cols 66–77)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 66 | *(no BVI code)* | AM ERV: Total | **Aggregation**: SUM(`erv_monthly col[36]`) × 12 across all units |
| 67–77 | *(various)* | AM ERV: Office, Mezzanine, Industrial, Freifläche, Gastronomy, Retail, Hotel, Rampe, Residential, Parking, Other | **Aggregation**: SUM(`erv_monthly col[36]`) × 12 grouped by `Art` |

#### G2 Columns: Targeted Net Rent — Let (cols 78–88)

Same use-type breakdown as cols 54–65, but **only for let units** (tenant_name != `LEERSTAND`).

| Col | BVI Field | Label |
|---|---|---|
| 78 | GROSS_POTENTIAL_INCOME_OFFICE_LET | Targeted net rent: Office - let |
| 79 | *(no BVI code)* | Targeted net rent: Mezzanine - let |
| 80 | GROSS_POTENTIAL_INCOME_INDUSTRY_LET | Targeted net rent: Industrial - let |
| 81–88 | *(various)* | Freifläche, Gastronomy, Retail, Hotel, Rampe, Residential, Parking, Other — let |

#### G2 Columns: Targeted Net Rent — Vacant (cols 89–99)

Same use-type breakdown, but **only for vacant units** (tenant_name = `LEERSTAND`). Uses market rent (`col[35]` × 12) for vacant units.

| Col | BVI Field | Label |
|---|---|---|
| 89 | GROSS_POTENTIAL_INCOME_OFFICE_VACANT | Targeted net rent: Office - vacant |
| 90–99 | *(various)* | Mezzanine, Industrial, Freifläche, Gastronomy, Retail, Hotel, Rampe, Residential, Parking, Other — vacant |

#### G2 Columns: Lease Expiry Schedule (cols 100–112)

| Col | BVI Field | Label | Derivation |
|---|---|---|---|
| 100 | CONTRACTUAL_RENT_EXP_0 | Contract rent expiring year (t) | SUM annual_net_rent WHERE lease ends in current reporting year |
| 101 | CONTRACTUAL_RENT_EXP_1 | Contract rent expiring year (t+1) | SUM annual_net_rent WHERE lease ends in year t+1 |
| 102–109 | CONTRACTUAL_RENT_EXP_2 to _9 | Years (t+2) through (t+9) | Same pattern |
| 110 | CONTRACTUAL_RENT_EXP_10 | Contract rent expiring year (t+10) | SUM annual_net_rent WHERE lease ends in year t+10 **or later** |
| 111 | CONTRACTUAL_RENT_OPEN_ENDED | Contract rent of open-ended leases | SUM annual_net_rent WHERE no lease end date |
| 112 | LEASE_TERM_AVRG | Weighted remaining lease terms | WAULT from summary row `col[26]` or rent-weighted average of remaining lease terms |

#### G2 Columns: Tenant Count (col 113)

| Col | BVI Field | Label | Note |
|---|---|---|---|
| 113 | TENANT_COUNT | Number of tenants | Duplicate of col 35 — BVI spec places it here again within the "Number of tenants" group |

#### G2 Columns: Sustainability / ESG (cols 114–135)

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

#### G2 Columns: Technical Specifications (cols 136–142)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 136 | TECH_CLEAR_HEIGHT | Max. clear height | **External data** (logistics building spec) |
| 137 | TECH_FLC | Floor load capacity | **External data** |
| 138 | TECH_DOCKS | Loading docks | **External data** |
| 139 | TECH_SPRINKLER | Sprinkler system | **External data** |
| 140 | TECH_LIGHT | Lighting | **External data** |
| 141 | TECH_HEAT | Heating | **External data** |
| 142 | MAINTENANCE | Maintenance | **External data** |

#### G2 Column: Reversion (col 144)

| Col | BVI Field | Label | Source |
|---|---|---|---|
| 144 | Reversion | Reversion | **Derivable**: `(MARKET_RENTAL_VALUE - CONTRACTUAL_RENT) / CONTRACTUAL_RENT` or **External data** |

### 2.3 Unit Type → BVI Column Mapping (areas, rent, ERV)

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
