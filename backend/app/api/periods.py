from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.bvi_export import generate_bvi_xlsx
from app.database import get_db
from app.models.database import (
    CsvUpload,
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    ReportingPeriod,
    SnapshotFundMapping,
    SnapshotPropertyMaster,
    SnapshotTenantMaster,
    SnapshotTenantNameAlias,
    TenantMaster,
    TenantNameAlias,
)

router = APIRouter(tags=["periods"])


class PeriodCreate(BaseModel):
    upload_id: int


class PeriodResponse(BaseModel):
    id: int
    stichtag: str | None
    upload_id: int | None
    status: str
    finalized_at: str | None
    notes: str | None
    created_at: str

    model_config = {"from_attributes": True}


class FinalizeCheck(BaseModel):
    can_finalize: bool
    blocking_errors: int
    unmapped_tenants: int
    unmapped_funds: int
    property_completeness_pct: float
    warnings: list[str]


class FinalizeResult(BaseModel):
    status: str
    snapshot_counts: dict[str, int]


def _to_response(p: ReportingPeriod) -> dict:
    return {
        "id": p.id,
        "stichtag": p.stichtag.isoformat() if p.stichtag else None,
        "upload_id": p.upload_id,
        "status": p.status,
        "finalized_at": p.finalized_at.isoformat() if p.finalized_at else None,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


@router.get("/periods")
def list_periods(db: Session = Depends(get_db)):
    periods = db.query(ReportingPeriod).order_by(ReportingPeriod.stichtag.desc()).all()
    return [_to_response(p) for p in periods]


@router.post("/periods", status_code=201)
def create_period(body: PeriodCreate, db: Session = Depends(get_db)):
    upload = db.get(CsvUpload, body.upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    if upload.status != "complete":
        raise HTTPException(400, "Upload is not complete")
    if not upload.stichtag:
        raise HTTPException(400, "Upload has no stichtag")

    existing = db.query(ReportingPeriod).filter(
        ReportingPeriod.stichtag == upload.stichtag
    ).first()
    if existing:
        raise HTTPException(409, f"Period for {upload.stichtag} already exists (id={existing.id})")

    period = ReportingPeriod(
        stichtag=upload.stichtag,
        upload_id=upload.id,
        status="draft",
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return _to_response(period)


@router.get("/periods/{period_id}")
def get_period(period_id: int, db: Session = Depends(get_db)):
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    return _to_response(period)


CORE_PROPERTY_FIELDS = [
    "country", "city", "street", "prop_state", "ownership_type",
    "fair_value", "ownership_share",
]


@router.get("/periods/{period_id}/finalize-check", response_model=FinalizeCheck)
def finalize_check(period_id: int, db: Session = Depends(get_db)):
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Period not found")

    warnings = []

    blocking = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == period.upload_id,
        DataInconsistency.severity == "error",
        DataInconsistency.status == "open",
    ).count()

    unmapped_tenants = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == period.upload_id,
        DataInconsistency.category == "unmapped_tenant",
        DataInconsistency.status == "open",
    ).count()

    unmapped_funds = db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == period.upload_id,
        DataInconsistency.category == "unmapped_fund",
        DataInconsistency.status == "open",
    ).count()

    props = db.query(PropertyMaster).all()
    total_fields = len(props) * len(CORE_PROPERTY_FIELDS)
    filled = 0
    if props:
        for p in props:
            for f in CORE_PROPERTY_FIELDS:
                if getattr(p, f, None) is not None:
                    filled += 1
    completeness = (filled / total_fields * 100) if total_fields > 0 else 100.0

    if blocking > 0:
        warnings.append(f"{blocking} unresolved error(s)")
    if unmapped_tenants > 0:
        warnings.append(f"{unmapped_tenants} unmapped tenant(s)")
    if unmapped_funds > 0:
        warnings.append(f"{unmapped_funds} unmapped fund(s)")
    if completeness < 70:
        warnings.append(f"Property completeness {completeness:.0f}% (below 70% threshold)")

    can_finalize = blocking == 0 and unmapped_tenants == 0 and unmapped_funds == 0

    return FinalizeCheck(
        can_finalize=can_finalize,
        blocking_errors=blocking,
        unmapped_tenants=unmapped_tenants,
        unmapped_funds=unmapped_funds,
        property_completeness_pct=round(completeness, 1),
        warnings=warnings,
    )


@router.post("/periods/{period_id}/finalize", response_model=FinalizeResult)
def finalize_period(period_id: int, db: Session = Depends(get_db)):
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    if period.status == "finalized":
        raise HTTPException(400, "Period is already finalized")

    counts = _create_snapshot(db, period)

    period.status = "finalized"
    period.finalized_at = datetime.now(timezone.utc)
    db.commit()

    return FinalizeResult(status="finalized", snapshot_counts=counts)


def _create_snapshot(db: Session, period: ReportingPeriod) -> dict[str, int]:
    counts = {}

    props = db.query(PropertyMaster).all()
    for p in props:
        sp = SnapshotPropertyMaster(reporting_period_id=period.id)
        for col in PropertyMaster.__table__.columns:
            if col.name in ("id",):
                continue
            setattr(sp, col.name, getattr(p, col.name, None))
        db.add(sp)
    counts["properties"] = len(props)

    tenants = db.query(TenantMaster).all()
    tenant_id_map: dict[int, int] = {}
    for t in tenants:
        st = SnapshotTenantMaster(
            reporting_period_id=period.id,
            bvi_tenant_id=t.bvi_tenant_id,
            tenant_name_canonical=t.tenant_name_canonical,
            nace_sector=t.nace_sector,
            pd_min=t.pd_min,
            pd_max=t.pd_max,
            notes=t.notes,
        )
        db.add(st)
        db.flush()
        tenant_id_map[t.id] = st.id
    counts["tenants"] = len(tenants)

    aliases = db.query(TenantNameAlias).all()
    for a in aliases:
        snap_tenant_id = tenant_id_map.get(a.tenant_master_id)
        if snap_tenant_id:
            sa = SnapshotTenantNameAlias(
                reporting_period_id=period.id,
                snapshot_tenant_master_id=snap_tenant_id,
                csv_tenant_name=a.csv_tenant_name,
                property_id=a.property_id,
            )
            db.add(sa)
    counts["aliases"] = len(aliases)

    funds = db.query(FundMapping).all()
    for f in funds:
        sf = SnapshotFundMapping(
            reporting_period_id=period.id,
            csv_fund_name=f.csv_fund_name,
            bvi_fund_id=f.bvi_fund_id,
            description=f.description,
        )
        db.add(sf)
    counts["funds"] = len(funds)

    db.flush()
    return counts


@router.get("/periods/{period_id}/export")
def export_period(period_id: int, db: Session = Depends(get_db)):
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Period not found")

    is_draft = period.status != "finalized"
    xlsx_bytes = generate_bvi_xlsx(
        db, period.upload_id, stichtag=period.stichtag, is_draft=is_draft,
    )

    filename = f"BVI_{period.stichtag or 'export'}"
    if is_draft:
        filename += "_DRAFT"
    filename += ".xlsx"

    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/periods/{period_id}")
def delete_period(period_id: int, db: Session = Depends(get_db)):
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    if period.status == "finalized":
        raise HTTPException(400, "Cannot delete a finalized period")
    db.delete(period)
    db.commit()
    return {"status": "deleted"}
