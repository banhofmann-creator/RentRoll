from datetime import date

import pytest

from app.parsers.garbe_mieterliste import (
    GarbeMieterliste,
    _clean_numeric,
    _clean_percent,
    _parse_date,
)


class TestHelpers:
    def test_clean_numeric_basic(self):
        assert _clean_numeric("712") == 712.0

    def test_clean_numeric_apostrophe(self):
        assert _clean_numeric("38'266") == 38266.0

    def test_clean_numeric_large(self):
        assert _clean_numeric("1'234'567") == 1234567.0

    def test_clean_numeric_decimal(self):
        assert _clean_numeric("123.45") == 123.45

    def test_clean_numeric_empty(self):
        assert _clean_numeric("") is None
        assert _clean_numeric("  ") is None

    def test_clean_numeric_none(self):
        assert _clean_numeric(None) is None

    def test_clean_percent(self):
        assert _clean_percent("37.9%") == pytest.approx(37.9)

    def test_clean_percent_hundred(self):
        assert _clean_percent("100%") == pytest.approx(100.0)

    def test_clean_percent_negative(self):
        assert _clean_percent("-2.1%") == pytest.approx(-2.1)

    def test_clean_percent_empty(self):
        assert _clean_percent("") is None

    def test_parse_date_german(self):
        assert _parse_date("22.04.2026") == date(2026, 4, 22)

    def test_parse_date_empty(self):
        assert _parse_date("") is None
        assert _parse_date("  ") is None

    def test_parse_date_invalid(self):
        assert _parse_date("not-a-date") is None


class TestDetect:
    def test_detect_valid(self, sample_csv_bytes):
        assert GarbeMieterliste.detect(sample_csv_bytes, "test.csv") is True

    def test_detect_invalid(self):
        assert GarbeMieterliste.detect(b"just,some,csv,data\n1,2,3,4", "test.csv") is False

    def test_detect_utf8_no_mieterliste(self):
        assert GarbeMieterliste.detect(b"Hello World", "test.csv") is False


class TestExtractMetadata:
    def test_metadata_fund_label(self, sample_csv_bytes):
        parser = GarbeMieterliste()
        meta = parser.extract_metadata(sample_csv_bytes)
        assert meta.fund_label == "1 - GARBE"

    def test_metadata_stichtag(self, sample_csv_bytes):
        parser = GarbeMieterliste()
        meta = parser.extract_metadata(sample_csv_bytes)
        assert meta.stichtag == date(2026, 4, 22)

    def test_metadata_columns(self, sample_csv_bytes):
        parser = GarbeMieterliste()
        meta = parser.extract_metadata(sample_csv_bytes)
        assert len(meta.column_headers) == 61
        assert meta.column_headers[0] == "Fonds"
        assert "Numer" in meta.column_headers[1]
        assert meta.column_headers[12] == "Mietername"

    def test_metadata_fingerprint(self, sample_csv_bytes):
        parser = GarbeMieterliste()
        meta = parser.extract_metadata(sample_csv_bytes)
        assert meta.column_fingerprint
        assert len(meta.column_fingerprint) == 16


class TestParseFull:
    @pytest.fixture(autouse=True)
    def _parse(self, sample_csv_bytes):
        parser = GarbeMieterliste()
        self.result = parser.parse(sample_csv_bytes)

    def test_row_count(self):
        assert self.result.stats["data_rows"] == 3298

    def test_summary_count(self):
        assert self.result.stats["summary_rows"] == 221

    def test_orphan_count(self):
        assert self.result.stats["orphan_rows"] == 14

    def test_total_row(self):
        assert self.result.stats["total_rows_found"] == 1

    def test_total_parsed(self):
        total = self.result.stats["total_rows"]
        expected = 3298 + 221 + 14 + 1
        assert total == expected

    def test_first_data_row(self):
        data_rows = [r for r in self.result.rows if r["row_type"] == "data"]
        first = data_rows[0]
        assert first["fund"] == "GLIFPLUSII"
        assert first["property_id"] == "1001"
        assert first["tenant_name"] == "Linde Material Handling Rhein-Ruhr GmbH & Co. KG"
        assert first["area_sqm"] == 712.0
        assert first["annual_net_rent"] == 38266.0

    def test_summary_row_detection(self):
        summaries = [r for r in self.result.rows if r["row_type"] == "property_summary"]
        assert len(summaries) == 221
        first = summaries[0]
        assert first["property_name"] is not None or first["fund"] is not None

    def test_orphan_rows_have_inherited_fund(self):
        orphans = [r for r in self.result.rows if r["row_type"] == "orphan"]
        assert len(orphans) == 14
        for orphan in orphans:
            assert orphan["fund"] is not None, f"Orphan at row {orphan['row_number']} has no fund"
            assert orphan["fund_inherited"] is True

    def test_orphan_rows_inherit_from_preceding_data(self):
        orphans = [r for r in self.result.rows if r["row_type"] == "orphan"]
        orphan_funds = {o["fund"] for o in orphans}
        assert "HPV" in orphan_funds or "GIG" in orphan_funds or "DEVFUND" in orphan_funds

    def test_orphan_property_ids(self):
        orphans = [r for r in self.result.rows if r["row_type"] == "orphan"]
        orphan_pids = {o["property_id"] for o in orphans}
        assert "350" in orphan_pids or "360" in orphan_pids or "5053" in orphan_pids

    def test_funds_discovered(self):
        data_rows = [r for r in self.result.rows if r["row_type"] == "data"]
        funds = {r["fund"] for r in data_rows}
        assert "GLIF" in funds
        assert "GLIFPLUSII" in funds
        assert "HPV" in funds
        assert len(funds) == 16

    def test_leerstand_rows(self):
        leerstand = [r for r in self.result.rows if r.get("tenant_name") == "LEERSTAND"]
        assert len(leerstand) >= 600

    def test_date_parsing(self):
        data_rows = [r for r in self.result.rows if r["row_type"] == "data"]
        rows_with_lease_start = [r for r in data_rows if r.get("lease_start")]
        assert len(rows_with_lease_start) > 0
        first_dated = rows_with_lease_start[0]
        assert isinstance(first_dated["lease_start"], date)

    def test_numeric_parsing_large_rent(self):
        data_rows = [r for r in self.result.rows if r["row_type"] == "data"]
        rents = [r["annual_net_rent"] for r in data_rows if r.get("annual_net_rent")]
        assert max(rents) > 100000

    def test_total_row_detection(self):
        total_rows = [r for r in self.result.rows if r["row_type"] == "total"]
        assert len(total_rows) == 1

    def test_metadata(self):
        assert self.result.metadata.fund_label == "1 - GARBE"
        assert self.result.metadata.stichtag == date(2026, 4, 22)
