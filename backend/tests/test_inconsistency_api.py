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
    RawRentRoll,
)
from app.parsers.garbe_mieterliste import GarbeMieterliste

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


@pytest.fixture
def upload_with_inconsistencies(db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add_all([
        DataInconsistency(
            upload_id=upload.id,
            category="unmapped_tenant",
            severity="error",
            entity_type="tenant",
            entity_id="Acme Corp",
            description="Tenant 'Acme Corp' has no mapping",
            status="open",
        ),
        DataInconsistency(
            upload_id=upload.id,
            category="unmapped_fund",
            severity="error",
            entity_type="fund",
            entity_id="TESTFUND",
            description="Fund 'TESTFUND' has no mapping",
            status="open",
        ),
        DataInconsistency(
            upload_id=upload.id,
            category="missing_metadata",
            severity="warning",
            entity_type="property",
            entity_id="9999",
            description="Property '9999' has no entry in property_master",
            status="open",
        ),
        DataInconsistency(
            upload_id=upload.id,
            category="orphan_row",
            severity="info",
            entity_type="row",
            description="Orphan row inherited fund GLIF",
            status="open",
        ),
    ])
    db.commit()
    return upload.id


def test_list_inconsistencies(client, upload_with_inconsistencies):
    resp = client.get(f"/api/inconsistencies?upload_id={upload_with_inconsistencies}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4


def test_list_filter_by_category(client, upload_with_inconsistencies):
    resp = client.get(
        f"/api/inconsistencies?upload_id={upload_with_inconsistencies}&category=unmapped_tenant"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["category"] == "unmapped_tenant"


def test_list_filter_by_severity(client, upload_with_inconsistencies):
    resp = client.get(
        f"/api/inconsistencies?upload_id={upload_with_inconsistencies}&severity=error"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for item in data:
        assert item["severity"] == "error"


def test_list_filter_by_status(client, upload_with_inconsistencies):
    resp = client.get(
        f"/api/inconsistencies?upload_id={upload_with_inconsistencies}&status=open"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4


def test_summary(client, upload_with_inconsistencies):
    resp = client.get(f"/api/inconsistencies/summary?upload_id={upload_with_inconsistencies}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["by_severity"]["error"] == 2
    assert data["by_severity"]["warning"] == 1
    assert data["by_severity"]["info"] == 1
    assert data["has_blocking_errors"] is True


def test_get_single(client, upload_with_inconsistencies, db):
    item = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_with_inconsistencies
    ).first()
    resp = client.get(f"/api/inconsistencies/{item.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == item.id


def test_get_not_found(client):
    resp = client.get("/api/inconsistencies/99999")
    assert resp.status_code == 404


def test_resolve_inconsistency(client, upload_with_inconsistencies, db):
    item = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_with_inconsistencies,
        DataInconsistency.category == "unmapped_tenant",
    ).first()

    resp = client.patch(
        f"/api/inconsistencies/{item.id}",
        json={
            "status": "resolved",
            "resolution_note": "Mapped manually",
            "resolved_by": "test_user",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolution_note"] == "Mapped manually"
    assert data["resolved_by"] == "test_user"
    assert data["resolved_at"] is not None


def test_acknowledge_inconsistency(client, upload_with_inconsistencies, db):
    item = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_with_inconsistencies,
        DataInconsistency.category == "missing_metadata",
    ).first()

    resp = client.patch(
        f"/api/inconsistencies/{item.id}",
        json={"status": "acknowledged"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


def test_ignore_inconsistency(client, upload_with_inconsistencies, db):
    item = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_with_inconsistencies,
        DataInconsistency.category == "orphan_row",
    ).first()

    resp = client.patch(
        f"/api/inconsistencies/{item.id}",
        json={"status": "ignored"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_invalid_status(client, upload_with_inconsistencies, db):
    item = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_with_inconsistencies,
    ).first()

    resp = client.patch(
        f"/api/inconsistencies/{item.id}",
        json={"status": "invalid_status"},
    )
    assert resp.status_code == 400


def test_summary_no_blocking_after_resolve(client, upload_with_inconsistencies, db):
    errors = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_with_inconsistencies,
        DataInconsistency.severity == "error",
    ).all()

    for item in errors:
        client.patch(
            f"/api/inconsistencies/{item.id}",
            json={"status": "resolved", "resolution_note": "Fixed"},
        )

    resp = client.get(f"/api/inconsistencies/summary?upload_id={upload_with_inconsistencies}")
    assert resp.status_code == 200
    assert resp.json()["has_blocking_errors"] is False


def test_recheck(client, upload_with_inconsistencies):
    resp = client.post(f"/api/inconsistencies/{upload_with_inconsistencies}/recheck")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data


def test_recheck_not_found(client):
    resp = client.post("/api/inconsistencies/99999/recheck")
    assert resp.status_code == 404


def test_pagination(client, upload_with_inconsistencies):
    resp = client.get(
        f"/api/inconsistencies?upload_id={upload_with_inconsistencies}&limit=2&offset=0"
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = client.get(
        f"/api/inconsistencies?upload_id={upload_with_inconsistencies}&limit=2&offset=2"
    )
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2
