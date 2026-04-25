from datetime import date
from decimal import Decimal

from app.models.database import MasterDataAudit
from app.core.audit import log_changes, log_creation, log_deletion, snapshot


def test_log_changes_detects_diffs(db):
    old = {"name": "Old Name", "value": "100"}
    new = {"name": "New Name", "value": "200"}
    entries = log_changes(db, "test_table", 1, old, new)
    db.commit()

    assert len(entries) == 2
    names = {e.field_name for e in entries}
    assert names == {"name", "value"}
    for e in entries:
        assert e.table_name == "test_table"
        assert e.record_id == 1


def test_log_changes_ignores_unchanged(db):
    old = {"name": "Same", "value": "100"}
    new = {"name": "Same", "value": "200"}
    entries = log_changes(db, "test_table", 1, old, new)
    db.commit()

    assert len(entries) == 1
    assert entries[0].field_name == "value"


def test_log_changes_handles_types(db):
    old = {"d": date(2025, 1, 1), "n": Decimal("10.50"), "x": None}
    new = {"d": date(2025, 6, 1), "n": Decimal("20.00"), "x": "now set"}
    entries = log_changes(db, "test_table", 1, old, new)
    db.commit()

    by_field = {e.field_name: e for e in entries}
    assert by_field["d"].old_value == "2025-01-01"
    assert by_field["d"].new_value == "2025-06-01"
    assert by_field["n"].old_value == "10.50"
    assert by_field["n"].new_value == "20.00"
    assert by_field["x"].old_value is None
    assert by_field["x"].new_value == "now set"


def test_log_creation_records_non_none(db):
    values = {"name": "Test", "count": 5, "empty": None}
    entries = log_creation(db, "test_table", 1, values)
    db.commit()

    assert len(entries) == 2
    for e in entries:
        assert e.old_value is None
        assert e.new_value is not None


def test_log_deletion_records_non_none(db):
    values = {"name": "Test", "count": 5, "empty": None}
    entries = log_deletion(db, "test_table", 1, values)
    db.commit()

    assert len(entries) == 2
    for e in entries:
        assert e.old_value is not None
        assert e.new_value is None


def test_snapshot_captures_fields():
    class FakeObj:
        a = "hello"
        b = 42
        c = None

    result = snapshot(FakeObj(), ["a", "b", "c"])
    assert result == {"a": "hello", "b": 42, "c": None}
