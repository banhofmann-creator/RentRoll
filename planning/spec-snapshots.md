# Temporal Data Model & Reporting Period Snapshots

Snapshot-on-finalize mechanism, time-series queries, and period management UI. Referenced from [PLAN.md](PLAN.md).

---

## 1. The Problem

Rent rolls are periodic snapshots. A new CSV is uploaded every reporting cycle (quarterly or semi-annually), and the BVI export must reflect the state of the world **at that reporting date** — not the current state of the database. Without temporal handling:

- Editing master data for Q3 2025 silently corrupts the Q1 2025 export
- There's no way to answer "how has fair value changed over the last 4 quarters?"
- Re-exporting a past BVI submission produces different numbers than the original

Two categories of data have different temporal characteristics:

| Data Type | Storage | Temporal Handling |
|---|---|---|
| **CSV-derived** (rent, area, vacancy, tenants, WAULT, lease expiry) | `raw_rent_roll` linked to `csv_uploads` via `upload_id` | Already multi-period: each upload is a separate snapshot. Query by `upload_id` to get any period. |
| **External/master data** (fair value, debt, ESG, ownership, address, risk style, NACE sectors, PD values, fund mappings) | `property_master`, `tenant_master`, `fund_mapping` | **Single mutable record** — no history. This is the gap. |

## 2. Solution: Snapshot-on-Finalize

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
2. **Work in draft:** The user reviews inconsistencies, edits master data, previews the transformation. All edits go to the live tables. Transform preview reads from live tables.
3. **Finalize:** User clicks "Finalize period" → the system copies current state of all master tables into snapshot tables, all linked to this `reporting_period_id`. Sets status to `finalized`.
4. **Export:** BVI XLSX generation reads from the snapshot tables (not the live tables). This is reproducible forever.
5. **Continue editing:** After finalization, the user can keep editing live master data for the next period. The snapshot is immutable.
6. **Supersede (correction):** If a finalized snapshot needs correction, a new snapshot replaces it. The old one is marked `superseded`.

## 3. What Gets Snapshotted

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

**Storage impact:** ~1,200 rows per snapshot. With quarterly reporting that's ~5,000 rows/year — negligible.

## 4. Time-Series Queries

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

## 5. Finalization Guardrails

1. **Pre-finalization checklist:** Blocks finalization if:
   - Unresolved `error`-severity inconsistencies
   - Unmapped tenants or funds
   - Property_master completeness below threshold (default: core fields 100%, overall 70%)
2. **Confirmation dialog:** Shows summary of what will be frozen
3. **Draft export watermark:** Exports from a draft period are marked "PROVISIONAL — NOT FINALIZED"
4. **Supersede, don't delete:** Corrections create a new snapshot; old one is preserved with `superseded` status
