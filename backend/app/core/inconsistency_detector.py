import re
from decimal import Decimal

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.database import (
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    TenantNameAlias,
)

SUMMARY_PROP_RE = re.compile(r"^(\d+)\s*-\s*")

AGGREGATION_FIELDS = [
    ("area_sqm", "Area (sqm)"),
    ("annual_net_rent", "Annual net rent"),
    ("monthly_net_rent", "Monthly net rent"),
    ("parking_count", "Parking count"),
    ("market_rent_monthly", "Market rent (monthly)"),
    ("erv_monthly", "ERV (monthly)"),
]

TOLERANCE_PCT = 1.0


def detect_inconsistencies(db: Session, upload_id: int) -> list[DataInconsistency]:
    db.query(DataInconsistency).filter(
        DataInconsistency.upload_id == upload_id,
        DataInconsistency.category.in_([
            "aggregation_mismatch",
            "unmapped_tenant",
            "unmapped_fund",
            "missing_metadata",
        ]),
    ).delete(synchronize_session=False)

    results: list[DataInconsistency] = []
    results.extend(_detect_aggregation_mismatches(db, upload_id))
    results.extend(_detect_unmapped_tenants(db, upload_id))
    results.extend(_detect_unmapped_funds(db, upload_id))
    results.extend(_detect_missing_metadata(db, upload_id))
    return results


def _detect_aggregation_mismatches(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    agg_query = (
        db.query(
            RawRentRoll.property_id,
            func.sum(RawRentRoll.area_sqm).label("area_sqm"),
            func.sum(RawRentRoll.annual_net_rent).label("annual_net_rent"),
            func.sum(RawRentRoll.monthly_net_rent).label("monthly_net_rent"),
            func.sum(RawRentRoll.parking_count).label("parking_count"),
            func.sum(RawRentRoll.market_rent_monthly).label("market_rent_monthly"),
            func.sum(RawRentRoll.erv_monthly).label("erv_monthly"),
        )
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .group_by(RawRentRoll.property_id)
        .all()
    )

    aggregated = {}
    for row in agg_query:
        aggregated[row.property_id] = {
            "area_sqm": row.area_sqm,
            "annual_net_rent": row.annual_net_rent,
            "monthly_net_rent": row.monthly_net_rent,
            "parking_count": row.parking_count,
            "market_rent_monthly": row.market_rent_monthly,
            "erv_monthly": row.erv_monthly,
        }

    summary_rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type == "property_summary",
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for srow in summary_rows:
        m = SUMMARY_PROP_RE.match(srow.fund or "")
        if not m:
            continue
        prop_id = m.group(1)
        agg = aggregated.get(prop_id)
        if not agg:
            continue

        for field, label in AGGREGATION_FIELDS:
            summary_val = getattr(srow, field, None)
            agg_val = agg.get(field)

            if summary_val is None or agg_val is None:
                continue

            s = float(summary_val) if isinstance(summary_val, Decimal) else float(summary_val or 0)
            a = float(agg_val) if isinstance(agg_val, Decimal) else float(agg_val or 0)

            if s == 0 and a == 0:
                continue

            if s == 0:
                deviation = 100.0
            else:
                deviation = abs(a - s) / abs(s) * 100
            if deviation > TOLERANCE_PCT:
                results.append(DataInconsistency(
                    upload_id=upload_id,
                    category="aggregation_mismatch",
                    severity="warning",
                    entity_type="property",
                    entity_id=prop_id,
                    field_name=field,
                    expected_value=str(round(s, 2)),
                    actual_value=str(round(a, 2)),
                    deviation_pct=round(deviation, 2),
                    description=(
                        f"{label} mismatch for property {prop_id}: "
                        f"summary={round(s, 2)}, aggregated={round(a, 2)} "
                        f"(deviation {round(deviation, 1)}%)"
                    ),
                    status="open",
                ))

    return results


def _detect_unmapped_tenants(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    tenant_names = (
        db.query(distinct(RawRentRoll.tenant_name))
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.tenant_name.isnot(None),
            RawRentRoll.tenant_name != "LEERSTAND",
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for (name,) in tenant_names:
        alias = (
            db.query(TenantNameAlias)
            .filter(TenantNameAlias.csv_tenant_name == name)
            .first()
        )
        if alias is None:
            results.append(DataInconsistency(
                upload_id=upload_id,
                category="unmapped_tenant",
                severity="error",
                entity_type="tenant",
                entity_id=name,
                description=f"Tenant '{name}' has no mapping in tenant_name_alias",
                status="open",
            ))

    return results


def _detect_unmapped_funds(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    fund_names = (
        db.query(distinct(RawRentRoll.fund))
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.fund.isnot(None),
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for (name,) in fund_names:
        mapping = (
            db.query(FundMapping)
            .filter(FundMapping.csv_fund_name == name)
            .first()
        )
        if mapping is None:
            results.append(DataInconsistency(
                upload_id=upload_id,
                category="unmapped_fund",
                severity="error",
                entity_type="fund",
                entity_id=name,
                description=f"Fund '{name}' has no mapping in fund_mapping",
                status="open",
            ))

    return results


def _detect_missing_metadata(
    db: Session, upload_id: int
) -> list[DataInconsistency]:
    property_ids = (
        db.query(distinct(RawRentRoll.property_id))
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
            RawRentRoll.property_id.isnot(None),
        )
        .all()
    )

    results: list[DataInconsistency] = []
    for (prop_id,) in property_ids:
        pm = (
            db.query(PropertyMaster)
            .filter(PropertyMaster.property_id == prop_id)
            .first()
        )
        if pm is None:
            results.append(DataInconsistency(
                upload_id=upload_id,
                category="missing_metadata",
                severity="warning",
                entity_type="property",
                entity_id=prop_id,
                description=f"Property '{prop_id}' has no entry in property_master",
                status="open",
            ))

    return results
