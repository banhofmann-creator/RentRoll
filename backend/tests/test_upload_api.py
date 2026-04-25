import pytest

from app.api.upload import _process_upload
from app.models.database import CsvUpload


def _sync_upload(db, sample_csv_bytes):
    """Create upload and process synchronously."""
    upload = CsvUpload(filename="test.csv", status="processing")
    db.add(upload)
    db.commit()
    db.refresh(upload)
    _process_upload(upload.id, sample_csv_bytes, "test.csv")
    db.expire_all()
    return upload.id


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_csv(client, db, sample_csv_bytes):
    upload_id = _sync_upload(db, sample_csv_bytes)

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

    # List, row browsing, and row filtering — verify in same upload
    resp = client.get("/api/uploads")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    rows_resp = client.get(f"/api/uploads/{upload_id}/rows?row_type=data&limit=5")
    assert rows_resp.status_code == 200
    data = rows_resp.json()
    assert data["total"] == 3298
    assert len(data["rows"]) == 5
    assert data["rows"][0]["fund"] == "GLIFPLUSII"

    rows_resp = client.get(f"/api/uploads/{upload_id}/rows?property_id=1001")
    assert rows_resp.status_code == 200
    data = rows_resp.json()
    assert data["total"] > 0
    for row in data["rows"]:
        assert row["property_id"] == "1001"


def test_upload_empty_file(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400


def test_delete_upload(client, db, sample_csv_bytes):
    upload_id = _sync_upload(db, sample_csv_bytes)

    del_resp = client.delete(f"/api/uploads/{upload_id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/uploads/{upload_id}")
    assert get_resp.status_code == 404
