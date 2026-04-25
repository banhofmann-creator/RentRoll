# Codex Review — Phase 3B (2026-04-25)

## Findings

| # | Severity | File | Issue | Fix |
|---|---|---|---|---|
| 1 | P1 | `backend/app/api/excel_roundtrip.py` | Normalize exported XLSX values before diffing — openpyxl reloads dates as datetime, numerics as int/float, while ORM holds date/Decimal. `str()` comparison produces bogus diffs. | Added `_normalize()` function handling datetime→date, Decimal→float, int-float equivalence. Used in both preview and apply paths. |
| 2 | P1 | `frontend/src/app/master-data/properties/[id]/page.tsx` | CRREM keys (`retail`, `industrial`, etc.) don't match BVI parser keys (`retail_high_street`, `industrial_warehouse`, etc.). Saving overwrites imported data with wrong keys. | Updated CRREM_KEYS to match BVI parser output. |
| 3 | P2 | `backend/app/api/bvi_import.py` | `_resolve_missing_metadata` only called in creation branch, not update. Existing properties with open inconsistencies stay unresolved after BVI import. | Added `_resolve_missing_metadata(db, pid)` to the update branch. Added test `test_execute_update_resolves_missing_metadata`. |
| 4 | P2 | `backend/app/api/excel_roundtrip.py` | Excel import creation path has no audit trail and doesn't auto-resolve `missing_metadata` inconsistencies. | Added `log_creation`, `snapshot`, and `_resolve_missing_metadata` calls to creation path. |

## Verification

- 137 backend tests pass (including 1 new test for finding #3)
- Frontend builds clean
- All 4 findings fixed before commit
