from io import BytesIO

import pytest

from app.models.database import (
    CsvUpload,
    DataInconsistency,
    MasterDataAudit,
    PropertyMaster,
)
from tests.conftest import make_test_bvi_xlsx


def _upload(client, bvi_bytes, endpoint, **params):
    files = {"file": ("test.xlsx", BytesIO(bvi_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    return client.post(f"/api/{endpoint}", files=files, params=params)


# ── Preview Tests ───────────────────────────────────────────────────

def test_preview_bvi_file(client):
    xlsx = make_test_bvi_xlsx([
        {"bvi_fund_id": "GLIF3LUF", "property_id": 7042, "city": "Almere", "country": "NL"},
        {"bvi_fund_id": "GLIF3LUF", "property_id": 7102, "city": "Essen", "country": "DE"},
    ])
    resp = _upload(client, xlsx, "bvi-import/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["properties_found"] == 2
    assert len(data["new_properties"]) == 2
    assert len(data["existing_properties"]) == 0
    assert data["field_coverage"]["city"] == 2
    assert "GLIF3LUF" in data["bvi_fund_ids"]


def test_preview_with_existing_properties(client, db):
    db.add(PropertyMaster(property_id="7042", city="Old City"))
    db.commit()

    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere"},
        {"property_id": 7102, "city": "Essen"},
    ])
    resp = _upload(client, xlsx, "bvi-import/preview")
    data = resp.json()
    assert "7042" in data["existing_properties"]
    assert "7102" in data["new_properties"]


# ── Execute Tests ───────────────────────────────────────────────────

def test_execute_fill_gaps_creates_new(client, db):
    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere", "country": "NL", "fair_value": 36400000},
    ])
    resp = _upload(client, xlsx, "bvi-import/execute", mode="fill_gaps")
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 1

    db.expire_all()
    prop = db.query(PropertyMaster).filter(PropertyMaster.property_id == "7042").first()
    assert prop is not None
    assert prop.city == "Almere"
    assert prop.country == "NL"
    assert float(prop.fair_value) == 36400000


def test_execute_fill_gaps_preserves_existing(client, db):
    db.add(PropertyMaster(property_id="7042", city="Original City", country="DE"))
    db.commit()

    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "New City", "country": "NL", "street": "Main St 1"},
    ])
    resp = _upload(client, xlsx, "bvi-import/execute", mode="fill_gaps")
    data = resp.json()
    assert data["updated"] == 1

    db.expire_all()
    prop = db.query(PropertyMaster).filter(PropertyMaster.property_id == "7042").first()
    assert prop.city == "Original City"
    assert prop.country == "DE"
    assert prop.street == "Main St 1"


def test_execute_overwrite_replaces(client, db):
    db.add(PropertyMaster(property_id="7042", city="Original City"))
    db.commit()

    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "New City", "country": "NL"},
    ])
    resp = _upload(client, xlsx, "bvi-import/execute", mode="overwrite")
    data = resp.json()
    assert data["updated"] == 1

    db.expire_all()
    prop = db.query(PropertyMaster).filter(PropertyMaster.property_id == "7042").first()
    assert prop.city == "New City"
    assert prop.country == "NL"


def test_empty_rows_skipped(client):
    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere"},
        {},  # empty row (no property_id)
        {"property_id": 7102, "city": "Essen"},
    ])
    resp = _upload(client, xlsx, "bvi-import/execute")
    data = resp.json()
    assert data["created"] == 2


def test_duplicate_property_ids_deduplicated(client, db):
    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere", "country": "NL"},
        {"property_id": 7042, "city": "Almere Updated", "street": "New Street"},
    ])
    resp = _upload(client, xlsx, "bvi-import/execute")
    data = resp.json()
    assert data["created"] == 1

    db.expire_all()
    prop = db.query(PropertyMaster).filter(PropertyMaster.property_id == "7042").first()
    assert prop.city == "Almere"
    assert prop.country == "NL"
    assert prop.street == "New Street"


def test_audit_entries_created(client, db):
    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere", "country": "NL"},
    ])
    _upload(client, xlsx, "bvi-import/execute")

    db.expire_all()
    audits = db.query(MasterDataAudit).filter(
        MasterDataAudit.table_name == "property_master",
        MasterDataAudit.change_source == "bvi_import",
    ).all()
    assert len(audits) > 0
    field_names = {a.field_name for a in audits}
    assert "city" in field_names
    assert "country" in field_names


def test_execute_resolves_missing_metadata(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="missing_metadata",
        severity="warning",
        entity_type="property",
        entity_id="7042",
        description="No property metadata",
        status="open",
    ))
    db.commit()

    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere"},
    ])
    _upload(client, xlsx, "bvi-import/execute")

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "7042"
    ).first()
    assert inc.status == "resolved"


def test_execute_update_resolves_missing_metadata(client, db):
    db.add(PropertyMaster(property_id="7042"))
    db.commit()

    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="missing_metadata",
        severity="warning",
        entity_type="property",
        entity_id="7042",
        description="No property metadata",
        status="open",
    ))
    db.commit()

    xlsx = make_test_bvi_xlsx([
        {"property_id": 7042, "city": "Almere"},
    ])
    _upload(client, xlsx, "bvi-import/execute")

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "7042"
    ).first()
    assert inc.status == "resolved"


def test_invalid_mode_rejected(client):
    xlsx = make_test_bvi_xlsx([{"property_id": 7042}])
    resp = _upload(client, xlsx, "bvi-import/execute", mode="invalid")
    assert resp.status_code == 400
