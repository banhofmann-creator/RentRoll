import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.models.database import (
    CsvUpload,
    DataInconsistency,
    FundMapping,
    MasterDataAudit,
    PropertyMaster,
    TenantMaster,
    TenantNameAlias,
)

test_engine = create_engine(
    settings.effective_database_url,
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(test_engine)

    from app.api.upload import set_session_factory
    set_session_factory(TestSession)
    yield
    set_session_factory(None)
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def client():
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db():
    session = TestSession()
    yield session
    session.close()


# ── Fund Mapping Tests ───────────────────────────────────────────────

def test_create_fund(client):
    resp = client.post("/api/master-data/funds", json={
        "csv_fund_name": "GLIF",
        "bvi_fund_id": "F01",
        "description": "Test fund",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["csv_fund_name"] == "GLIF"
    assert data["bvi_fund_id"] == "F01"


def test_create_fund_duplicate(client):
    client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    resp = client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    assert resp.status_code == 400


def test_list_funds(client):
    for name in ["GLIF", "GLIFPLUSII", "OTHER"]:
        client.post("/api/master-data/funds", json={"csv_fund_name": name})
    resp = client.get("/api/master-data/funds")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_funds_search(client):
    for name in ["GLIF", "GLIFPLUSII", "OTHER"]:
        client.post("/api/master-data/funds", json={"csv_fund_name": name})
    resp = client.get("/api/master-data/funds?search=GLIF")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all("GLIF" in f["csv_fund_name"] for f in data)


def test_update_fund(client):
    resp = client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    fund_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/funds/{fund_id}", json={
        "bvi_fund_id": "F99",
        "description": "Updated",
    })
    assert resp.status_code == 200
    assert resp.json()["bvi_fund_id"] == "F99"
    assert resp.json()["description"] == "Updated"


def test_update_fund_not_found(client):
    resp = client.patch("/api/master-data/funds/99999", json={"bvi_fund_id": "X"})
    assert resp.status_code == 404


def test_delete_fund(client):
    resp = client.post("/api/master-data/funds", json={"csv_fund_name": "GLIF"})
    fund_id = resp.json()["id"]

    resp = client.delete(f"/api/master-data/funds/{fund_id}")
    assert resp.status_code == 200

    resp = client.get("/api/master-data/funds")
    assert len(resp.json()) == 0


def test_create_fund_resolves_inconsistency(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="unmapped_fund",
        severity="error",
        entity_type="fund",
        entity_id="TESTFUND",
        description="Fund 'TESTFUND' has no mapping",
        status="open",
    ))
    db.commit()

    client.post("/api/master-data/funds", json={"csv_fund_name": "TESTFUND"})

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "TESTFUND"
    ).first()
    assert inc.status == "resolved"


# ── Tenant Master Tests ──────────────────────────────────────────────

def test_create_tenant(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme Corp",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_name_canonical"] == "Acme Corp"
    assert data["aliases"] == []


def test_create_tenant_with_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme Corp",
        "initial_alias": "ACME CORP GMBH",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["aliases"]) == 1
    assert data["aliases"][0]["csv_tenant_name"] == "ACME CORP GMBH"


def test_create_tenant_with_duplicate_initial_alias(client):
    client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme Corp",
        "initial_alias": "ACME CSV",
    })
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Other Corp",
        "initial_alias": "ACME CSV",
    })
    assert resp.status_code == 400


def test_update_tenant_duplicate_bvi_id(client):
    client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Alpha",
        "bvi_tenant_id": "BVI-001",
    })
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Beta",
        "bvi_tenant_id": "BVI-002",
    })
    beta_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/tenants/{beta_id}", json={
        "bvi_tenant_id": "BVI-001",
    })
    assert resp.status_code == 400


def test_list_tenants(client):
    for name in ["Alpha", "Beta", "Gamma"]:
        client.post("/api/master-data/tenants", json={"tenant_name_canonical": name})
    resp = client.get("/api/master-data/tenants")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_tenants_search_canonical(client):
    for name in ["Alpha Corp", "Beta Inc", "Gamma Ltd"]:
        client.post("/api/master-data/tenants", json={"tenant_name_canonical": name})
    resp = client.get("/api/master-data/tenants?search=Alpha")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_tenants_search_by_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Alpha Corp",
        "initial_alias": "ALPHA GMBH",
    })
    client.post("/api/master-data/tenants", json={"tenant_name_canonical": "Beta Inc"})

    resp = client.get("/api/master-data/tenants?search=ALPHA GMBH")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tenant_name_canonical"] == "Alpha Corp"


def test_get_tenant_detail(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]

    resp = client.get(f"/api/master-data/tenants/{tenant_id}")
    assert resp.status_code == 200
    assert resp.json()["tenant_name_canonical"] == "Acme"
    assert len(resp.json()["aliases"]) == 1


def test_update_tenant(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
    })
    tenant_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/tenants/{tenant_id}", json={
        "nace_sector": "MANUFACTURING",
    })
    assert resp.status_code == 200
    assert resp.json()["nace_sector"] == "MANUFACTURING"


def test_delete_tenant_cascades(client, db):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]

    resp = client.delete(f"/api/master-data/tenants/{tenant_id}")
    assert resp.status_code == 200

    db.expire_all()
    assert db.query(TenantNameAlias).count() == 0


def test_add_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
    })
    tenant_id = resp.json()["id"]

    resp = client.post(f"/api/master-data/tenants/{tenant_id}/aliases", json={
        "csv_tenant_name": "ACME CSV NAME",
    })
    assert resp.status_code == 200
    assert resp.json()["csv_tenant_name"] == "ACME CSV NAME"


def test_add_alias_duplicate(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]

    resp = client.post(f"/api/master-data/tenants/{tenant_id}/aliases", json={
        "csv_tenant_name": "ACME CSV",
    })
    assert resp.status_code == 400


def test_remove_alias(client):
    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Acme",
        "initial_alias": "ACME CSV",
    })
    tenant_id = resp.json()["id"]
    alias_id = resp.json()["aliases"][0]["id"]

    resp = client.delete(f"/api/master-data/tenants/{tenant_id}/aliases/{alias_id}")
    assert resp.status_code == 200

    resp = client.get(f"/api/master-data/tenants/{tenant_id}")
    assert len(resp.json()["aliases"]) == 0


def test_add_alias_resolves_inconsistency(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="unmapped_tenant",
        severity="error",
        entity_type="tenant",
        entity_id="UNMAPPED TENANT NAME",
        description="Tenant has no mapping",
        status="open",
    ))
    db.commit()

    resp = client.post("/api/master-data/tenants", json={
        "tenant_name_canonical": "Mapped Tenant",
    })
    tenant_id = resp.json()["id"]

    client.post(f"/api/master-data/tenants/{tenant_id}/aliases", json={
        "csv_tenant_name": "UNMAPPED TENANT NAME",
    })

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "UNMAPPED TENANT NAME"
    ).first()
    assert inc.status == "resolved"


# ── Property Master Tests ────────────────────────────────────────────

def test_create_property(client):
    resp = client.post("/api/master-data/properties", json={
        "property_id": "1001",
        "city": "Essen",
        "country": "DE",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["property_id"] == "1001"
    assert data["city"] == "Essen"


def test_create_property_duplicate(client):
    client.post("/api/master-data/properties", json={"property_id": "1001"})
    resp = client.post("/api/master-data/properties", json={"property_id": "1001"})
    assert resp.status_code == 400


def test_list_properties(client):
    for pid in ["1001", "1002", "1003"]:
        client.post("/api/master-data/properties", json={"property_id": pid})
    resp = client.get("/api/master-data/properties")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_properties_search_city(client):
    client.post("/api/master-data/properties", json={"property_id": "1001", "city": "Essen"})
    client.post("/api/master-data/properties", json={"property_id": "1002", "city": "Berlin"})
    client.post("/api/master-data/properties", json={"property_id": "1003", "city": "Essen"})

    resp = client.get("/api/master-data/properties?search=Essen")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_property_partial(client):
    resp = client.post("/api/master-data/properties", json={
        "property_id": "1001",
        "city": "Essen",
        "country": "DE",
    })
    prop_id = resp.json()["id"]

    resp = client.patch(f"/api/master-data/properties/{prop_id}", json={
        "city": "Dortmund",
    })
    assert resp.status_code == 200
    assert resp.json()["city"] == "Dortmund"
    assert resp.json()["country"] == "DE"


def test_delete_property(client):
    resp = client.post("/api/master-data/properties", json={"property_id": "1001"})
    prop_id = resp.json()["id"]

    resp = client.delete(f"/api/master-data/properties/{prop_id}")
    assert resp.status_code == 200

    resp = client.get("/api/master-data/properties")
    assert len(resp.json()) == 0


def test_create_property_resolves_inconsistency(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id,
        category="missing_metadata",
        severity="warning",
        entity_type="property",
        entity_id="9999",
        description="Property has no metadata",
        status="open",
    ))
    db.commit()

    client.post("/api/master-data/properties", json={"property_id": "9999"})

    db.expire_all()
    inc = db.query(DataInconsistency).filter(
        DataInconsistency.entity_id == "9999"
    ).first()
    assert inc.status == "resolved"


# ── Unmapped Endpoint Tests ──────────────────────────────────────────

def test_unmapped_returns_grouped(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add_all([
        DataInconsistency(
            upload_id=upload.id, category="unmapped_fund", severity="error",
            entity_type="fund", entity_id="FUND_A", description="x", status="open",
        ),
        DataInconsistency(
            upload_id=upload.id, category="unmapped_tenant", severity="error",
            entity_type="tenant", entity_id="TENANT_A", description="x", status="open",
        ),
        DataInconsistency(
            upload_id=upload.id, category="missing_metadata", severity="warning",
            entity_type="property", entity_id="1001", description="x", status="open",
        ),
    ])
    db.commit()

    resp = client.get("/api/master-data/unmapped")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    types = {item["entity_type"] for item in data}
    assert types == {"fund", "tenant", "property"}


def test_unmapped_filter_by_type(client, db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add_all([
        DataInconsistency(
            upload_id=upload.id, category="unmapped_fund", severity="error",
            entity_type="fund", entity_id="FUND_A", description="x", status="open",
        ),
        DataInconsistency(
            upload_id=upload.id, category="unmapped_tenant", severity="error",
            entity_type="tenant", entity_id="TENANT_A", description="x", status="open",
        ),
    ])
    db.commit()

    resp = client.get("/api/master-data/unmapped?entity_type=fund")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["entity_type"] == "fund"


# ── Audit Tests ──────────────────────────────────────────────────────

def test_update_creates_audit_entries(client, db):
    resp = client.post("/api/master-data/funds", json={
        "csv_fund_name": "GLIF",
        "bvi_fund_id": "F01",
    })
    fund_id = resp.json()["id"]

    client.patch(f"/api/master-data/funds/{fund_id}", json={
        "bvi_fund_id": "F99",
    })

    db.expire_all()
    audits = db.query(MasterDataAudit).filter(
        MasterDataAudit.table_name == "fund_mapping",
        MasterDataAudit.record_id == fund_id,
        MasterDataAudit.field_name == "bvi_fund_id",
    ).all()
    change_audits = [a for a in audits if a.old_value is not None and a.new_value is not None]
    assert len(change_audits) >= 1
    audit = change_audits[0]
    assert audit.old_value == "F01"
    assert audit.new_value == "F99"
