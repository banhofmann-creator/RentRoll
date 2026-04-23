import hashlib
import re
from datetime import date, datetime
from typing import Any

from app.parsers.base import ParseMetadata, ParseResult, RentRollParser

KNOWN_FUNDS = {
    "ARES", "BrookfieldJV", "DEVFUND", "EhemalsRasmala", "GIANT", "GIG",
    "GLIF", "GLIFPLUSII", "GLIFPLUSIII", "GUNIF", "HPV", "MATTERHORN",
    "Pontegadea_Partler", "TRIUVA", "UIIGARBEGENO", "UIIGARBENONGENO",
}

HEADER_ROW_COUNT = 10
SUMMARY_RE = re.compile(r"^\d{2,4}\s*-\s*")

COL_MAP = {
    "fund": 0,
    "property_id": 1,
    "property_name": 2,
    "garbe_office": 3,
    "unit_id": 5,
    "unit_type": 6,
    "floor": 7,
    "parking_count": 8,
    "area_sqm": 9,
    "lease_id": 11,
    "tenant_name": 12,
    "lease_start": 13,
    "lease_end_agreed": 14,
    "lease_end_termination": 15,
    "lease_end_actual": 16,
    "special_termination_notice": 17,
    "special_termination_date": 18,
    "notice_period": 19,
    "notice_date": 20,
    "option_duration_months": 21,
    "option_exercise_deadline": 22,
    "lease_end_after_option": 23,
    "additional_options": 24,
    "max_lease_term": 25,
    "wault": 26,
    "waulb": 27,
    "waule": 28,
    "annual_net_rent": 30,
    "monthly_net_rent": 31,
    "investment_rent": 32,
    "rent_free_end": 33,
    "rent_free_amount": 34,
    "market_rent_monthly": 35,
    "erv_monthly": 36,
    "reversion_potential_pct": 37,
    "net_rent_per_sqm_pa": 38,
    "market_rent_per_sqm_pa": 39,
    "erv_per_sqm_pa": 40,
    "service_charge_advance": 42,
    "service_charge_lumpsum": 43,
    "sc_advance_per_sqm_pa": 44,
    "sc_lumpsum_per_sqm_pa": 45,
    "total_gross_rent_monthly": 46,
    "total_gross_rent_per_sqm": 47,
    "vat_liable": 48,
    "pct_rent_increase": 50,
    "increase_percentage": 51,
    "next_increase_date": 52,
    "escalation_cycles": 53,
    "index_escalation": 55,
    "index_type": 56,
    "threshold": 57,
    "index_ref_date": 58,
    "passthrough_pct": 59,
    "green_lease": 60,
}

NUMERIC_FIELDS = {
    "area_sqm", "parking_count",
    "wault", "waulb", "waule",
    "annual_net_rent", "monthly_net_rent", "investment_rent",
    "rent_free_amount", "market_rent_monthly", "erv_monthly",
    "net_rent_per_sqm_pa", "market_rent_per_sqm_pa", "erv_per_sqm_pa",
    "service_charge_advance", "service_charge_lumpsum",
    "sc_advance_per_sqm_pa", "sc_lumpsum_per_sqm_pa",
    "total_gross_rent_monthly", "total_gross_rent_per_sqm",
    "increase_percentage",
}

PERCENT_FIELDS = {"reversion_potential_pct", "passthrough_pct"}

INTEGER_FIELDS = {"parking_count", "option_duration_months", "additional_options", "green_lease"}

DATE_FIELDS = {
    "lease_start", "lease_end_agreed", "lease_end_termination", "lease_end_actual",
    "special_termination_date", "notice_date", "option_exercise_deadline",
    "lease_end_after_option", "rent_free_end", "next_increase_date", "index_ref_date",
}

TEXT_FIELDS = {
    "fund", "property_id", "property_name", "garbe_office",
    "unit_id", "unit_type", "floor", "lease_id", "tenant_name",
    "special_termination_notice", "notice_period", "max_lease_term",
    "vat_liable", "pct_rent_increase", "escalation_cycles",
    "index_escalation", "index_type", "threshold",
}


def _clean_numeric(val: str) -> float | None:
    if not val or not val.strip():
        return None
    s = val.strip().replace("'", "").replace("\xa0", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_percent(val: str) -> float | None:
    if not val or not val.strip():
        return None
    s = val.strip().replace("%", "").replace("'", "").replace("\xa0", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_integer(val: str) -> int | None:
    n = _clean_numeric(val)
    if n is None:
        return None
    return int(n)


def _parse_date(val: str) -> date | None:
    if not val or not val.strip():
        return None
    s = val.strip()
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except ValueError:
        return None


def _clean_text(val: str) -> str | None:
    if not val:
        return None
    s = val.strip().strip('"')
    if not s:
        return None
    return s


def _fingerprint_headers(headers: list[str]) -> str:
    normalized = ";".join(h.strip().strip('"').replace("\n", " ") for h in headers)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _classify_row(cols: list[str], known_funds: set[str]) -> str:
    col0 = cols[0].strip() if cols[0] else ""
    col1 = cols[1].strip() if len(cols) > 1 and cols[1] else ""

    if col0.startswith("Total"):
        return "total"
    if col0 in known_funds:
        return "data"
    if SUMMARY_RE.match(col0):
        return "property_summary"
    if not col0 and col1:
        return "orphan"
    return "unknown"


class GarbeMieterliste(RentRollParser):
    @staticmethod
    def detect(file_content: bytes, filename: str) -> bool:
        try:
            text = file_content[:2000].decode("latin-1")
        except UnicodeDecodeError:
            return False
        return "MIETERLISTE" in text and ";" in text

    def extract_metadata(self, file_content: bytes) -> ParseMetadata:
        text = file_content.decode("latin-1")
        lines = text.split("\r\n") if "\r\n" in text else text.split("\n")

        fund_label = lines[0].split(";")[0].strip() if len(lines) > 0 else None

        stichtag = None
        if len(lines) > 5:
            date_str = lines[5].split(";")[0].strip()
            stichtag = _parse_date(date_str)

        column_headers = []
        if len(lines) > 8:
            column_headers = [h.strip().strip('"').replace("\n", " ") for h in lines[8].split(";")]

        return ParseMetadata(
            fund_label=fund_label,
            stichtag=stichtag,
            column_headers=column_headers,
            column_fingerprint=_fingerprint_headers(lines[8].split(";")),
        )

    def parse(self, file_content: bytes) -> ParseResult:
        text = file_content.decode("latin-1")
        lines = text.split("\r\n") if "\r\n" in text else text.split("\n")

        metadata = self.extract_metadata(file_content)
        warnings: list[str] = []
        rows: list[dict[str, Any]] = []

        if len(lines) <= HEADER_ROW_COUNT:
            warnings.append("File has no data rows after header")
            return ParseResult(metadata=metadata, rows=[], warnings=warnings)

        discovered_funds: set[str] = set()
        for line in lines[HEADER_ROW_COUNT:]:
            col0 = line.split(";")[0].strip() if line else ""
            if col0 and col0 not in ("", ) and not col0.startswith("Total") and not SUMMARY_RE.match(col0):
                if not col0.isdigit():
                    discovered_funds.add(col0)

        all_funds = KNOWN_FUNDS | discovered_funds
        if discovered_funds - KNOWN_FUNDS:
            new = discovered_funds - KNOWN_FUNDS
            warnings.append(f"New fund names not in known list: {sorted(new)}")

        last_data_fund: str | None = None
        stats = {"data": 0, "property_summary": 0, "orphan": 0, "total": 0, "unknown": 0}

        for line_idx, line in enumerate(lines[HEADER_ROW_COUNT:], start=HEADER_ROW_COUNT):
            if not line.strip():
                continue

            cols = line.split(";")
            if len(cols) < 5:
                continue

            row_type = _classify_row(cols, all_funds)
            stats[row_type] = stats.get(row_type, 0) + 1

            row: dict[str, Any] = {
                "row_number": line_idx,
                "row_type": row_type,
                "fund_inherited": False,
            }

            for field_name, col_idx in COL_MAP.items():
                if col_idx >= len(cols):
                    row[field_name] = None
                    continue

                raw = cols[col_idx]
                if field_name in DATE_FIELDS:
                    row[field_name] = _parse_date(raw)
                elif field_name in PERCENT_FIELDS:
                    row[field_name] = _clean_percent(raw)
                elif field_name in INTEGER_FIELDS:
                    row[field_name] = _clean_integer(raw)
                elif field_name in NUMERIC_FIELDS:
                    row[field_name] = _clean_numeric(raw)
                elif field_name in TEXT_FIELDS:
                    row[field_name] = _clean_text(raw)
                else:
                    row[field_name] = _clean_text(raw)

            if row_type == "data":
                last_data_fund = row.get("fund")
            elif row_type == "orphan":
                if last_data_fund:
                    row["fund"] = last_data_fund
                    row["fund_inherited"] = True
                    warnings.append(
                        f"Row {line_idx}: orphan row (property {row.get('property_id')}) "
                        f"inherited fund '{last_data_fund}'"
                    )
                else:
                    warnings.append(
                        f"Row {line_idx}: orphan row with no preceding data row to inherit fund from"
                    )

            rows.append(row)

        fund_list = sorted(all_funds)
        property_ids = {r["property_id"] for r in rows if r.get("property_id") and r["row_type"] in ("data", "orphan")}

        result_stats = {
            "total_rows": len(rows),
            "data_rows": stats["data"],
            "summary_rows": stats["property_summary"],
            "orphan_rows": stats["orphan"],
            "total_rows_found": stats["total"],
            "unknown_rows": stats.get("unknown", 0),
            "funds": len(fund_list),
            "properties": len(property_ids),
        }

        return ParseResult(
            metadata=metadata,
            rows=rows,
            warnings=warnings,
            stats=result_stats,
        )
