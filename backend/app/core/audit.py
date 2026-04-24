from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.database import MasterDataAudit


def _serialize(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def snapshot(obj, fields: list[str]) -> dict:
    return {f: getattr(obj, f, None) for f in fields}


def log_changes(
    db: Session,
    table_name: str,
    record_id: int,
    old_values: dict,
    new_values: dict,
    change_source: str = "api",
    changed_by: str | None = None,
) -> list[MasterDataAudit]:
    entries = []
    for field, new_val in new_values.items():
        old_val = old_values.get(field)
        if _serialize(old_val) != _serialize(new_val):
            entry = MasterDataAudit(
                table_name=table_name,
                record_id=record_id,
                field_name=field,
                old_value=_serialize(old_val),
                new_value=_serialize(new_val),
                change_source=change_source,
                changed_by=changed_by,
            )
            db.add(entry)
            entries.append(entry)
    return entries


def log_creation(
    db: Session,
    table_name: str,
    record_id: int,
    values: dict,
    change_source: str = "api",
    changed_by: str | None = None,
) -> list[MasterDataAudit]:
    entries = []
    for field, val in values.items():
        if val is not None:
            entry = MasterDataAudit(
                table_name=table_name,
                record_id=record_id,
                field_name=field,
                old_value=None,
                new_value=_serialize(val),
                change_source=change_source,
                changed_by=changed_by,
            )
            db.add(entry)
            entries.append(entry)
    return entries


def log_deletion(
    db: Session,
    table_name: str,
    record_id: int,
    values: dict,
    change_source: str = "api",
    changed_by: str | None = None,
) -> list[MasterDataAudit]:
    entries = []
    for field, val in values.items():
        if val is not None:
            entry = MasterDataAudit(
                table_name=table_name,
                record_id=record_id,
                field_name=field,
                old_value=_serialize(val),
                new_value=None,
                change_source=change_source,
                changed_by=changed_by,
            )
            db.add(entry)
            entries.append(entry)
    return entries
