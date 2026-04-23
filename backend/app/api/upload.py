import os
import traceback
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.schema_validator import validate_schema
from app.database import SessionLocal, get_db
from app.models.database import CsvUpload, DataInconsistency, RawRentRoll
from app.models.schemas import UploadDetail, UploadListItem, UploadResponse
from app.parsers.garbe_mieterliste import GarbeMieterliste

router = APIRouter(tags=["upload"])

_session_factory = None


def get_session_factory():
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    return SessionLocal


def set_session_factory(factory):
    global _session_factory
    _session_factory = factory


def _process_upload(upload_id: int, file_content: bytes, filename: str):
    db = get_session_factory()()
    try:
        upload = db.query(CsvUpload).get(upload_id)
        if not upload:
            return

        parser = GarbeMieterliste()

        if not GarbeMieterliste.detect(file_content, filename):
            upload.status = "error"
            upload.error_message = "File format not recognized as GARBE Mieterliste CSV"
            db.commit()
            return

        result = parser.parse(file_content)
        schema_warnings = validate_schema(result.metadata)
        all_warnings = result.warnings + schema_warnings

        upload.stichtag = result.metadata.stichtag
        upload.fund_label = result.metadata.fund_label
        upload.column_fingerprint = result.metadata.column_fingerprint
        upload.column_headers_json = result.metadata.column_headers
        upload.parser_warnings_json = all_warnings
        upload.row_count = result.stats.get("total_rows", 0)
        upload.data_row_count = result.stats.get("data_rows", 0)
        upload.summary_row_count = result.stats.get("summary_rows", 0)
        upload.orphan_row_count = result.stats.get("orphan_rows", 0)

        db_rows = []
        for row_dict in result.rows:
            row_type = row_dict.pop("row_type")
            row_number = row_dict.pop("row_number")
            fund_inherited = row_dict.pop("fund_inherited", False)

            db_row = RawRentRoll(
                upload_id=upload_id,
                row_number=row_number,
                row_type=row_type,
                fund_inherited=fund_inherited,
                **row_dict,
            )
            db_rows.append(db_row)

        db.bulk_save_objects(db_rows)

        for w in schema_warnings:
            db.add(DataInconsistency(
                upload_id=upload_id,
                category="schema_drift",
                severity="warning",
                entity_type="upload",
                entity_id=str(upload_id),
                description=w,
                status="open",
            ))

        orphan_warnings = [w for w in result.warnings if "orphan" in w.lower()]
        for w in orphan_warnings:
            db.add(DataInconsistency(
                upload_id=upload_id,
                category="orphan_row",
                severity="info",
                entity_type="row",
                description=w,
                status="open",
            ))

        upload.status = "complete"
        db.commit()

    except Exception as e:
        db.rollback()
        upload = db.query(CsvUpload).get(upload_id)
        if upload:
            upload.status = "error"
            upload.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace("..", "").replace("/", "_").replace("\\", "_")
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    upload = CsvUpload(filename=safe_name, status="processing")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    background_tasks.add_task(_process_upload, upload.id, content, safe_name)

    return UploadResponse(
        id=upload.id,
        filename=safe_name,
        status="processing",
        message="Upload received, parsing in background",
    )


@router.get("/uploads", response_model=list[UploadListItem])
def list_uploads(db: Session = Depends(get_db)):
    uploads = db.query(CsvUpload).order_by(CsvUpload.upload_date.desc()).all()
    return uploads


@router.get("/uploads/{upload_id}", response_model=UploadDetail)
def get_upload(upload_id: int, db: Session = Depends(get_db)):
    upload = db.query(CsvUpload).get(upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    return upload


@router.get("/uploads/{upload_id}/rows")
def get_upload_rows(
    upload_id: int,
    row_type: str | None = None,
    fund: str | None = None,
    property_id: str | None = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    upload = db.query(CsvUpload).get(upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")

    query = db.query(RawRentRoll).filter(RawRentRoll.upload_id == upload_id)
    if row_type:
        query = query.filter(RawRentRoll.row_type == row_type)
    if fund:
        query = query.filter(RawRentRoll.fund == fund)
    if property_id:
        query = query.filter(RawRentRoll.property_id == property_id)

    total = query.count()
    rows = query.order_by(RawRentRoll.row_number).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": [
            {
                "id": r.id,
                "row_number": r.row_number,
                "row_type": r.row_type,
                "fund": r.fund,
                "fund_inherited": r.fund_inherited,
                "property_id": r.property_id,
                "property_name": r.property_name,
                "unit_id": r.unit_id,
                "unit_type": r.unit_type,
                "tenant_name": r.tenant_name,
                "area_sqm": float(r.area_sqm) if r.area_sqm is not None else None,
                "annual_net_rent": float(r.annual_net_rent) if r.annual_net_rent is not None else None,
                "monthly_net_rent": float(r.monthly_net_rent) if r.monthly_net_rent is not None else None,
                "market_rent_monthly": float(r.market_rent_monthly) if r.market_rent_monthly is not None else None,
                "lease_start": r.lease_start.isoformat() if r.lease_start else None,
                "lease_end_actual": r.lease_end_actual.isoformat() if r.lease_end_actual else None,
            }
            for r in rows
        ],
    }


@router.delete("/uploads/{upload_id}")
def delete_upload(upload_id: int, db: Session = Depends(get_db)):
    upload = db.query(CsvUpload).get(upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    db.delete(upload)
    db.commit()
    return {"message": "Upload deleted"}
