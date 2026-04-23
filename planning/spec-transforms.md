# Transformation Rules & Validation

Critical logic for CSV parsing, Z1/G2 aggregation, and data validation. Referenced from [PLAN.md](PLAN.md).

---

## 1. CSV Parsing

1. Skip first 10 rows (metadata + headers parsed separately)
2. **Extract metadata from header rows:**
   - Row 0 → fund label
   - Row 5 → Stichtag (reporting date)
   - Row 8 → column headers (store for fingerprinting)
3. **Fingerprint column headers:** Hash the column header row and compare against the expected schema. If mismatch: reject upload with diff showing which columns changed.
4. Read data area with `sep=';'`, `encoding='latin-1'`
5. Strip `'` (apostrophe) from all numeric fields before casting to float. Strip `%` from percentage fields.
6. Parse dates from `dd.mm.yyyy` format
7. Classify each row by type (data / summary / orphan / total)
8. **For orphan rows** (`col[0]` is empty but `col[1]` has a property_id): inherit fund from the **most recent data row above** (not the most recent row with the same property_id — orphan rows have new property IDs that don't appear in prior data rows). Mark these rows with `fund_inherited = TRUE`. In the sample data, all 14 orphan rows appear in the DEVFUND/GIG fund sections (properties 350, 360, 5053).

## 2. Z1 Aggregation (CSV → Tenants & Leases)

```
FOR EACH (fund, property_id, tenant_name) WHERE tenant_name != 'LEERSTAND'
                                           AND row_type = 'data':
  → CONTRACTUAL_RENT = SUM(annual_net_rent) across all units
  → Look up tenant_master for BVI tenant ID, NACE sector, PD values
  → Look up fund_mapping for BVI fund ID
  → DUNS_ID = property_id (repurposed field)
```

## 3. G2 Aggregation (CSV → Property Data)

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

## 4. USE_TYPE_PRIMARY Derivation

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

## 5. Validation

- Compare aggregated `RENTABLE_AREA` against property summary row `col[9]`
- Compare aggregated `annual_net_rent` against summary row `col[30]`
- Compare aggregated `PARKING_SPACE_COUNT` against summary row `col[8]`
- Compare aggregated `market_rent` against summary row `col[35]`
- Flag discrepancies > 1% for manual review → create `data_inconsistencies` records
- Cross-upload validation: compare new upload against previous upload for the same fund to detect unexpected changes (tenants appearing/disappearing, large rent swings, property count changes)

---

## 6. Column Schema Fingerprinting

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

## 7. Row-Level Change Detection (Cross-Upload)

When a new CSV is uploaded for a fund that already has data:

1. Compare property counts: flag if properties appeared or disappeared
2. Compare tenant rosters per property: flag new/removed tenants
3. Compare unit counts per property: flag structural changes
4. Compare key numeric values (rent, area) per property: flag large deviations (>5%)
5. Compare LEERSTAND counts: flag vacancy changes

Present these as `cross_upload_change` inconsistencies in the review workflow.
