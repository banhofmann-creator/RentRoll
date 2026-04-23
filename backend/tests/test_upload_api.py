import os
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from app.database import Base, get_db
from app.config import settings

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
def setup_test_db():
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


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_csv(client, sample_csv_bytes):
    resp = client.post(
        "/api/upload",
        files={"file": ("test.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processing"
    upload_id = data["id"]

    time.sleep(2)

    detail = client.get(f"/api/uploads/{upload_id}")
    assert detail.status_code == 200
    d = detail.json()
    assert d["status"] == "complete", f"Upload failed: {d.get('error_message')}"
    assert d["stichtag"] == "2026-04-22"
    assert d["fund_label"] == "1 - GARBE"
    assert d["row_count"] == 3534
    assert d["data_row_count"] == 3298
    assert d["summary_row_count"] == 221
    assert d["orphan_row_count"] == 14


def test_upload_empty_file(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400


def test_list_uploads(client, sample_csv_bytes):
    client.post(
        "/api/upload",
        files={"file": ("test.csv", sample_csv_bytes, "text/csv")},
    )
    time.sleep(2)

    resp = client.get("/api/uploads")
    assert resp.status_code == 200
    uploads = resp.json()
    assert len(uploads) >= 1


def test_get_rows(client, sample_csv_bytes):
    resp = client.post(
        "/api/upload",
        files={"file": ("test.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    upload_id = resp.json()["id"]
    time.sleep(2)

    rows_resp = client.get(f"/api/uploads/{upload_id}/rows?row_type=data&limit=5")
    assert rows_resp.status_code == 200
    data = rows_resp.json()
    assert data["total"] == 3298
    assert len(data["rows"]) == 5
    assert data["rows"][0]["fund"] == "GLIFPLUSII"


def test_get_rows_filter_by_property(client, sample_csv_bytes):
    resp = client.post(
        "/api/upload",
        files={"file": ("test.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    upload_id = resp.json()["id"]
    time.sleep(2)

    rows_resp = client.get(f"/api/uploads/{upload_id}/rows?property_id=1001")
    assert rows_resp.status_code == 200
    data = rows_resp.json()
    assert data["total"] > 0
    for row in data["rows"]:
        assert row["property_id"] == "1001"


def test_delete_upload(client, sample_csv_bytes):
    resp = client.post(
        "/api/upload",
        files={"file": ("test.csv", sample_csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200
    upload_id = resp.json()["id"]
    time.sleep(2)

    del_resp = client.delete(f"/api/uploads/{upload_id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/uploads/{upload_id}")
    assert get_resp.status_code == 404
