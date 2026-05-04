"""Tool definitions and executors for the AI chatbot."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import (
    CsvUpload,
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    ReportingPeriod,
    SnapshotPropertyMaster,
    TenantMaster,
    TenantNameAlias,
)

TOOL_DEFINITIONS = [
    {
        "name": "query_raw_data",
        "description": (
            "Query the raw rent roll data. Returns up to 50 rows matching the filters. "
            "Use this to answer questions about specific tenants, properties, rents, areas, "
            "lease dates, and other CSV-level data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "upload_id": {"type": "integer", "description": "Filter by upload ID. If omitted, uses the latest complete upload."},
                "property_id": {"type": "string", "description": "Filter by property ID (exact match)."},
                "tenant_name": {"type": "string", "description": "Filter by tenant name (case-insensitive substring)."},
                "fund": {"type": "string", "description": "Filter by fund name (case-insensitive substring)."},
                "unit_type": {"type": "string", "description": "Filter by unit type (exact match)."},
                "row_type": {"type": "string", "enum": ["data", "orphan", "property_summary", "total"], "description": "Filter by row type. Defaults to data+orphan."},
                "limit": {"type": "integer", "description": "Max rows to return (default 20, max 50)."},
            },
            "required": [],
        },
    },
    {
        "name": "query_portfolio_summary",
        "description": (
            "Get a high-level summary of the portfolio from the latest upload: "
            "total properties, tenants, funds, total rent, total area, vacancy rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "upload_id": {"type": "integer", "description": "Upload ID. If omitted, uses the latest complete upload."},
            },
            "required": [],
        },
    },
    {
        "name": "search_tenants",
        "description": "Search tenant master records by name pattern. Returns canonical names, BVI IDs, aliases, and NACE sectors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name_pattern": {"type": "string", "description": "Search string (case-insensitive substring match)."},
            },
            "required": ["name_pattern"],
        },
    },
    {
        "name": "list_properties",
        "description": "List properties from property_master. Returns property IDs, cities, fund associations, and key financial fields.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search by property_id, city, or street (substring match)."},
                "limit": {"type": "integer", "description": "Max results (default 20, max 50)."},
            },
            "required": [],
        },
    },
    {
        "name": "list_inconsistencies",
        "description": "List data quality issues. Returns category, severity, description, and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "upload_id": {"type": "integer", "description": "Filter by upload ID."},
                "category": {"type": "string", "enum": ["aggregation_mismatch", "unmapped_tenant", "unmapped_fund", "missing_metadata"]},
                "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                "status": {"type": "string", "enum": ["open", "resolved", "acknowledged", "ignored"]},
                "limit": {"type": "integer", "description": "Max results (default 20, max 50)."},
            },
            "required": [],
        },
    },
    {
        "name": "list_periods",
        "description": "List all reporting periods with their status, stichtag dates, and upload references.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "compare_periods",
        "description": "Compare two reporting periods side by side. Returns deltas for rent, area, vacancy, fair value, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period_a_id": {"type": "integer", "description": "First period ID."},
                "period_b_id": {"type": "integer", "description": "Second period ID."},
            },
            "required": ["period_a_id", "period_b_id"],
        },
    },
    {
        "name": "update_tenant",
        "description": (
            "Update a tenant master record. REQUIRES USER CONFIRMATION. "
            "Can change canonical name, BVI tenant ID, or NACE sector."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "integer", "description": "Tenant master ID."},
                "tenant_name_canonical": {"type": "string"},
                "bvi_tenant_id": {"type": "string"},
                "nace_sector": {"type": "string"},
            },
            "required": ["tenant_id"],
        },
    },
    {
        "name": "update_property",
        "description": (
            "Update a property master record. REQUIRES USER CONFIRMATION. "
            "Can update any property_master field (city, country, fair_value, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "property_id": {"type": "string", "description": "The property ID (e.g. '7042')."},
                "fields": {
                    "type": "object",
                    "description": "Key-value pairs of fields to update.",
                },
            },
            "required": ["property_id", "fields"],
        },
    },
    {
        "name": "update_fund_mapping",
        "description": (
            "Update a fund mapping record. REQUIRES USER CONFIRMATION. "
            "Can set the BVI fund ID or description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "csv_fund_name": {"type": "string", "description": "The CSV fund name to update."},
                "bvi_fund_id": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["csv_fund_name"],
        },
    },
    {
        "name": "resolve_inconsistency",
        "description": (
            "Resolve a data inconsistency. REQUIRES USER CONFIRMATION. "
            "Sets status to resolved/acknowledged/ignored with a note."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "inconsistency_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["resolved", "acknowledged", "ignored"]},
                "resolution_note": {"type": "string"},
            },
            "required": ["inconsistency_id", "status"],
        },
    },
]

WRITE_TOOLS = {"update_tenant", "update_property", "update_fund_mapping", "resolve_inconsistency"}


def _latest_upload_id(db: Session) -> int | None:
    return (
        db.query(CsvUpload.id)
        .filter(CsvUpload.status == "complete")
        .order_by(CsvUpload.upload_date.desc())
        .limit(1)
        .scalar()
    )


def _serialize_row(row: RawRentRoll) -> dict:
    return {
        "property_id": row.property_id,
        "tenant_name": row.tenant_name,
        "fund": row.fund,
        "unit_type": row.unit_type,
        "area_sqm": float(row.area_sqm) if row.area_sqm else None,
        "annual_net_rent": float(row.annual_net_rent) if row.annual_net_rent else None,
        "monthly_net_rent": float(row.monthly_net_rent) if row.monthly_net_rent else None,
        "lease_start": str(row.lease_start) if row.lease_start else None,
        "lease_end_agreed": str(row.lease_end_agreed) if row.lease_end_agreed else None,
        "wault": float(row.wault) if row.wault else None,
        "row_type": row.row_type,
    }


def execute_tool(db: Session, tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result as a dict."""
    if tool_name == "query_raw_data":
        return _query_raw_data(db, tool_input)
    elif tool_name == "query_portfolio_summary":
        return _query_portfolio_summary(db, tool_input)
    elif tool_name == "search_tenants":
        return _search_tenants(db, tool_input)
    elif tool_name == "list_properties":
        return _list_properties(db, tool_input)
    elif tool_name == "list_inconsistencies":
        return _list_inconsistencies(db, tool_input)
    elif tool_name == "list_periods":
        return _list_periods(db)
    elif tool_name == "compare_periods":
        return _compare_periods(db, tool_input)
    elif tool_name == "update_tenant":
        return _update_tenant(db, tool_input)
    elif tool_name == "update_property":
        return _update_property(db, tool_input)
    elif tool_name == "update_fund_mapping":
        return _update_fund_mapping(db, tool_input)
    elif tool_name == "resolve_inconsistency":
        return _resolve_inconsistency(db, tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _query_raw_data(db: Session, inp: dict) -> dict:
    upload_id = inp.get("upload_id") or _latest_upload_id(db)
    if not upload_id:
        return {"error": "No completed uploads found."}

    q = db.query(RawRentRoll).filter(RawRentRoll.upload_id == upload_id)

    row_type = inp.get("row_type")
    if row_type:
        q = q.filter(RawRentRoll.row_type == row_type)
    else:
        q = q.filter(RawRentRoll.row_type.in_(["data", "orphan"]))

    if inp.get("property_id"):
        q = q.filter(RawRentRoll.property_id == inp["property_id"])
    if inp.get("tenant_name"):
        q = q.filter(RawRentRoll.tenant_name.ilike(f"%{inp['tenant_name']}%"))
    if inp.get("fund"):
        q = q.filter(RawRentRoll.fund.ilike(f"%{inp['fund']}%"))
    if inp.get("unit_type"):
        q = q.filter(RawRentRoll.unit_type == inp["unit_type"])

    limit = min(inp.get("limit", 20), 50)
    rows = q.order_by(RawRentRoll.row_number).limit(limit).all()
    total = q.count()

    return {
        "upload_id": upload_id,
        "total_matching": total,
        "rows_returned": len(rows),
        "rows": [_serialize_row(r) for r in rows],
    }


def _query_portfolio_summary(db: Session, inp: dict) -> dict:
    upload_id = inp.get("upload_id") or _latest_upload_id(db)
    if not upload_id:
        return {"error": "No completed uploads found."}

    upload = db.get(CsvUpload, upload_id)
    if not upload:
        return {"error": f"Upload {upload_id} not found."}

    base = db.query(RawRentRoll).filter(
        RawRentRoll.upload_id == upload_id,
        RawRentRoll.row_type.in_(["data", "orphan"]),
    )

    total_rent = float(base.with_entities(func.coalesce(func.sum(RawRentRoll.annual_net_rent), 0)).scalar() or 0)
    total_area = float(base.with_entities(func.coalesce(func.sum(RawRentRoll.area_sqm), 0)).scalar() or 0)
    vacant_area = float(
        base.filter(RawRentRoll.tenant_name == "LEERSTAND")
        .with_entities(func.coalesce(func.sum(RawRentRoll.area_sqm), 0))
        .scalar() or 0
    )
    tenant_count = base.filter(
        RawRentRoll.tenant_name.isnot(None),
        RawRentRoll.tenant_name != "LEERSTAND",
    ).with_entities(func.count(func.distinct(RawRentRoll.tenant_name))).scalar() or 0
    property_count = base.with_entities(func.count(func.distinct(RawRentRoll.property_id))).scalar() or 0
    fund_count = base.with_entities(func.count(func.distinct(RawRentRoll.fund))).scalar() or 0

    return {
        "upload_id": upload_id,
        "filename": upload.filename,
        "stichtag": str(upload.stichtag) if upload.stichtag else None,
        "total_properties": property_count,
        "total_tenants": tenant_count,
        "total_funds": fund_count,
        "total_annual_rent": round(total_rent, 2),
        "total_area_sqm": round(total_area, 2),
        "vacant_area_sqm": round(vacant_area, 2),
        "vacancy_rate_pct": round(vacant_area / total_area * 100, 2) if total_area > 0 else 0,
    }


def _search_tenants(db: Session, inp: dict) -> dict:
    pattern = inp["name_pattern"]
    tenants = (
        db.query(TenantMaster)
        .filter(TenantMaster.tenant_name_canonical.ilike(f"%{pattern}%"))
        .limit(20)
        .all()
    )

    if not tenants:
        aliases = (
            db.query(TenantNameAlias)
            .filter(TenantNameAlias.csv_tenant_name.ilike(f"%{pattern}%"))
            .limit(20)
            .all()
        )
        if aliases:
            tenant_ids = {a.tenant_master_id for a in aliases}
            tenants = db.query(TenantMaster).filter(TenantMaster.id.in_(tenant_ids)).all()

    return {
        "count": len(tenants),
        "tenants": [
            {
                "id": t.id,
                "canonical_name": t.tenant_name_canonical,
                "bvi_tenant_id": t.bvi_tenant_id,
                "nace_sector": t.nace_sector,
                "aliases": [a.csv_tenant_name for a in t.aliases],
            }
            for t in tenants
        ],
    }


def _list_properties(db: Session, inp: dict) -> dict:
    q = db.query(PropertyMaster)
    search = inp.get("search")
    if search:
        q = q.filter(
            PropertyMaster.property_id.ilike(f"%{search}%")
            | PropertyMaster.city.ilike(f"%{search}%")
            | PropertyMaster.street.ilike(f"%{search}%")
        )
    limit = min(inp.get("limit", 20), 50)
    props = q.order_by(PropertyMaster.property_id).limit(limit).all()

    return {
        "count": len(props),
        "properties": [
            {
                "id": p.id,
                "property_id": p.property_id,
                "city": p.city,
                "street": p.street,
                "country": p.country,
                "fund_csv_name": p.fund_csv_name,
                "fair_value": float(p.fair_value) if p.fair_value else None,
                "construction_year": p.construction_year,
            }
            for p in props
        ],
    }


def _list_inconsistencies(db: Session, inp: dict) -> dict:
    q = db.query(DataInconsistency)
    if inp.get("upload_id"):
        q = q.filter(DataInconsistency.upload_id == inp["upload_id"])
    if inp.get("category"):
        q = q.filter(DataInconsistency.category == inp["category"])
    if inp.get("severity"):
        q = q.filter(DataInconsistency.severity == inp["severity"])
    if inp.get("status"):
        q = q.filter(DataInconsistency.status == inp["status"])
    else:
        q = q.filter(DataInconsistency.status == "open")

    limit = min(inp.get("limit", 20), 50)
    items = q.order_by(DataInconsistency.id.desc()).limit(limit).all()
    total = q.count()

    return {
        "total": total,
        "returned": len(items),
        "items": [
            {
                "id": i.id,
                "category": i.category,
                "severity": i.severity,
                "entity_type": i.entity_type,
                "entity_id": i.entity_id,
                "description": i.description,
                "status": i.status,
            }
            for i in items
        ],
    }


def _list_periods(db: Session) -> dict:
    periods = db.query(ReportingPeriod).order_by(ReportingPeriod.stichtag).all()
    return {
        "count": len(periods),
        "periods": [
            {
                "id": p.id,
                "stichtag": str(p.stichtag) if p.stichtag else None,
                "status": p.status,
                "upload_id": p.upload_id,
                "finalized_at": str(p.finalized_at) if p.finalized_at else None,
            }
            for p in periods
        ],
    }


def _compare_periods(db: Session, inp: dict) -> dict:
    from app.api.analytics import _csv_kpis, _snapshot_kpis

    pa = db.get(ReportingPeriod, inp["period_a_id"])
    pb = db.get(ReportingPeriod, inp["period_b_id"])
    if not pa or not pb:
        return {"error": "One or both periods not found."}

    kpi_a = {**_csv_kpis(db, pa), **_snapshot_kpis(db, pa)}
    kpi_b = {**_csv_kpis(db, pb), **_snapshot_kpis(db, pb)}

    metrics = []
    for field in ["total_rent", "total_area", "vacant_area", "vacancy_rate",
                   "tenant_count", "property_count", "fair_value", "total_debt", "wault_avg"]:
        va = kpi_a.get(field)
        vb = kpi_b.get(field)
        delta = None
        if va is not None and vb is not None:
            delta = round(vb - va, 2)
        metrics.append({"metric": field, "period_a": va, "period_b": vb, "delta": delta})

    return {
        "period_a": str(pa.stichtag),
        "period_b": str(pb.stichtag),
        "metrics": metrics,
    }


def _update_tenant(db: Session, inp: dict) -> dict:
    tenant = db.get(TenantMaster, inp["tenant_id"])
    if not tenant:
        return {"error": f"Tenant {inp['tenant_id']} not found."}

    from app.core.audit import log_changes, snapshot
    update_fields = ["tenant_name_canonical", "bvi_tenant_id", "nace_sector"]
    changes = {}
    for field in update_fields:
        if field in inp and inp[field] is not None:
            changes[field] = inp[field]
    if not changes:
        return {"error": "No fields to update."}

    old = snapshot(tenant, list(changes.keys()))
    for k, v in changes.items():
        setattr(tenant, k, v)
    new = snapshot(tenant, list(changes.keys()))
    log_changes(db, "tenant_master", tenant.id, old, new, changed_by="chatbot")
    db.commit()

    return {"success": True, "tenant_id": tenant.id, "updated_fields": list(changes.keys())}


def _update_property(db: Session, inp: dict) -> dict:
    prop = (
        db.query(PropertyMaster)
        .filter(PropertyMaster.property_id == inp["property_id"])
        .first()
    )
    if not prop:
        return {"error": f"Property {inp['property_id']} not found."}

    from app.core.audit import log_changes, snapshot

    fields = inp.get("fields", {})
    if not fields:
        return {"error": "No fields to update."}

    valid_cols = {c.name for c in PropertyMaster.__table__.columns} - {"id"}
    invalid = set(fields.keys()) - valid_cols
    if invalid:
        return {"error": f"Invalid fields: {', '.join(invalid)}"}

    old = snapshot(prop, list(fields.keys()))
    for k, v in fields.items():
        setattr(prop, k, v)
    new = snapshot(prop, list(fields.keys()))
    log_changes(db, "property_master", prop.id, old, new, changed_by="chatbot")
    db.commit()

    return {"success": True, "property_id": prop.property_id, "updated_fields": list(fields.keys())}


def _update_fund_mapping(db: Session, inp: dict) -> dict:
    fund = (
        db.query(FundMapping)
        .filter(FundMapping.csv_fund_name == inp["csv_fund_name"])
        .first()
    )
    if not fund:
        return {"error": f"Fund mapping '{inp['csv_fund_name']}' not found."}

    from app.core.audit import log_changes, snapshot
    changes = {}
    for field in ["bvi_fund_id", "description"]:
        if field in inp and inp[field] is not None:
            changes[field] = inp[field]
    if not changes:
        return {"error": "No fields to update."}

    old = snapshot(fund, list(changes.keys()))
    for k, v in changes.items():
        setattr(fund, k, v)
    new = snapshot(fund, list(changes.keys()))
    log_changes(db, "fund_mapping", fund.id, old, new, changed_by="chatbot")
    db.commit()

    return {"success": True, "fund": fund.csv_fund_name, "updated_fields": list(changes.keys())}


def _resolve_inconsistency(db: Session, inp: dict) -> dict:
    item = db.get(DataInconsistency, inp["inconsistency_id"])
    if not item:
        return {"error": f"Inconsistency {inp['inconsistency_id']} not found."}

    item.status = inp["status"]
    item.resolution_note = inp.get("resolution_note")
    item.resolved_by = "chatbot"
    db.commit()

    return {"success": True, "inconsistency_id": item.id, "new_status": item.status}
