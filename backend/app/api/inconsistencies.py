from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database import CsvUpload, DataInconsistency
from app.models.schemas import InconsistencyListItem, InconsistencySummary, InconsistencyUpdate

router = APIRouter(tags=["inconsistencies"])


@router.get("/inconsistencies", response_model=list[InconsistencyListItem])
def list_inconsistencies(
    upload_id: int | None = None,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(DataInconsistency)
    if upload_id is not None:
        query = query.filter(DataInconsistency.upload_id == upload_id)
    if category:
        query = query.filter(DataInconsistency.category == category)
    if severity:
        query = query.filter(DataInconsistency.severity == severity)
    if status:
        query = query.filter(DataInconsistency.status == status)

    items = (
        query.order_by(DataInconsistency.created_at.desc(), DataInconsistency.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items


@router.get("/inconsistencies/summary", response_model=InconsistencySummary)
def inconsistency_summary(
    upload_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(DataInconsistency)
    if upload_id is not None:
        query = query.filter(DataInconsistency.upload_id == upload_id)

    rows = query.all()
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    has_blocking = False

    for r in rows:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.severity == "error" and r.status == "open":
            has_blocking = True

    return InconsistencySummary(
        total=len(rows),
        by_severity=by_severity,
        by_category=by_category,
        by_status=by_status,
        has_blocking_errors=has_blocking,
    )


@router.get("/inconsistencies/{inconsistency_id}", response_model=InconsistencyListItem)
def get_inconsistency(
    inconsistency_id: int,
    db: Session = Depends(get_db),
):
    item = db.get(DataInconsistency, inconsistency_id)
    if not item:
        raise HTTPException(404, "Inconsistency not found")
    return item


@router.patch("/inconsistencies/{inconsistency_id}", response_model=InconsistencyListItem)
def update_inconsistency(
    inconsistency_id: int,
    body: InconsistencyUpdate,
    db: Session = Depends(get_db),
):
    item = db.get(DataInconsistency, inconsistency_id)
    if not item:
        raise HTTPException(404, "Inconsistency not found")

    valid_statuses = {"open", "resolved", "acknowledged", "ignored"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    item.status = body.status
    if body.resolution_note is not None:
        item.resolution_note = body.resolution_note
    if body.resolved_by is not None:
        item.resolved_by = body.resolved_by

    if body.status in ("resolved", "acknowledged", "ignored"):
        item.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(item)
    return item


@router.post("/inconsistencies/{upload_id}/recheck")
def recheck_inconsistencies(
    upload_id: int,
    db: Session = Depends(get_db),
):
    upload = db.get(CsvUpload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")

    from app.core.inconsistency_detector import detect_inconsistencies
    detected = detect_inconsistencies(db, upload_id)
    db.add_all(detected)
    db.commit()

    return {"message": f"Recheck complete. {len(detected)} inconsistencies detected.", "count": len(detected)}
