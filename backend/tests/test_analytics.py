from datetime import date

import pytest

from app.models.database import (
    CsvUpload,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    ReportingPeriod,
    SnapshotPropertyMaster,
    TenantMaster,
)


def _make_period(db, stichtag, status="finalized", with_data=True):
    """Create a period with an upload and optional rent roll data."""
    upload = CsvUpload(
        filename="test.csv", status="complete",
        stichtag=stichtag, row_count=10, data_row_count=5, summary_row_count=2,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    period = ReportingPeriod(
        stichtag=stichtag, upload_id=upload.id, status=status,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period, upload


def _add_row(db, upload_id, property_id, tenant, unit_type, area, rent, **kw):
    row = RawRentRoll(
        upload_id=upload_id, row_number=kw.get("row_number", 10),
        row_type=kw.get("row_type", "data"),
        fund="GLIF", property_id=str(property_id),
        tenant_name=tenant, unit_type=unit_type,
        area_sqm=area, annual_net_rent=rent,
        monthly_net_rent=rent / 12 if rent else None,
        wault=kw.get("wault"),
    )
    db.add(row)
    db.commit()
    return row


def _add_snapshot_property(db, period_id, property_id, fair_value=None, debt=None):
    sp = SnapshotPropertyMaster(
        reporting_period_id=period_id,
        property_id=str(property_id),
        fair_value=fair_value,
        debt_property=debt,
    )
    db.add(sp)
    db.commit()
    return sp


# ── Portfolio KPIs ────────────────────────────────────────────────────

def test_kpis_single_period(client, db):
    p, u = _make_period(db, date(2025, 3, 31))
    _add_row(db, u.id, "7042", "Tenant A", "Halle", 5000, 120000)
    _add_row(db, u.id, "7042", "Tenant B", "Büro", 500, 30000)
    _add_row(db, u.id, "7042", "LEERSTAND", "Halle", 1000, 0)
    _add_snapshot_property(db, p.id, "7042", fair_value=50000000, debt=20000000)

    resp = client.get("/api/analytics/kpis")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1

    kpi = data[0]
    assert kpi["stichtag"] == "2025-03-31"
    assert kpi["total_rent"] == 150000
    assert kpi["total_area"] == 6500
    assert kpi["vacant_area"] == 1000
    assert kpi["vacancy_rate"] == pytest.approx(15.38, abs=0.01)
    assert kpi["tenant_count"] == 2
    assert kpi["property_count"] == 1
    assert kpi["fair_value"] == 50000000
    assert kpi["total_debt"] == 20000000


def test_kpis_multiple_periods(client, db):
    p1, u1 = _make_period(db, date(2025, 3, 31))
    _add_row(db, u1.id, "7042", "T", "Halle", 5000, 100000)
    _add_snapshot_property(db, p1.id, "7042", fair_value=40000000)

    p2, u2 = _make_period(db, date(2025, 9, 30))
    _add_row(db, u2.id, "7042", "T", "Halle", 5000, 110000)
    _add_snapshot_property(db, p2.id, "7042", fair_value=42000000)

    resp = client.get("/api/analytics/kpis")
    data = resp.json()
    assert len(data) == 2
    assert data[0]["stichtag"] == "2025-03-31"
    assert data[1]["stichtag"] == "2025-09-30"
    assert data[1]["total_rent"] == 110000
    assert data[1]["fair_value"] == 42000000


def test_kpis_draft_excluded_by_default(client, db):
    _make_period(db, date(2025, 3, 31), status="finalized")
    _make_period(db, date(2025, 9, 30), status="draft")

    resp = client.get("/api/analytics/kpis")
    assert len(resp.json()) == 1


def test_kpis_all_includes_draft(client, db):
    _make_period(db, date(2025, 3, 31), status="finalized")
    _make_period(db, date(2025, 9, 30), status="draft")

    resp = client.get("/api/analytics/kpis?status=all")
    assert len(resp.json()) == 2


def test_kpis_empty(client):
    resp = client.get("/api/analytics/kpis")
    assert resp.status_code == 200
    assert resp.json() == []


def test_kpis_parking_excluded_from_area(client, db):
    p, u = _make_period(db, date(2025, 3, 31))
    _add_row(db, u.id, "7042", "T", "Halle", 5000, 100000)
    _add_row(db, u.id, "7042", "T", "Stellplätze", 0, 5000)

    resp = client.get("/api/analytics/kpis")
    assert resp.json()[0]["total_area"] == 5000


def test_kpis_wault_from_summary(client, db):
    p, u = _make_period(db, date(2025, 3, 31))
    _add_row(db, u.id, "7042", "T", "Halle", 5000, 100000)
    _add_row(db, u.id, "7042", None, None, None, None,
             row_type="property_summary", wault=4.5, row_number=99)

    resp = client.get("/api/analytics/kpis")
    assert resp.json()[0]["wault_avg"] == 4.5


# ── Period Comparison ─────────────────────────────────────────────────

def test_compare_periods(client, db):
    p1, u1 = _make_period(db, date(2025, 3, 31))
    _add_row(db, u1.id, "7042", "T", "Halle", 5000, 100000)
    _add_snapshot_property(db, p1.id, "7042", fair_value=40000000)

    p2, u2 = _make_period(db, date(2025, 9, 30))
    _add_row(db, u2.id, "7042", "T", "Halle", 5000, 120000)
    _add_snapshot_property(db, p2.id, "7042", fair_value=44000000)

    resp = client.get(f"/api/analytics/compare?period_a={p1.id}&period_b={p2.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_a"] == "2025-03-31"
    assert data["period_b"] == "2025-09-30"

    by_metric = {m["metric"]: m for m in data["metrics"]}
    assert by_metric["total_rent"]["delta"] == 20000
    assert by_metric["total_rent"]["delta_pct"] == 20.0
    assert by_metric["fair_value"]["delta"] == 4000000
    assert by_metric["fair_value"]["delta_pct"] == 10.0


def test_compare_not_found(client):
    resp = client.get("/api/analytics/compare?period_a=999&period_b=998")
    assert resp.status_code == 404


# ── Property History ──────────────────────────────────────────────────

def test_property_history(client, db):
    p1, u1 = _make_period(db, date(2025, 3, 31))
    _add_row(db, u1.id, "7042", "T", "Halle", 5000, 100000)
    _add_snapshot_property(db, p1.id, "7042", fair_value=40000000)

    p2, u2 = _make_period(db, date(2025, 9, 30))
    _add_row(db, u2.id, "7042", "T", "Halle", 5500, 115000)
    _add_row(db, u2.id, "7042", "LEERSTAND", "Büro", 300, 0)
    _add_snapshot_property(db, p2.id, "7042", fair_value=43000000)

    resp = client.get("/api/analytics/properties/7042/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    assert data[0]["stichtag"] == "2025-03-31"
    assert data[0]["rent"] == 100000
    assert data[0]["area"] == 5000
    assert data[0]["vacancy_rate"] == 0
    assert data[0]["fair_value"] == 40000000

    assert data[1]["stichtag"] == "2025-09-30"
    assert data[1]["rent"] == 115000
    assert data[1]["area"] == 5800
    assert data[1]["vacancy_rate"] == pytest.approx(5.17, abs=0.01)
    assert data[1]["fair_value"] == 43000000


def test_property_history_empty(client, db):
    _make_period(db, date(2025, 3, 31))
    resp = client.get("/api/analytics/properties/9999/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_property_history_excludes_draft(client, db):
    p1, u1 = _make_period(db, date(2025, 3, 31), status="finalized")
    _add_row(db, u1.id, "7042", "T", "Halle", 5000, 100000)

    p2, u2 = _make_period(db, date(2025, 9, 30), status="draft")
    _add_row(db, u2.id, "7042", "T", "Halle", 5500, 110000)

    resp = client.get("/api/analytics/properties/7042/history")
    assert len(resp.json()) == 1
