from app.core.schema_validator import EXPECTED_HEADERS, validate_schema
from app.parsers.base import ParseMetadata


def test_valid_schema():
    meta = ParseMetadata(column_headers=list(EXPECTED_HEADERS))
    warnings = validate_schema(meta)
    assert warnings == []


def test_wrong_column_count():
    meta = ParseMetadata(column_headers=EXPECTED_HEADERS[:50])
    warnings = validate_schema(meta)
    assert any("Column count mismatch" in w for w in warnings)


def test_header_mismatch():
    headers = list(EXPECTED_HEADERS)
    headers[0] = "WrongName"
    meta = ParseMetadata(column_headers=headers)
    warnings = validate_schema(meta)
    assert any("Column header differences" in w for w in warnings)
    assert any("WrongName" in w for w in warnings)


def test_sample_file_passes(sample_csv_bytes):
    from app.parsers.garbe_mieterliste import GarbeMieterliste
    parser = GarbeMieterliste()
    meta = parser.extract_metadata(sample_csv_bytes)
    warnings = validate_schema(meta)
    assert warnings == [], f"Sample CSV should pass schema validation but got: {warnings}"
