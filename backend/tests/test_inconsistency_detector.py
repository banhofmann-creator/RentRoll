import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models.database import (
    CsvUpload,
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    TenantNameAlias,
    TenantMaster,
)
from app.core.inconsistency_detector import detect_inconsistencies
from app.parsers.garbe_mieterliste import GarbeMieterliste

test_engine = create_engine(
    settings.effective_database_url,
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def parsed_upload(db, sample_csv_bytes):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    parser = GarbeMieterliste()
    result = parser.parse(sample_csv_bytes)

    rows = []
    for row_dict in result.rows:
        row_type = row_dict.pop("row_type")
        row_number = row_dict.pop("row_number")
        fund_inherited = row_dict.pop("fund_inherited", False)
        rows.append(RawRentRoll(
            upload_id=upload.id,
            row_number=row_number,
            row_type=row_type,
            fund_inherited=fund_inherited,
            **row_dict,
        ))

    db.bulk_save_objects(rows)
    db.commit()
    return upload.id


def test_no_false_positive_aggregation_on_real_data(db, parsed_upload):
    results = detect_inconsistencies(db, parsed_upload)
    agg_mismatches = [r for r in results if r.category == "aggregation_mismatch"]
    assert len(agg_mismatches) == 0, (
        f"Expected no aggregation mismatches on clean sample data, "
        f"got {len(agg_mismatches)}: {[r.description for r in agg_mismatches]}"
    )


def test_unmapped_tenants_detected(db, parsed_upload):
    results = detect_inconsistencies(db, parsed_upload)
    unmapped = [r for r in results if r.category == "unmapped_tenant"]
    assert len(unmapped) > 0
    for item in unmapped:
        assert item.severity == "error"
        assert item.entity_type == "tenant"
        assert item.entity_id != "LEERSTAND"


def test_leerstand_excluded_from_unmapped(db, parsed_upload):
    results = detect_inconsistencies(db, parsed_upload)
    unmapped = [r for r in results if r.category == "unmapped_tenant"]
    entity_ids = [r.entity_id for r in unmapped]
    assert "LEERSTAND" not in entity_ids


def test_unmapped_funds_detected(db, parsed_upload):
    results = detect_inconsistencies(db, parsed_upload)
    unmapped = [r for r in results if r.category == "unmapped_fund"]
    assert len(unmapped) > 0
    for item in unmapped:
        assert item.severity == "error"
        assert item.entity_type == "fund"


def test_missing_metadata_detected(db, parsed_upload):
    results = detect_inconsistencies(db, parsed_upload)
    missing = [r for r in results if r.category == "missing_metadata"]
    assert len(missing) > 0
    for item in missing:
        assert item.severity == "warning"
        assert item.entity_type == "property"


def test_mapped_tenant_not_flagged(db, parsed_upload):
    first_tenant = (
        db.query(RawRentRoll.tenant_name)
        .filter(
            RawRentRoll.upload_id == parsed_upload,
            RawRentRoll.row_type == "data",
            RawRentRoll.tenant_name.isnot(None),
            RawRentRoll.tenant_name != "LEERSTAND",
        )
        .first()
    )
    assert first_tenant is not None
    tenant_name = first_tenant[0]

    master = TenantMaster(tenant_name_canonical=tenant_name)
    db.add(master)
    db.commit()
    db.refresh(master)

    alias = TenantNameAlias(
        tenant_master_id=master.id,
        csv_tenant_name=tenant_name,
    )
    db.add(alias)
    db.commit()

    results = detect_inconsistencies(db, parsed_upload)
    unmapped = [r for r in results if r.category == "unmapped_tenant"]
    entity_ids = [r.entity_id for r in unmapped]
    assert tenant_name not in entity_ids


def test_mapped_fund_not_flagged(db, parsed_upload):
    first_fund = (
        db.query(RawRentRoll.fund)
        .filter(
            RawRentRoll.upload_id == parsed_upload,
            RawRentRoll.row_type == "data",
            RawRentRoll.fund.isnot(None),
        )
        .first()
    )
    assert first_fund is not None
    fund_name = first_fund[0]

    mapping = FundMapping(csv_fund_name=fund_name)
    db.add(mapping)
    db.commit()

    results = detect_inconsistencies(db, parsed_upload)
    unmapped = [r for r in results if r.category == "unmapped_fund"]
    entity_ids = [r.entity_id for r in unmapped]
    assert fund_name not in entity_ids


def test_property_with_metadata_not_flagged(db, parsed_upload):
    first_prop = (
        db.query(RawRentRoll.property_id)
        .filter(
            RawRentRoll.upload_id == parsed_upload,
            RawRentRoll.row_type == "data",
            RawRentRoll.property_id.isnot(None),
        )
        .first()
    )
    assert first_prop is not None
    prop_id = first_prop[0]

    pm = PropertyMaster(property_id=prop_id)
    db.add(pm)
    db.commit()

    results = detect_inconsistencies(db, parsed_upload)
    missing = [r for r in results if r.category == "missing_metadata"]
    entity_ids = [r.entity_id for r in missing]
    assert prop_id not in entity_ids


def test_rerun_idempotency(db, parsed_upload):
    results1 = detect_inconsistencies(db, parsed_upload)
    db.add_all(results1)
    db.commit()

    count1 = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == parsed_upload
    ).count()

    results2 = detect_inconsistencies(db, parsed_upload)
    db.add_all(results2)
    db.commit()

    count2 = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == parsed_upload
    ).count()

    assert count1 == count2


def test_synthetic_aggregation_mismatch(db):
    upload = CsvUpload(filename="synthetic.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(RawRentRoll(
        upload_id=upload.id, row_number=1, row_type="data",
        fund="TESTFUND", property_id="9999",
        area_sqm=1000.0, annual_net_rent=120000.0,
    ))
    db.add(RawRentRoll(
        upload_id=upload.id, row_number=2, row_type="data",
        fund="TESTFUND", property_id="9999",
        area_sqm=500.0, annual_net_rent=60000.0,
    ))

    db.add(RawRentRoll(
        upload_id=upload.id, row_number=3, row_type="property_summary",
        fund="9999 - Test Property",
        area_sqm=1500.0, annual_net_rent=200000.0,
    ))

    db.commit()

    results = detect_inconsistencies(db, upload.id)
    agg = [r for r in results if r.category == "aggregation_mismatch"]
    assert len(agg) >= 1
    rent_mismatch = [r for r in agg if r.field_name == "annual_net_rent"]
    assert len(rent_mismatch) == 1
    assert float(rent_mismatch[0].deviation_pct) > 1.0


def test_zero_vs_nonzero_aggregation_mismatch(db):
    upload = CsvUpload(filename="zero_test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(RawRentRoll(
        upload_id=upload.id, row_number=1, row_type="data",
        fund="TESTFUND", property_id="8888",
        area_sqm=500.0, market_rent_monthly=5000.0,
    ))

    db.add(RawRentRoll(
        upload_id=upload.id, row_number=2, row_type="property_summary",
        fund="8888 - Zero Test",
        area_sqm=500.0, market_rent_monthly=0.0,
    ))

    db.commit()

    results = detect_inconsistencies(db, upload.id)
    agg = [r for r in results if r.category == "aggregation_mismatch"]
    market_rent = [r for r in agg if r.field_name == "market_rent_monthly"]
    assert len(market_rent) == 1
    assert float(market_rent[0].deviation_pct) == 100.0
