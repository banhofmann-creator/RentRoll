from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_changes, log_creation, log_deletion, snapshot
from app.database import get_db
from app.models.database import (
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    TenantMaster,
    TenantNameAlias,
)
from app.models.schemas import (
    FundMappingCreate,
    FundMappingResponse,
    FundMappingUpdate,
    PropertyMasterCreate,
    PropertyMasterResponse,
    PropertyMasterUpdate,
    TenantAliasCreate,
    TenantAliasResponse,
    TenantMasterCreate,
    TenantMasterResponse,
    TenantMasterUpdate,
    UnmappedItem,
)

router = APIRouter(tags=["master-data"])

FUND_FIELDS = ["csv_fund_name", "bvi_fund_id", "description"]
TENANT_FIELDS = [
    "tenant_name_canonical", "bvi_tenant_id", "nace_sector",
    "pd_min", "pd_max", "notes",
]
PROPERTY_FIELDS = [
    "property_id", "fund_csv_name", "predecessor_id", "prop_state",
    "ownership_type", "land_ownership", "country", "region", "zip_code",
    "city", "street", "location_quality", "green_building_vendor",
    "green_building_cert", "green_building_from", "green_building_to",
    "ownership_share", "purchase_date", "construction_year", "risk_style",
    "fair_value", "market_net_yield", "last_valuation_date",
    "next_valuation_date", "plot_size_sqm", "debt_property",
    "shareholder_loan", "co2_emissions", "co2_measurement_year",
    "energy_intensity", "energy_intensity_normalised", "data_quality_energy",
    "energy_reference_area", "crrem_floor_areas_json",
    "exposure_fossil_fuels", "exposure_energy_inefficiency", "waste_total",
    "waste_recycled_pct", "epc_rating", "tech_clear_height",
    "tech_floor_load_capacity", "tech_loading_docks", "tech_sprinkler",
    "tech_lighting", "tech_heating", "maintenance",
]


# ── Auto-resolution helpers ──────────────────────────────────────────

def _resolve_inconsistencies(db: Session, category: str, entity_id: str):
    db.query(DataInconsistency).filter(
        DataInconsistency.category == category,
        DataInconsistency.entity_id == entity_id,
        DataInconsistency.status == "open",
    ).update(
        {
            "status": "resolved",
            "resolution_note": "Auto-resolved: mapping created",
            "resolved_at": datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )


# ── Fund Mapping ─────────────────────────────────────────────────────

@router.get("/master-data/funds", response_model=list[FundMappingResponse])
def list_funds(
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(FundMapping)
    if search:
        query = query.filter(FundMapping.csv_fund_name.ilike(f"%{search}%"))
    return query.order_by(FundMapping.csv_fund_name).offset(offset).limit(limit).all()


@router.post("/master-data/funds", response_model=FundMappingResponse)
def create_fund(body: FundMappingCreate, db: Session = Depends(get_db)):
    existing = db.query(FundMapping).filter(
        FundMapping.csv_fund_name == body.csv_fund_name
    ).first()
    if existing:
        raise HTTPException(400, f"Fund mapping for '{body.csv_fund_name}' already exists")

    fund = FundMapping(**body.model_dump())
    db.add(fund)
    db.flush()
    log_creation(db, "fund_mapping", fund.id, snapshot(fund, FUND_FIELDS))
    _resolve_inconsistencies(db, "unmapped_fund", body.csv_fund_name)
    db.commit()
    db.refresh(fund)
    return fund


@router.patch("/master-data/funds/{fund_id}", response_model=FundMappingResponse)
def update_fund(fund_id: int, body: FundMappingUpdate, db: Session = Depends(get_db)):
    fund = db.get(FundMapping, fund_id)
    if not fund:
        raise HTTPException(404, "Fund mapping not found")

    old = snapshot(fund, FUND_FIELDS)
    updates = body.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(fund, field, val)
    log_changes(db, "fund_mapping", fund.id, old, updates)
    db.commit()
    db.refresh(fund)
    return fund


@router.delete("/master-data/funds/{fund_id}")
def delete_fund(fund_id: int, db: Session = Depends(get_db)):
    fund = db.get(FundMapping, fund_id)
    if not fund:
        raise HTTPException(404, "Fund mapping not found")
    log_deletion(db, "fund_mapping", fund.id, snapshot(fund, FUND_FIELDS))
    db.delete(fund)
    db.commit()
    return {"message": "Fund mapping deleted"}


# ── Tenant Master ────────────────────────────────────────────────────

@router.get("/master-data/tenants", response_model=list[TenantMasterResponse])
def list_tenants(
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(TenantMaster).options(selectinload(TenantMaster.aliases))
    if search:
        query = (
            query.outerjoin(TenantNameAlias)
            .filter(or_(
                TenantMaster.tenant_name_canonical.ilike(f"%{search}%"),
                TenantNameAlias.csv_tenant_name.ilike(f"%{search}%"),
            ))
            .distinct()
        )
    return (
        query.order_by(TenantMaster.tenant_name_canonical)
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("/master-data/tenants", response_model=TenantMasterResponse)
def create_tenant(body: TenantMasterCreate, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"initial_alias"})
    tenant = TenantMaster(**data)
    db.add(tenant)
    db.flush()
    log_creation(db, "tenant_master", tenant.id, snapshot(tenant, TENANT_FIELDS))

    if body.initial_alias:
        existing_alias = db.query(TenantNameAlias).filter(
            TenantNameAlias.csv_tenant_name == body.initial_alias
        ).first()
        if existing_alias:
            raise HTTPException(400, f"Alias '{body.initial_alias}' already exists")
        alias = TenantNameAlias(
            tenant_master_id=tenant.id,
            csv_tenant_name=body.initial_alias,
        )
        db.add(alias)
        db.flush()
        log_creation(db, "tenant_name_alias", alias.id, {"csv_tenant_name": body.initial_alias})
        _resolve_inconsistencies(db, "unmapped_tenant", body.initial_alias)

    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/master-data/tenants/{tenant_id}", response_model=TenantMasterResponse)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = (
        db.query(TenantMaster)
        .options(selectinload(TenantMaster.aliases))
        .filter(TenantMaster.id == tenant_id)
        .first()
    )
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return tenant


@router.patch("/master-data/tenants/{tenant_id}", response_model=TenantMasterResponse)
def update_tenant(tenant_id: int, body: TenantMasterUpdate, db: Session = Depends(get_db)):
    tenant = db.get(TenantMaster, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    old = snapshot(tenant, TENANT_FIELDS)
    updates = body.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(tenant, field, val)
    log_changes(db, "tenant_master", tenant.id, old, updates)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "A tenant with that BVI ID already exists")
    db.refresh(tenant)
    return tenant


@router.delete("/master-data/tenants/{tenant_id}")
def delete_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = (
        db.query(TenantMaster)
        .options(selectinload(TenantMaster.aliases))
        .filter(TenantMaster.id == tenant_id)
        .first()
    )
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    log_deletion(db, "tenant_master", tenant.id, snapshot(tenant, TENANT_FIELDS))
    db.delete(tenant)
    db.commit()
    return {"message": "Tenant deleted"}


# ── Tenant Aliases ───────────────────────────────────────────────────

@router.post(
    "/master-data/tenants/{tenant_id}/aliases",
    response_model=TenantAliasResponse,
)
def add_alias(tenant_id: int, body: TenantAliasCreate, db: Session = Depends(get_db)):
    tenant = db.get(TenantMaster, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    existing = db.query(TenantNameAlias).filter(
        TenantNameAlias.csv_tenant_name == body.csv_tenant_name
    ).first()
    if existing:
        raise HTTPException(400, f"Alias '{body.csv_tenant_name}' already exists")

    alias = TenantNameAlias(
        tenant_master_id=tenant_id,
        csv_tenant_name=body.csv_tenant_name,
        property_id=body.property_id,
    )
    db.add(alias)
    db.flush()
    log_creation(
        db, "tenant_name_alias", alias.id,
        {"csv_tenant_name": alias.csv_tenant_name, "property_id": alias.property_id},
    )
    _resolve_inconsistencies(db, "unmapped_tenant", body.csv_tenant_name)
    db.commit()
    db.refresh(alias)
    return alias


@router.delete("/master-data/tenants/{tenant_id}/aliases/{alias_id}")
def remove_alias(tenant_id: int, alias_id: int, db: Session = Depends(get_db)):
    alias = db.query(TenantNameAlias).filter(
        TenantNameAlias.id == alias_id,
        TenantNameAlias.tenant_master_id == tenant_id,
    ).first()
    if not alias:
        raise HTTPException(404, "Alias not found")
    log_deletion(
        db, "tenant_name_alias", alias.id,
        {"csv_tenant_name": alias.csv_tenant_name, "property_id": alias.property_id},
    )
    db.delete(alias)
    db.commit()
    return {"message": "Alias removed"}


# ── Property Master ──────────────────────────────────────────────────

@router.get("/master-data/properties", response_model=list[PropertyMasterResponse])
def list_properties(
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(PropertyMaster)
    if search:
        query = query.filter(or_(
            PropertyMaster.property_id.ilike(f"%{search}%"),
            PropertyMaster.city.ilike(f"%{search}%"),
        ))
    return query.order_by(PropertyMaster.property_id).offset(offset).limit(limit).all()


@router.post("/master-data/properties", response_model=PropertyMasterResponse)
def create_property(body: PropertyMasterCreate, db: Session = Depends(get_db)):
    existing = db.query(PropertyMaster).filter(
        PropertyMaster.property_id == body.property_id
    ).first()
    if existing:
        raise HTTPException(400, f"Property '{body.property_id}' already exists")

    prop = PropertyMaster(**body.model_dump())
    db.add(prop)
    db.flush()
    log_creation(db, "property_master", prop.id, snapshot(prop, PROPERTY_FIELDS))
    _resolve_inconsistencies(db, "missing_metadata", body.property_id)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/master-data/properties/{property_id}", response_model=PropertyMasterResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.get(PropertyMaster, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    return prop


@router.patch("/master-data/properties/{property_id}", response_model=PropertyMasterResponse)
def update_property(property_id: int, body: PropertyMasterUpdate, db: Session = Depends(get_db)):
    prop = db.get(PropertyMaster, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")

    old = snapshot(prop, PROPERTY_FIELDS)
    updates = body.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(prop, field, val)
    log_changes(db, "property_master", prop.id, old, updates)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/master-data/properties/{property_id}")
def delete_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.get(PropertyMaster, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    log_deletion(db, "property_master", prop.id, snapshot(prop, PROPERTY_FIELDS))
    db.delete(prop)
    db.commit()
    return {"message": "Property deleted"}


# ── Unmapped Items ───────────────────────────────────────────────────

CATEGORY_TO_ENTITY = {
    "unmapped_fund": "fund",
    "unmapped_tenant": "tenant",
    "missing_metadata": "property",
}


@router.get("/master-data/unmapped", response_model=list[UnmappedItem])
def list_unmapped(
    entity_type: str | None = None,
    db: Session = Depends(get_db),
):
    categories = list(CATEGORY_TO_ENTITY.keys())
    if entity_type:
        categories = [c for c, e in CATEGORY_TO_ENTITY.items() if e == entity_type]

    rows = (
        db.query(DataInconsistency)
        .filter(
            DataInconsistency.category.in_(categories),
            DataInconsistency.status == "open",
        )
        .all()
    )

    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    upload_counts: dict[tuple[str, str], set[int]] = defaultdict(set)

    for r in rows:
        etype = CATEGORY_TO_ENTITY.get(r.category, r.category)
        key = (etype, r.entity_id or "")
        grouped[key].append(r.id)
        upload_counts[key].add(r.upload_id)

    return [
        UnmappedItem(
            entity_type=etype,
            entity_id=eid,
            upload_count=len(upload_counts[(etype, eid)]),
            inconsistency_ids=ids,
        )
        for (etype, eid), ids in sorted(grouped.items())
    ]
