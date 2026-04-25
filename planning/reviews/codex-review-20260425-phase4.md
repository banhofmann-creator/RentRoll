# Codex Review — Phase 4 (2026-04-25)

## Findings

| # | Severity | File | Issue | Fix |
|---|---|---|---|---|
| 1 | P1 | `backend/app/core/aggregation.py` | `gross_potential_income` copied `contractual_rent` verbatim, ignoring vacant market rent. Partially vacant properties understated this field. | Changed to `contractual_rent + sum(vacant_rent_*)` |
| 2 | P2 | `backend/app/core/aggregation.py` | Reversion computed as `-1.0` when no summary row exists (market_rental_value defaults to 0). Should be `None` for unknown. | Added `and g2.market_rental_value` guard to reversion computation. |
| 3 | P2 | `backend/app/core/aggregation.py` | Truthiness checks on numeric property_master fields (`if pm.co2_emissions`) turned legitimate zero values into `None`. | Changed all numeric field checks to `is not None`. |

## Verification

- 171 backend tests pass (including 3 new tests for findings)
- Frontend builds clean
- All 3 findings fixed before commit
