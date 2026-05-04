from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database import (
    RawRentRoll,
    ReportingPeriod,
    SnapshotPropertyMaster,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Schemas ───────────────────────────────────────────────────────────

class PeriodKPI(BaseModel):
    period_id: int
    stichtag: str
    total_rent: float
    total_area: float
    vacant_area: float
    vacancy_rate: float
    tenant_count: int
    property_count: int
    fair_value: float | None
    total_debt: float | None
    wault_avg: float | None


class PeriodComparison(BaseModel):
    metric: str
    period_a_value: float | None
    period_b_value: float | None
    delta: float | None
    delta_pct: float | None


class ComparisonResponse(BaseModel):
    period_a: str
    period_b: str
    metrics: list[PeriodComparison]


class PropertySnapshot(BaseModel):
    stichtag: str
    rent: float
    area: float
    vacancy_rate: float
    tenant_count: int
    fair_value: float | None


# ── Helpers ───────────────────────────────────────────────────────────

def _csv_kpis(db: Session, period: ReportingPeriod) -> dict:
    """Aggregate KPIs from raw_rent_roll for a period's upload."""
    base = db.query(RawRentRoll).filter(
        RawRentRoll.upload_id == period.upload_id,
        RawRentRoll.row_type.in_(["data", "orphan"]),
    )

    rent_area = base.with_entities(
        func.coalesce(func.sum(RawRentRoll.annual_net_rent), 0),
        func.coalesce(func.sum(
            case(
                (RawRentRoll.unit_type != "Stellplätze", RawRentRoll.area_sqm),
                else_=0,
            )
        ), 0),
        func.coalesce(func.sum(
            case(
                (
                    (RawRentRoll.tenant_name == "LEERSTAND") &
                    (RawRentRoll.unit_type != "Stellplätze"),
                    RawRentRoll.area_sqm,
                ),
                else_=0,
            )
        ), 0),
    ).one()

    total_rent = float(rent_area[0] or 0)
    total_area = float(rent_area[1] or 0)
    vacant_area = float(rent_area[2] or 0)

    tenant_count = base.filter(
        RawRentRoll.tenant_name.isnot(None),
        RawRentRoll.tenant_name != "LEERSTAND",
    ).with_entities(
        func.count(func.distinct(RawRentRoll.tenant_name))
    ).scalar() or 0

    property_count = base.filter(
        RawRentRoll.property_id.isnot(None),
    ).with_entities(
        func.count(func.distinct(RawRentRoll.property_id))
    ).scalar() or 0

    wault_row = (
        db.query(func.avg(RawRentRoll.wault))
        .filter(
            RawRentRoll.upload_id == period.upload_id,
            RawRentRoll.row_type == "property_summary",
            RawRentRoll.wault.isnot(None),
        )
        .scalar()
    )

    return {
        "total_rent": total_rent,
        "total_area": total_area,
        "vacant_area": vacant_area,
        "vacancy_rate": round(vacant_area / total_area * 100, 2) if total_area > 0 else 0,
        "tenant_count": tenant_count,
        "property_count": property_count,
        "wault_avg": round(float(wault_row), 2) if wault_row is not None else None,
    }


def _snapshot_kpis(db: Session, period: ReportingPeriod) -> dict:
    """Aggregate KPIs from snapshot tables for a finalized period."""
    if period.status != "finalized":
        return {"fair_value": None, "total_debt": None}

    row = (
        db.query(
            func.sum(SnapshotPropertyMaster.fair_value),
            func.sum(SnapshotPropertyMaster.debt_property),
        )
        .filter(SnapshotPropertyMaster.reporting_period_id == period.id)
        .one()
    )
    return {
        "fair_value": float(row[0]) if row[0] is not None else None,
        "total_debt": float(row[1]) if row[1] is not None else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/kpis", response_model=list[PeriodKPI])
def get_portfolio_kpis(
    status: str = Query("finalized", pattern="^(finalized|all)$"),
    db: Session = Depends(get_db),
):
    query = db.query(ReportingPeriod).order_by(ReportingPeriod.stichtag)
    if status == "finalized":
        query = query.filter(ReportingPeriod.status == "finalized")

    periods = query.all()
    results = []
    for p in periods:
        csv = _csv_kpis(db, p)
        snap = _snapshot_kpis(db, p)
        results.append(PeriodKPI(
            period_id=p.id,
            stichtag=p.stichtag.isoformat(),
            **csv,
            **snap,
        ))
    return results


@router.get("/compare", response_model=ComparisonResponse)
def compare_periods(
    period_a: int = Query(...),
    period_b: int = Query(...),
    db: Session = Depends(get_db),
):
    pa = db.get(ReportingPeriod, period_a)
    pb = db.get(ReportingPeriod, period_b)
    if not pa or not pb:
        raise HTTPException(404, "Period not found")

    kpi_a = {**_csv_kpis(db, pa), **_snapshot_kpis(db, pa)}
    kpi_b = {**_csv_kpis(db, pb), **_snapshot_kpis(db, pb)}

    compare_fields = [
        "total_rent", "total_area", "vacant_area", "vacancy_rate",
        "tenant_count", "property_count", "fair_value", "total_debt", "wault_avg",
    ]

    metrics = []
    for field in compare_fields:
        va = kpi_a.get(field)
        vb = kpi_b.get(field)
        delta = None
        delta_pct = None
        if va is not None and vb is not None:
            delta = round(vb - va, 2)
            if va != 0:
                delta_pct = round(delta / abs(va) * 100, 2)
        metrics.append(PeriodComparison(
            metric=field,
            period_a_value=va,
            period_b_value=vb,
            delta=delta,
            delta_pct=delta_pct,
        ))

    return ComparisonResponse(
        period_a=pa.stichtag.isoformat(),
        period_b=pb.stichtag.isoformat(),
        metrics=metrics,
    )


@router.get("/properties/{property_id}/history", response_model=list[PropertySnapshot])
def get_property_history(
    property_id: str,
    db: Session = Depends(get_db),
):
    periods = (
        db.query(ReportingPeriod)
        .filter(ReportingPeriod.status == "finalized")
        .order_by(ReportingPeriod.stichtag)
        .all()
    )

    results = []
    for p in periods:
        base = db.query(RawRentRoll).filter(
            RawRentRoll.upload_id == p.upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.property_id == property_id,
        )

        agg = base.with_entities(
            func.coalesce(func.sum(RawRentRoll.annual_net_rent), 0),
            func.coalesce(func.sum(
                case(
                    (RawRentRoll.unit_type != "Stellplätze", RawRentRoll.area_sqm),
                    else_=0,
                )
            ), 0),
            func.coalesce(func.sum(
                case(
                    (
                        (RawRentRoll.tenant_name == "LEERSTAND") &
                        (RawRentRoll.unit_type != "Stellplätze"),
                        RawRentRoll.area_sqm,
                    ),
                    else_=0,
                )
            ), 0),
        ).one()

        rent = float(agg[0] or 0)
        area = float(agg[1] or 0)
        vacant = float(agg[2] or 0)

        tc = base.filter(
            RawRentRoll.tenant_name.isnot(None),
            RawRentRoll.tenant_name != "LEERSTAND",
        ).with_entities(
            func.count(func.distinct(RawRentRoll.tenant_name))
        ).scalar() or 0

        fv = (
            db.query(SnapshotPropertyMaster.fair_value)
            .filter(
                SnapshotPropertyMaster.reporting_period_id == p.id,
                SnapshotPropertyMaster.property_id == property_id,
            )
            .scalar()
        )

        if rent == 0 and area == 0 and tc == 0:
            continue

        results.append(PropertySnapshot(
            stichtag=p.stichtag.isoformat(),
            rent=rent,
            area=area,
            vacancy_rate=round(vacant / area * 100, 2) if area > 0 else 0,
            tenant_count=tc,
            fair_value=float(fv) if fv is not None else None,
        ))

    return results
