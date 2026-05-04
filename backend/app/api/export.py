from __future__ import annotations

from dataclasses import asdict
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.channels.base import ExportMetadata
from app.channels.registry import get_channel, list_channels
from app.core.investor_pack import generate_investor_pack
from app.database import get_db
from app.models.database import RawRentRoll, ReportingPeriod

router = APIRouter(prefix="/export", tags=["export"])


class ChannelInfo(BaseModel):
    name: str
    description: str


class InvestorPackPreview(BaseModel):
    filename: str
    file_count: int
    files: list[str]


class PushRequest(BaseModel):
    period_id: int
    channel: str
    fund: str | None = None


class PushResultResponse(BaseModel):
    success: bool
    channel: str
    files_pushed: int
    destination: str
    errors: list[str]


def _normalize_fund_label(fund: str | None) -> str:
    return fund or "all_funds"


def _get_period_or_404(db: Session, period_id: int) -> ReportingPeriod:
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Reporting period not found")
    return period


def _selected_property_ids(db: Session, period: ReportingPeriod, fund: str | None) -> list[str]:
    if period.upload_id is None:
        return []

    query = db.query(RawRentRoll.property_id).filter(
        RawRentRoll.upload_id == period.upload_id,
        RawRentRoll.row_type.in_(["data", "orphan"]),
        RawRentRoll.property_id.isnot(None),
    )
    if fund is not None:
        query = query.filter(RawRentRoll.fund == fund)

    return [row[0] for row in query.distinct().order_by(RawRentRoll.property_id).all()]


def _generate_pack_or_error(db: Session, period_id: int, fund: str | None):
    try:
        return generate_investor_pack(db, period_id, fund=fund)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(404, message) from exc
        raise HTTPException(400, message) from exc


@router.get("/channels", response_model=list[ChannelInfo])
def export_channels():
    return list_channels()


@router.post("/investor-pack")
def download_investor_pack(
    period_id: int = Query(...),
    fund: str | None = Query(None),
    db: Session = Depends(get_db),
):
    zip_bytes, filename, _ = _generate_pack_or_error(db, period_id, fund)
    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/investor-pack/preview", response_model=InvestorPackPreview)
def preview_investor_pack(
    period_id: int = Query(...),
    fund: str | None = Query(None),
    db: Session = Depends(get_db),
):
    _, filename, export_files = _generate_pack_or_error(db, period_id, fund)
    return InvestorPackPreview(
        filename=filename,
        file_count=len(export_files),
        files=[export_file.filename for export_file in export_files],
    )


@router.post("/push", response_model=PushResultResponse)
def push_investor_pack(body: PushRequest, db: Session = Depends(get_db)):
    try:
        channel = get_channel(body.channel)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    period = _get_period_or_404(db, body.period_id)
    _, _, export_files = _generate_pack_or_error(db, body.period_id, body.fund)

    metadata = ExportMetadata(
        stichtag=period.stichtag,
        fund=_normalize_fund_label(body.fund),
        properties=_selected_property_ids(db, period, body.fund),
        reporting_period_id=period.id,
    )
    result = channel.push(export_files, metadata)
    return jsonable_encoder(asdict(result))
