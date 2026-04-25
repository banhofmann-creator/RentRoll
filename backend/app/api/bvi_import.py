from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.audit import log_changes, log_creation, snapshot
from app.database import get_db
from app.models.database import DataInconsistency, PropertyMaster
from app.models.schemas import BviImportPreview, BviImportResult
from app.parsers.bvi_g2_importer import parse_bvi_g2

router = APIRouter(tags=["bvi-import"])

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


@router.post("/bvi-import/preview", response_model=BviImportPreview)
async def preview_bvi_import(
    file: UploadFile,
    db: Session = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    try:
        properties, warnings = parse_bvi_g2(content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    existing_ids = {
        row[0] for row in
        db.query(PropertyMaster.property_id).all()
    }

    parsed_ids = [p["property_id"] for p in properties]
    new_props = [pid for pid in parsed_ids if pid not in existing_ids]
    existing_props = [pid for pid in parsed_ids if pid in existing_ids]

    field_coverage: dict[str, int] = {}
    for prop in properties:
        for k, v in prop.items():
            if k.startswith("_") or k == "property_id":
                continue
            if v is not None:
                field_coverage[k] = field_coverage.get(k, 0) + 1

    bvi_fund_ids = sorted({
        p["_bvi_fund_id"] for p in properties if "_bvi_fund_id" in p
    })

    return BviImportPreview(
        properties_found=len(properties),
        new_properties=new_props,
        existing_properties=existing_props,
        field_coverage=field_coverage,
        bvi_fund_ids=bvi_fund_ids,
        warnings=warnings,
    )


@router.post("/bvi-import/execute", response_model=BviImportResult)
async def execute_bvi_import(
    file: UploadFile,
    mode: str = "fill_gaps",
    db: Session = Depends(get_db),
):
    if mode not in ("fill_gaps", "overwrite"):
        raise HTTPException(400, "Mode must be 'fill_gaps' or 'overwrite'")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    try:
        properties, warnings = parse_bvi_g2(content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    created = 0
    updated = 0
    skipped = 0

    for prop_data in properties:
        pid = prop_data["property_id"]
        prop_data.pop("_bvi_fund_id", None)

        existing = db.query(PropertyMaster).filter(
            PropertyMaster.property_id == pid
        ).first()

        if existing:
            old = snapshot(existing, PROPERTY_FIELDS)
            changes = {}
            for field, val in prop_data.items():
                if field == "property_id":
                    continue
                if mode == "fill_gaps" and getattr(existing, field, None) is not None:
                    continue
                if val != getattr(existing, field, None):
                    setattr(existing, field, val)
                    changes[field] = val

            if changes:
                log_changes(db, "property_master", existing.id, old, changes,
                            change_source="bvi_import")
                _resolve_missing_metadata(db, pid)
                updated += 1
            else:
                skipped += 1
        else:
            new_prop = PropertyMaster(**{
                k: v for k, v in prop_data.items() if not k.startswith("_")
            })
            db.add(new_prop)
            db.flush()
            log_creation(db, "property_master", new_prop.id,
                         snapshot(new_prop, PROPERTY_FIELDS),
                         change_source="bvi_import")
            _resolve_missing_metadata(db, pid)
            created += 1

    db.commit()

    return BviImportResult(
        created=created,
        updated=updated,
        skipped=skipped,
        warnings=warnings,
    )


def _resolve_missing_metadata(db: Session, property_id: str):
    db.query(DataInconsistency).filter(
        DataInconsistency.category == "missing_metadata",
        DataInconsistency.entity_id == property_id,
        DataInconsistency.status == "open",
    ).update(
        {
            "status": "resolved",
            "resolution_note": "Auto-resolved: BVI import",
            "resolved_at": datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )
