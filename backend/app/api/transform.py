from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.aggregation import aggregate_g2, aggregate_z1, validate_aggregation
from app.database import get_db
from app.models.database import CsvUpload
from app.models.schemas import (
    G2PreviewResponse,
    G2RowResponse,
    ValidationIssueResponse,
    ValidationResponse,
    Z1PreviewResponse,
    Z1RowResponse,
)

router = APIRouter(tags=["transform"])


def _get_upload(db: Session, upload_id: int) -> CsvUpload:
    upload = db.get(CsvUpload, upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    if upload.status != "complete":
        raise HTTPException(400, f"Upload not ready (status: {upload.status})")
    return upload


@router.get("/transform/z1/preview", response_model=Z1PreviewResponse)
def z1_preview(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, upload_id)
    rows = aggregate_z1(db, upload_id, stichtag=upload.stichtag)
    return Z1PreviewResponse(
        rows=[Z1RowResponse(**asdict(r)) for r in rows],
        total=len(rows),
    )


@router.get("/transform/g2/preview", response_model=G2PreviewResponse)
def g2_preview(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, upload_id)
    rows = aggregate_g2(db, upload_id, stichtag=upload.stichtag)
    return G2PreviewResponse(
        rows=[G2RowResponse(**asdict(r)) for r in rows],
        total=len(rows),
    )


@router.get("/transform/validation", response_model=ValidationResponse)
def validation_check(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, upload_id)
    issues = validate_aggregation(db, upload_id)

    summary_count = (
        db.query(CsvUpload)
        .filter(CsvUpload.id == upload_id)
        .first()
    )
    props_checked = summary_count.summary_row_count or 0

    return ValidationResponse(
        issues=[ValidationIssueResponse(**asdict(i)) for i in issues],
        total=len(issues),
        properties_checked=props_checked,
    )
