from datetime import date

import pytest

from app.core.aggregation import (
    aggregate_g2,
    aggregate_z1,
    derive_use_type,
    validate_aggregation,
)
from app.models.database import (
    CsvUpload,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    TenantMaster,
    TenantNameAlias,
)


def _make_upload(db, stichtag=None):
    upload = CsvUpload(
        filename="test.csv",
        status="complete",
        stichtag=stichtag or date(2025, 3, 31),
        row_count=10,
        data_row_count=5,
        summary_row_count=2,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload


def _add_data_row(db, upload_id, fund, property_id, tenant, unit_type, area, rent, **kwargs):
    row = RawRentRoll(
        upload_id=upload_id,
        row_number=kwargs.get("row_number", 10),
        row_type="data",
        fund=fund,
        property_id=str(property_id),
        property_name=kwargs.get("property_name"),
        tenant_name=tenant,
        unit_type=unit_type,
        area_sqm=area,
        annual_net_rent=rent,
        monthly_net_rent=rent / 12 if rent else None,
        market_rent_monthly=kwargs.get("market_rent_monthly"),
        erv_monthly=kwargs.get("erv_monthly"),
        parking_count=kwargs.get("parking_count"),
        lease_end_actual=kwargs.get("lease_end_actual"),
        wault=kwargs.get("wault"),
    )
    db.add(row)
    db.commit()
    return row


def _add_summary_row(db, upload_id, property_id, area=None, rent=None, market_rent_monthly=None, parking=None, wault=None):
    row = RawRentRoll(
        upload_id=upload_id,
        row_number=99,
        row_type="property_summary",
        property_id=str(property_id),
        property_name=f"{property_id} - TestCity",
        area_sqm=area,
        annual_net_rent=rent,
        market_rent_monthly=market_rent_monthly,
        parking_count=parking,
        wault=wault,
    )
    db.add(row)
    db.commit()
    return row


# ── USE_TYPE_PRIMARY ───────────────────────────────────────────────

def test_derive_use_type_single_dominant():
    assert derive_use_type({"Halle": 8000, "Büro": 1000}) == "INDUSTRIAL"


def test_derive_use_type_75pct_threshold():
    assert derive_use_type({"Halle": 7500, "Büro": 2500}) == "INDUSTRIAL"


def test_derive_use_type_below_75pct_single_above_25():
    assert derive_use_type({"Halle": 6000, "Büro": 2000, "Sonstige": 2000}) == "INDUSTRIAL"


def test_derive_use_type_miscellaneous():
    assert derive_use_type({"Halle": 4000, "Büro": 3500, "Sonstige": 2500}) == "MISCELLANEOUS"


def test_derive_use_type_empty():
    assert derive_use_type({}) == "OTHER"


# ── Z1 Aggregation ────────────────────────────────────────────────

def test_z1_basic(db):
    upload = _make_upload(db)
    db.add(FundMapping(csv_fund_name="GLIF", bvi_fund_id="GLIFLUF"))
    db.add(TenantMaster(tenant_name_canonical="Acme GmbH", bvi_tenant_id="T001", nace_sector="MANUFACTURING"))
    db.commit()

    _add_data_row(db, upload.id, "GLIF", "7042", "Acme GmbH", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Acme GmbH", "Büro", 500, 30000)

    rows = aggregate_z1(db, upload.id, stichtag=date(2025, 3, 31))
    assert len(rows) == 1
    assert rows[0].contractual_rent == 150000
    assert rows[0].bvi_fund_id == "GLIFLUF"
    assert rows[0].bvi_tenant_id == "T001"
    assert rows[0].nace_sector == "MANUFACTURING"
    assert rows[0].property_id == "7042"


def test_z1_excludes_leerstand(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Acme GmbH", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Halle", 2000, 0)

    rows = aggregate_z1(db, upload.id)
    assert len(rows) == 1
    assert rows[0].tenant_name == "Acme GmbH"


def test_z1_multiple_tenants(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 3000, 80000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant B", "Büro", 500, 20000)
    _add_data_row(db, upload.id, "GLIF", "7102", "Tenant A", "Halle", 4000, 100000)

    rows = aggregate_z1(db, upload.id)
    assert len(rows) == 3


def test_z1_tenant_alias(db):
    upload = _make_upload(db)
    tm = TenantMaster(tenant_name_canonical="Acme GmbH", bvi_tenant_id="T001")
    db.add(tm)
    db.commit()
    db.refresh(tm)
    db.add(TenantNameAlias(tenant_master_id=tm.id, csv_tenant_name="ACME GMBH"))
    db.commit()

    _add_data_row(db, upload.id, "GLIF", "7042", "ACME GMBH", "Halle", 5000, 120000)

    rows = aggregate_z1(db, upload.id)
    assert len(rows) == 1
    assert rows[0].bvi_tenant_id == "T001"


# ── G2 Aggregation ────────────────────────────────────────────────

def test_g2_areas(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Büro", 500, 30000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Stellplätze", 0, 5000, parking_count=10)

    rows = aggregate_g2(db, upload.id, stichtag=date(2025, 3, 31))
    assert len(rows) == 1
    g = rows[0]
    assert g.rentable_area == 5500
    assert g.area_industrial == 5000
    assert g.area_office == 500
    assert g.parking_total == 10
    assert g.parking_let == 10


def test_g2_tenant_count_excludes_leerstand(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant B", "Büro", 500, 30000)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Halle", 2000, 0)

    rows = aggregate_g2(db, upload.id, stichtag=date(2025, 3, 31))
    assert rows[0].tenant_count == 2


def test_g2_rent_by_type(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Büro", 500, 30000)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.rent_industrial == 120000
    assert g.rent_office == 30000
    assert g.contractual_rent == 150000


def test_g2_erv(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000, erv_monthly=11000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Büro", 500, 30000, erv_monthly=2800)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.erv_industrial == 132000
    assert g.erv_office == 33600
    assert g.erv_total == 165600


def test_g2_let_vs_vacant_rent(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Büro", 500, 0, market_rent_monthly=3000)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.let_rent_industrial == 120000
    assert g.let_rent_office == 0
    assert g.vacant_rent_office == 36000


def test_g2_floorspace_let(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Büro", 500, 0)

    rows = aggregate_g2(db, upload.id)
    assert rows[0].floorspace_let == 5000
    assert rows[0].rentable_area == 5500


def test_g2_use_type_primary(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 8000, 200000)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Büro", 1000, 50000)

    rows = aggregate_g2(db, upload.id)
    assert rows[0].use_type_primary == "INDUSTRIAL"


def test_g2_lease_expiry_bucketing(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T1", "Halle", 5000, 100000,
                  lease_end_actual=date(2025, 12, 31))
    _add_data_row(db, upload.id, "GLIF", "7042", "T2", "Büro", 500, 30000,
                  lease_end_actual=date(2027, 6, 30))
    _add_data_row(db, upload.id, "GLIF", "7042", "T3", "Halle", 2000, 50000)

    rows = aggregate_g2(db, upload.id, stichtag=date(2025, 3, 31))
    g = rows[0]
    assert g.lease_expiry["0"] == 100000
    assert g.lease_expiry["2"] == 30000
    assert g.lease_expiry["open_ended"] == 50000


def test_g2_lease_expiry_10plus(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T1", "Halle", 5000, 100000,
                  lease_end_actual=date(2040, 1, 1))

    rows = aggregate_g2(db, upload.id, stichtag=date(2025, 3, 31))
    assert rows[0].lease_expiry["10"] == 100000


def test_g2_property_master_fields(db):
    upload = _make_upload(db)
    db.add(PropertyMaster(
        property_id="7042", country="NL", city="Almere",
        fair_value=50000000, epc_rating="B",
        tech_clear_height=12.5,
    ))
    db.commit()

    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 100000)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.country == "NL"
    assert g.city == "Almere"
    assert g.fair_value == 50000000
    assert g.epc_rating == "B"
    assert g.tech_clear_height == 12.5


def test_g2_market_rental_and_reversion(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_summary_row(db, upload.id, "7042", area=5000, rent=120000, market_rent_monthly=11000, wault=4.5)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.market_rental_value == 132000
    assert g.lease_term_avg == 4.5
    assert g.reversion == pytest.approx(0.1, abs=0.001)


def test_g2_rent_per_sqm(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 100000)

    rows = aggregate_g2(db, upload.id)
    assert rows[0].rent_per_sqm == pytest.approx(20.0)


def test_g2_parking_let_excludes_leerstand(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Stellplätze", 0, 5000, parking_count=8)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Stellplätze", 0, 0, parking_count=2)

    rows = aggregate_g2(db, upload.id)
    assert rows[0].parking_total == 10
    assert rows[0].parking_let == 8


def test_g2_gross_potential_income_vacant_uses_market_when_no_erv(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Büro", 500, 0, market_rent_monthly=3000)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.contractual_rent == 120000
    assert g.gross_potential_income == 120000 + 36000
    assert g.vacant_rent_office == 36000
    assert g.rent_office == 36000  # targeted = let (0) + vacant (36000)
    assert g.let_rent_industrial == 120000


def test_g2_gross_potential_income_vacant_prefers_erv_over_market(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_data_row(
        db, upload.id, "GLIF", "7042", "LEERSTAND", "Büro", 500, 0,
        erv_monthly=3500, market_rent_monthly=3000,
    )

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.contractual_rent == 120000
    assert g.vacant_rent_office == 42000
    assert g.gross_potential_income == 120000 + 42000


def test_g2_gross_potential_income_vacant_falls_back_to_contract(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "LEERSTAND", "Büro", 500, 0)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.contractual_rent == 120000
    assert g.vacant_rent_office == 0
    assert g.gross_potential_income == 120000


def test_g2_gross_potential_income_includes_unmapped_unit_type(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant B", "UnknownArt", 100, 5000)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.contractual_rent == 125000
    assert g.gross_potential_income == 125000


def test_g2_targeted_rent_by_use_type_equals_let_plus_vacant(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T1", "Büro", 1000, 60000)
    _add_data_row(
        db, upload.id, "GLIF", "7042", "LEERSTAND", "Büro", 500, 0,
        erv_monthly=2000,
    )

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.let_rent_office == 60000
    assert g.vacant_rent_office == 24000
    assert g.rent_office == g.let_rent_office + g.vacant_rent_office
    assert g.gross_potential_income == 60000 + 24000


def test_g2_reversion_none_without_summary(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)

    rows = aggregate_g2(db, upload.id)
    assert rows[0].reversion is None


def test_g2_zero_valued_master_fields_preserved(db):
    upload = _make_upload(db)
    db.add(PropertyMaster(
        property_id="7042", co2_emissions=0, fair_value=0,
        ownership_share=0,
    ))
    db.commit()
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 100000)

    rows = aggregate_g2(db, upload.id)
    g = rows[0]
    assert g.co2_emissions == 0.0
    assert g.fair_value == 0.0
    assert g.ownership_share == 0.0


# ── Validation ─────────────────────────────────────────────────────

def test_validation_no_issues(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_summary_row(db, upload.id, "7042", area=5000, rent=120000)

    issues = validate_aggregation(db, upload.id)
    assert len(issues) == 0


def test_validation_detects_area_mismatch(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_summary_row(db, upload.id, "7042", area=6000, rent=120000)

    issues = validate_aggregation(db, upload.id)
    area_issues = [i for i in issues if i.field == "rentable_area"]
    assert len(area_issues) == 1
    assert area_issues[0].deviation_pct > 1.0


def test_validation_detects_rent_mismatch(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_summary_row(db, upload.id, "7042", area=5000, rent=100000)

    issues = validate_aggregation(db, upload.id)
    rent_issues = [i for i in issues if i.field == "annual_net_rent"]
    assert len(rent_issues) == 1
    assert rent_issues[0].expected == 100000
    assert rent_issues[0].actual == 120000


def test_validation_within_tolerance(db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_summary_row(db, upload.id, "7042", area=5000, rent=119500)

    issues = validate_aggregation(db, upload.id)
    rent_issues = [i for i in issues if i.field == "annual_net_rent"]
    assert len(rent_issues) == 0


# ── API Endpoints ──────────────────────────────────────────────────

def test_z1_preview_endpoint(client, db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "Tenant A", "Halle", 5000, 120000)

    resp = client.get(f"/api/transform/z1/preview?upload_id={upload.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["rows"][0]["tenant_name"] == "Tenant A"
    assert data["rows"][0]["contractual_rent"] == 120000


def test_g2_preview_endpoint(client, db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)

    resp = client.get(f"/api/transform/g2/preview?upload_id={upload.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["rows"][0]["property_id"] == "7042"
    assert data["rows"][0]["rentable_area"] == 5000


def test_validation_endpoint(client, db):
    upload = _make_upload(db)
    _add_data_row(db, upload.id, "GLIF", "7042", "T", "Halle", 5000, 120000)
    _add_summary_row(db, upload.id, "7042", area=6000, rent=120000)

    resp = client.get(f"/api/transform/validation?upload_id={upload.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(i["field"] == "rentable_area" for i in data["issues"])


def test_preview_upload_not_found(client):
    resp = client.get("/api/transform/z1/preview?upload_id=999")
    assert resp.status_code == 404


def test_preview_upload_not_ready(client, db):
    upload = CsvUpload(filename="test.csv", status="processing")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    resp = client.get(f"/api/transform/z1/preview?upload_id={upload.id}")
    assert resp.status_code == 400
