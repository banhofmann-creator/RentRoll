"""Report generation API — PPTX slides for properties, funds, and portfolio."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database import CsvUpload, RawRentRoll

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_upload(db: Session, upload_id: int) -> CsvUpload:
    upload = db.get(CsvUpload, upload_id)
    if not upload or upload.status != "complete":
        raise HTTPException(404, "Upload not found or not complete")
    return upload


@router.get("/property-factsheet")
def property_factsheet(
    upload_id: int = Query(...),
    property_id: str = Query(...),
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, upload_id)

    has_data = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.property_id == property_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .first()
    )
    if not has_data:
        raise HTTPException(404, f"No data for property {property_id}")

    from app.core.slides import generate_property_factsheet
    buf = generate_property_factsheet(db, upload_id, property_id)

    filename = f"factsheet_{property_id}_{upload.stichtag or 'draft'}.pptx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/portfolio-overview")
def portfolio_overview(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    _get_upload(db, upload_id)

    from app.core.slides import generate_portfolio_overview
    buf = generate_portfolio_overview(db, upload_id)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="portfolio_overview.pptx"'},
    )


@router.get("/lease-expiry")
def lease_expiry_profile(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    _get_upload(db, upload_id)

    from app.core.slides import generate_lease_expiry_profile
    buf = generate_lease_expiry_profile(db, upload_id)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="lease_expiry_profile.pptx"'},
    )


@router.get("/fund-summary")
def fund_summary(
    upload_id: int = Query(...),
    fund: str = Query(...),
    db: Session = Depends(get_db),
):
    upload = _get_upload(db, upload_id)

    has_data = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.fund == fund,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .first()
    )
    if not has_data:
        raise HTTPException(404, f"No data for fund {fund}")

    from app.core.slides import generate_fund_summary
    buf = generate_fund_summary(db, upload_id, fund)

    filename = f"fund_summary_{fund}_{upload.stichtag or 'draft'}.pptx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/available-funds")
def list_available_funds(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List distinct funds in an upload for the fund summary picker."""
    _get_upload(db, upload_id)

    funds = (
        db.query(RawRentRoll.fund)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.fund.isnot(None),
        )
        .distinct()
        .order_by(RawRentRoll.fund)
        .all()
    )
    return [f[0] for f in funds]


@router.get("/available-properties")
def list_available_properties(
    upload_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """List distinct property IDs in an upload for the factsheet picker."""
    _get_upload(db, upload_id)

    props = (
        db.query(RawRentRoll.property_id)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.property_id.isnot(None),
        )
        .distinct()
        .order_by(RawRentRoll.property_id)
        .all()
    )
    return [p[0] for p in props]
