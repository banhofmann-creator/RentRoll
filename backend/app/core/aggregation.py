from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.database import (
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    TenantMaster,
    TenantNameAlias,
)

UNIT_TYPE_ORDER = [
    "Büro", "Empore/Mezzanine", "Halle", "Freifläche",
    "Gastronomie", "Einzelhandel", "Hotel", "Rampe",
    "Wohnen", "Stellplätze", "Sonstige",
]

BVI_USE_TYPE_MAP = {
    "Büro": "OFFICE",
    "Empore/Mezzanine": "MEZZANINE",
    "Halle": "INDUSTRIAL",
    "Freifläche": "OUTDOOR",
    "Gastronomie": "GASTRONOMY",
    "Einzelhandel": "RETAIL",
    "Hotel": "HOTEL",
    "Rampe": "RAMP",
    "Wohnen": "RESIDENTIAL",
    "Stellplätze": "PARKING",
    "Sonstige": "OTHER",
}


def _dec(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def derive_use_type(area_by_type: dict[str, float]) -> str:
    total = sum(area_by_type.values())
    if total == 0:
        return "OTHER"
    for use_type, area in area_by_type.items():
        if area / total >= 0.75:
            return BVI_USE_TYPE_MAP.get(use_type, use_type)
    types_above_25 = [t for t, a in area_by_type.items() if a / total > 0.25]
    if len(types_above_25) <= 1:
        largest = max(area_by_type, key=area_by_type.get)
        return BVI_USE_TYPE_MAP.get(largest, largest)
    return "MISCELLANEOUS"


@dataclass
class Z1Row:
    bvi_fund_id: str | None
    stichtag: date | None
    currency: str = "EUR"
    bvi_tenant_id: str | None = None
    property_id: str | None = None
    tenant_name: str | None = None
    nace_sector: str | None = None
    pd_min: float | None = None
    pd_max: float | None = None
    contractual_rent: float = 0.0


@dataclass
class G2Row:
    fund_id: str | None = None
    stichtag: date | None = None
    currency: str = "EUR"
    property_id: str | None = None
    predecessor_id: str | None = None
    label: str | None = None
    prop_state: str | None = None
    ownership_type: str | None = None
    land_ownership: str | None = None

    country: str | None = None
    region: str | None = None
    zip_code: str | None = None
    city: str | None = None
    street: str | None = None
    location_quality: str | None = None

    green_building_vendor: str | None = None
    green_building_cert: str | None = None
    green_building_from: date | None = None
    green_building_to: date | None = None

    ownership_share: float | None = None
    purchase_date: date | None = None
    construction_year: int | None = None
    use_type_primary: str | None = None
    risk_style: str | None = None

    fair_value: float | None = None
    market_rental_value: float = 0.0
    market_net_yield: float | None = None
    last_valuation_date: date | None = None
    next_valuation_date: date | None = None

    area_measure: str = "M2"
    plot_size_sqm: float | None = None
    rentable_area: float = 0.0
    area_check: str | None = None
    tenant_count: int = 0
    floorspace_let: float = 0.0

    area_office: float = 0.0
    area_mezzanine: float = 0.0
    area_industrial: float = 0.0
    area_outdoor: float = 0.0
    area_gastronomy: float = 0.0
    area_retail: float = 0.0
    area_hotel: float = 0.0
    area_ramp: float = 0.0
    area_residential: float = 0.0
    area_other: float = 0.0

    parking_total: int = 0
    parking_let: int = 0
    debt_property: float | None = None
    shareholder_loan: float | None = None

    contractual_rent: float = 0.0
    rent_per_sqm: float | None = None
    gross_potential_income: float = 0.0

    rent_office: float = 0.0
    rent_mezzanine: float = 0.0
    rent_industrial_outdoor: float = 0.0
    rent_industrial: float = 0.0
    rent_outdoor: float = 0.0
    rent_gastronomy: float = 0.0
    rent_retail: float = 0.0
    rent_hotel: float = 0.0
    rent_ramp: float = 0.0
    rent_residential: float = 0.0
    rent_parking: float = 0.0
    rent_other: float = 0.0

    erv_total: float = 0.0
    erv_office: float = 0.0
    erv_mezzanine: float = 0.0
    erv_industrial: float = 0.0
    erv_outdoor: float = 0.0
    erv_gastronomy: float = 0.0
    erv_retail: float = 0.0
    erv_hotel: float = 0.0
    erv_ramp: float = 0.0
    erv_residential: float = 0.0
    erv_parking: float = 0.0
    erv_other: float = 0.0

    let_rent_office: float = 0.0
    let_rent_mezzanine: float = 0.0
    let_rent_industrial: float = 0.0
    let_rent_outdoor: float = 0.0
    let_rent_gastronomy: float = 0.0
    let_rent_retail: float = 0.0
    let_rent_hotel: float = 0.0
    let_rent_ramp: float = 0.0
    let_rent_residential: float = 0.0
    let_rent_parking: float = 0.0
    let_rent_other: float = 0.0

    vacant_rent_office: float = 0.0
    vacant_rent_mezzanine: float = 0.0
    vacant_rent_industrial: float = 0.0
    vacant_rent_outdoor: float = 0.0
    vacant_rent_gastronomy: float = 0.0
    vacant_rent_retail: float = 0.0
    vacant_rent_hotel: float = 0.0
    vacant_rent_ramp: float = 0.0
    vacant_rent_residential: float = 0.0
    vacant_rent_parking: float = 0.0
    vacant_rent_other: float = 0.0

    lease_expiry: dict = field(default_factory=dict)
    lease_term_avg: float | None = None
    tenant_count_2: int = 0

    co2_emissions: float | None = None
    co2_measurement_year: int | None = None
    energy_intensity: float | None = None
    energy_intensity_normalised: float | None = None
    data_quality_energy: str | None = None
    energy_reference_area: float | None = None
    crrem_floor_areas: dict | None = None
    exposure_fossil_fuels: float | None = None
    exposure_energy_inefficiency: float | None = None
    waste_total: float | None = None
    waste_recycled_pct: float | None = None
    epc_rating: str | None = None

    tech_clear_height: float | None = None
    tech_floor_load_capacity: float | None = None
    tech_loading_docks: int | None = None
    tech_sprinkler: str | None = None
    tech_lighting: str | None = None
    tech_heating: str | None = None
    maintenance: str | None = None

    reversion: float | None = None


def _build_fund_map(db: Session) -> dict[str, str | None]:
    mappings = db.query(FundMapping).all()
    return {m.csv_fund_name: m.bvi_fund_id for m in mappings}


def _build_tenant_map(db: Session) -> dict[str, TenantMaster]:
    tenants = db.query(TenantMaster).all()
    result: dict[str, TenantMaster] = {}
    for t in tenants:
        result[t.tenant_name_canonical.lower()] = t
    aliases = db.query(TenantNameAlias).all()
    for a in aliases:
        result[a.csv_tenant_name.lower()] = a.tenant_master
    return result


def _build_property_map(db: Session) -> dict[str, PropertyMaster]:
    props = db.query(PropertyMaster).all()
    return {p.property_id: p for p in props}


def aggregate_z1(
    db: Session,
    upload_id: int,
    stichtag: date | None = None,
) -> list[Z1Row]:
    fund_map = _build_fund_map(db)
    tenant_map = _build_tenant_map(db)

    rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .all()
    )

    groups: dict[tuple, dict] = {}
    for r in rows:
        if not r.tenant_name or r.tenant_name.upper() == "LEERSTAND":
            continue
        key = (r.fund, r.property_id, r.tenant_name)
        if key not in groups:
            groups[key] = {"rent": 0.0, "fund": r.fund, "property_id": r.property_id, "tenant_name": r.tenant_name}
        groups[key]["rent"] += _dec(r.annual_net_rent)

    result = []
    for (fund, prop_id, tenant_name), data in groups.items():
        bvi_fund = fund_map.get(fund)
        tm = tenant_map.get(tenant_name.lower())

        result.append(Z1Row(
            bvi_fund_id=bvi_fund,
            stichtag=stichtag,
            bvi_tenant_id=tm.bvi_tenant_id if tm else None,
            property_id=prop_id,
            tenant_name=tenant_name,
            nace_sector=tm.nace_sector if tm else None,
            pd_min=float(tm.pd_min) if tm and tm.pd_min else None,
            pd_max=float(tm.pd_max) if tm and tm.pd_max else None,
            contractual_rent=data["rent"],
        ))

    result.sort(key=lambda r: (r.bvi_fund_id or "", r.property_id or "", r.tenant_name or ""))
    return result


def _bucket_lease_expiry(lease_end: date | None, stichtag_year: int) -> str | None:
    if lease_end is None:
        return "open_ended"
    offset = lease_end.year - stichtag_year
    if offset < 0:
        offset = 0
    if offset <= 9:
        return str(offset)
    return "10"


_AREA_ATTR = {
    "Büro": "area_office",
    "Empore/Mezzanine": "area_mezzanine",
    "Halle": "area_industrial",
    "Freifläche": "area_outdoor",
    "Gastronomie": "area_gastronomy",
    "Einzelhandel": "area_retail",
    "Hotel": "area_hotel",
    "Rampe": "area_ramp",
    "Wohnen": "area_residential",
    "Sonstige": "area_other",
}

_RENT_ATTR = {
    "Büro": "rent_office",
    "Empore/Mezzanine": "rent_mezzanine",
    "Halle": "rent_industrial",
    "Freifläche": "rent_outdoor",
    "Gastronomie": "rent_gastronomy",
    "Einzelhandel": "rent_retail",
    "Hotel": "rent_hotel",
    "Rampe": "rent_ramp",
    "Wohnen": "rent_residential",
    "Stellplätze": "rent_parking",
    "Sonstige": "rent_other",
}

_ERV_ATTR = {
    "Büro": "erv_office",
    "Empore/Mezzanine": "erv_mezzanine",
    "Halle": "erv_industrial",
    "Freifläche": "erv_outdoor",
    "Gastronomie": "erv_gastronomy",
    "Einzelhandel": "erv_retail",
    "Hotel": "erv_hotel",
    "Rampe": "erv_ramp",
    "Wohnen": "erv_residential",
    "Stellplätze": "erv_parking",
    "Sonstige": "erv_other",
}

_LET_RENT_ATTR = {
    "Büro": "let_rent_office",
    "Empore/Mezzanine": "let_rent_mezzanine",
    "Halle": "let_rent_industrial",
    "Freifläche": "let_rent_outdoor",
    "Gastronomie": "let_rent_gastronomy",
    "Einzelhandel": "let_rent_retail",
    "Hotel": "let_rent_hotel",
    "Rampe": "let_rent_ramp",
    "Wohnen": "let_rent_residential",
    "Stellplätze": "let_rent_parking",
    "Sonstige": "let_rent_other",
}

_VACANT_RENT_ATTR = {
    "Büro": "vacant_rent_office",
    "Empore/Mezzanine": "vacant_rent_mezzanine",
    "Halle": "vacant_rent_industrial",
    "Freifläche": "vacant_rent_outdoor",
    "Gastronomie": "vacant_rent_gastronomy",
    "Einzelhandel": "vacant_rent_retail",
    "Hotel": "vacant_rent_hotel",
    "Rampe": "vacant_rent_ramp",
    "Wohnen": "vacant_rent_residential",
    "Stellplätze": "vacant_rent_parking",
    "Sonstige": "vacant_rent_other",
}


def aggregate_g2(
    db: Session,
    upload_id: int,
    stichtag: date | None = None,
) -> list[G2Row]:
    fund_map = _build_fund_map(db)
    prop_map = _build_property_map(db)

    data_rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .all()
    )

    summary_rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type == "property_summary",
        )
        .all()
    )
    summary_by_prop: dict[str, RawRentRoll] = {}
    for sr in summary_rows:
        if sr.property_id:
            summary_by_prop[sr.property_id] = sr

    props: dict[tuple[str, str], list[RawRentRoll]] = defaultdict(list)
    for r in data_rows:
        if r.fund and r.property_id:
            props[(r.fund, r.property_id)].append(r)

    stichtag_year = stichtag.year if stichtag else date.today().year

    result = []
    for (fund, prop_id), rows in props.items():
        g2 = G2Row()
        g2.fund_id = fund_map.get(fund)
        g2.stichtag = stichtag
        g2.property_id = prop_id

        pm = prop_map.get(prop_id)
        if pm:
            g2.predecessor_id = pm.predecessor_id
            g2.prop_state = pm.prop_state
            g2.ownership_type = pm.ownership_type
            g2.land_ownership = pm.land_ownership
            g2.country = pm.country
            g2.region = pm.region
            g2.zip_code = pm.zip_code
            g2.city = pm.city
            g2.street = pm.street
            g2.location_quality = pm.location_quality
            g2.green_building_vendor = pm.green_building_vendor
            g2.green_building_cert = pm.green_building_cert
            g2.green_building_from = pm.green_building_from
            g2.green_building_to = pm.green_building_to
            g2.ownership_share = float(pm.ownership_share) if pm.ownership_share is not None else None
            g2.purchase_date = pm.purchase_date
            g2.construction_year = pm.construction_year
            g2.risk_style = pm.risk_style
            g2.fair_value = float(pm.fair_value) if pm.fair_value is not None else None
            g2.market_net_yield = float(pm.market_net_yield) if pm.market_net_yield is not None else None
            g2.last_valuation_date = pm.last_valuation_date
            g2.next_valuation_date = pm.next_valuation_date
            g2.plot_size_sqm = float(pm.plot_size_sqm) if pm.plot_size_sqm is not None else None
            g2.debt_property = float(pm.debt_property) if pm.debt_property is not None else None
            g2.shareholder_loan = float(pm.shareholder_loan) if pm.shareholder_loan is not None else None
            g2.co2_emissions = float(pm.co2_emissions) if pm.co2_emissions is not None else None
            g2.co2_measurement_year = pm.co2_measurement_year
            g2.energy_intensity = float(pm.energy_intensity) if pm.energy_intensity is not None else None
            g2.energy_intensity_normalised = float(pm.energy_intensity_normalised) if pm.energy_intensity_normalised is not None else None
            g2.data_quality_energy = pm.data_quality_energy
            g2.energy_reference_area = float(pm.energy_reference_area) if pm.energy_reference_area is not None else None
            g2.crrem_floor_areas = pm.crrem_floor_areas_json
            g2.exposure_fossil_fuels = float(pm.exposure_fossil_fuels) if pm.exposure_fossil_fuels is not None else None
            g2.exposure_energy_inefficiency = float(pm.exposure_energy_inefficiency) if pm.exposure_energy_inefficiency is not None else None
            g2.waste_total = float(pm.waste_total) if pm.waste_total is not None else None
            g2.waste_recycled_pct = float(pm.waste_recycled_pct) if pm.waste_recycled_pct is not None else None
            g2.epc_rating = pm.epc_rating
            g2.tech_clear_height = float(pm.tech_clear_height) if pm.tech_clear_height is not None else None
            g2.tech_floor_load_capacity = float(pm.tech_floor_load_capacity) if pm.tech_floor_load_capacity is not None else None
            g2.tech_loading_docks = pm.tech_loading_docks
            g2.tech_sprinkler = pm.tech_sprinkler
            g2.tech_lighting = pm.tech_lighting
            g2.tech_heating = pm.tech_heating
            g2.maintenance = pm.maintenance

        summary = summary_by_prop.get(prop_id)
        if summary:
            g2.label = summary.property_name

        area_by_type: dict[str, float] = {}
        tenants: set[str] = set()
        lease_buckets: dict[str, float] = defaultdict(float)

        for r in rows:
            ut = r.unit_type or "Sonstige"
            area = _dec(r.area_sqm)
            rent = _dec(r.annual_net_rent)
            erv = _dec(r.erv_monthly) * 12
            market_rent = _dec(r.market_rent_monthly) * 12
            is_leerstand = r.tenant_name and r.tenant_name.upper() == "LEERSTAND"
            is_parking = ut == "Stellplätze"

            if not is_parking:
                g2.rentable_area += area
                area_attr = _AREA_ATTR.get(ut)
                if area_attr:
                    setattr(g2, area_attr, getattr(g2, area_attr) + area)
                    area_by_type[ut] = area_by_type.get(ut, 0) + area

                if not is_leerstand:
                    g2.floorspace_let += area

            if is_parking:
                parking = int(_dec(r.parking_count)) if r.parking_count else 0
                g2.parking_total += parking
                if not is_leerstand:
                    g2.parking_let += parking

            if not is_leerstand and r.tenant_name:
                tenants.add(r.tenant_name)

            g2.contractual_rent += rent

            erv_attr = _ERV_ATTR.get(ut)
            if erv_attr:
                setattr(g2, erv_attr, getattr(g2, erv_attr) + erv)
            g2.erv_total += erv

            if not is_leerstand:
                targeted = rent
                let_attr = _LET_RENT_ATTR.get(ut)
                if let_attr:
                    setattr(g2, let_attr, getattr(g2, let_attr) + rent)

                bucket = _bucket_lease_expiry(r.lease_end_actual, stichtag_year)
                if bucket:
                    lease_buckets[bucket] += rent
            else:
                if erv > 0:
                    targeted = erv
                elif market_rent > 0:
                    targeted = market_rent
                else:
                    targeted = rent
                vacant_attr = _VACANT_RENT_ATTR.get(ut)
                if vacant_attr:
                    setattr(g2, vacant_attr, getattr(g2, vacant_attr) + targeted)

            g2.gross_potential_income += targeted

            rent_attr = _RENT_ATTR.get(ut)
            if rent_attr:
                setattr(g2, rent_attr, getattr(g2, rent_attr) + targeted)

            if ut == "Halle":
                g2.rent_industrial_outdoor += targeted
            elif ut == "Freifläche":
                g2.rent_industrial_outdoor += targeted

        g2.tenant_count = len(tenants)
        g2.tenant_count_2 = g2.tenant_count
        g2.use_type_primary = derive_use_type(area_by_type)

        if g2.rentable_area > 0:
            g2.rent_per_sqm = g2.contractual_rent / g2.rentable_area

        if summary:
            g2.market_rental_value = _dec(summary.market_rent_monthly) * 12
            g2.lease_term_avg = float(summary.wault) if summary.wault else None

        if g2.contractual_rent and g2.contractual_rent != 0 and g2.market_rental_value:
            g2.reversion = (g2.market_rental_value - g2.contractual_rent) / g2.contractual_rent

        g2.lease_expiry = dict(lease_buckets)

        result.append(g2)

    result.sort(key=lambda r: (r.fund_id or "", r.property_id or ""))
    return result


@dataclass
class ValidationIssue:
    property_id: str
    field: str
    expected: float
    actual: float
    deviation_pct: float


def validate_aggregation(
    db: Session,
    upload_id: int,
) -> list[ValidationIssue]:
    data_rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type.in_(["data", "orphan"]),
        )
        .all()
    )
    summary_rows = (
        db.query(RawRentRoll)
        .filter(
            RawRentRoll.upload_id == upload_id,
            RawRentRoll.row_type == "property_summary",
        )
        .all()
    )
    summary_by_prop: dict[str, RawRentRoll] = {}
    for sr in summary_rows:
        if sr.property_id:
            summary_by_prop[sr.property_id] = sr

    agg: dict[str, dict] = defaultdict(lambda: {
        "area": 0.0, "rent": 0.0, "parking": 0, "market_rent": 0.0,
    })
    for r in data_rows:
        if not r.property_id:
            continue
        a = agg[r.property_id]
        ut = r.unit_type or "Sonstige"
        if ut != "Stellplätze":
            a["area"] += _dec(r.area_sqm)
        a["rent"] += _dec(r.annual_net_rent)
        a["parking"] += int(_dec(r.parking_count)) if r.parking_count else 0
        a["market_rent"] += _dec(r.market_rent_monthly) * 12

    issues = []
    checks = [
        ("rentable_area", "area", lambda s: _dec(s.area_sqm)),
        ("annual_net_rent", "rent", lambda s: _dec(s.annual_net_rent)),
        ("parking_count", "parking", lambda s: int(_dec(s.parking_count)) if s.parking_count else 0),
        ("market_rent", "market_rent", lambda s: _dec(s.market_rent_monthly) * 12),
    ]

    for prop_id, summary in summary_by_prop.items():
        if prop_id not in agg:
            continue
        a = agg[prop_id]
        for field_name, agg_key, summary_getter in checks:
            expected = summary_getter(summary)
            actual = a[agg_key]
            if expected == 0 and actual == 0:
                continue
            if expected == 0:
                deviation = 100.0
            else:
                deviation = abs(actual - expected) / abs(expected) * 100
            if deviation > 1.0:
                issues.append(ValidationIssue(
                    property_id=prop_id,
                    field=field_name,
                    expected=expected,
                    actual=actual,
                    deviation_pct=round(deviation, 2),
                ))

    issues.sort(key=lambda i: (-i.deviation_pct, i.property_id))
    return issues
