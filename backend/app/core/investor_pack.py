from __future__ import annotations

import io
import re
import zipfile

from sqlalchemy.orm import Session

from app.channels.base import ExportFile
from app.core.bvi_export import generate_bvi_xlsx
from app.core.slides import (
    generate_fund_summary,
    generate_lease_expiry_profile,
    generate_portfolio_overview,
    generate_property_factsheet,
)
from app.models.database import CsvUpload, RawRentRoll, ReportingPeriod


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "export"


def _selected_funds(db: Session, upload_id: int, fund: str | None) -> list[str]:
    funds = [
        row[0]
        for row in (
            db.query(RawRentRoll.fund)
            .filter(
                RawRentRoll.upload_id == upload_id,
                RawRentRoll.row_type.in_(["data", "orphan"]),
                RawRentRoll.fund.isnot(None),
            )
            .distinct()
            .order_by(RawRentRoll.fund)
            .all()
        )
    ]
    if fund is None:
        return funds
    if fund not in funds:
        raise ValueError(f"Fund not found in upload: {fund}")
    return [fund]


def _selected_properties(db: Session, upload_id: int, funds: list[str]) -> list[str]:
    return [
        row[0]
        for row in (
            db.query(RawRentRoll.property_id)
            .filter(
                RawRentRoll.upload_id == upload_id,
                RawRentRoll.row_type.in_(["data", "orphan"]),
                RawRentRoll.fund.in_(funds),
                RawRentRoll.property_id.isnot(None),
            )
            .distinct()
            .order_by(RawRentRoll.property_id)
            .all()
        )
    ]


def _pack_label(fund: str | None) -> str:
    return _safe_name(fund) if fund else "all_funds"


def generate_investor_pack(
    db: Session,
    period_id: int,
    fund: str | None = None,
) -> tuple[bytes, str, list[ExportFile]]:
    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise ValueError("Reporting period not found")
    if period.upload_id is None:
        raise ValueError("Reporting period has no source upload")

    upload = db.get(CsvUpload, period.upload_id)
    if not upload:
        raise ValueError("CSV upload not found")

    selected_funds = _selected_funds(db, upload.id, fund)
    selected_properties = _selected_properties(db, upload.id, selected_funds)
    is_draft = period.status != "finalized"
    label = _pack_label(fund)
    stichtag_label = period.stichtag.isoformat()

    export_files: list[ExportFile] = []

    bvi_filename = f"BVI_{label}_{stichtag_label}"
    if is_draft:
        bvi_filename += "_DRAFT"
    bvi_filename += ".xlsx"
    export_files.append(
        ExportFile(
            filename=bvi_filename,
            content=generate_bvi_xlsx(
                db,
                upload.id,
                stichtag=period.stichtag,
                is_draft=is_draft,
            ),
            file_type="xlsx",
            category="bvi_export",
        )
    )

    export_files.append(
        ExportFile(
            filename=f"portfolio_overview_{stichtag_label}.pptx",
            content=generate_portfolio_overview(db, upload.id).getvalue(),
            file_type="pptx",
            category="portfolio_overview",
        )
    )
    export_files.append(
        ExportFile(
            filename=f"lease_expiry_profile_{stichtag_label}.pptx",
            content=generate_lease_expiry_profile(db, upload.id).getvalue(),
            file_type="pptx",
            category="lease_expiry_profile",
        )
    )

    for fund_name in selected_funds:
        export_files.append(
            ExportFile(
                filename=f"fund_summary_{_safe_name(fund_name)}_{stichtag_label}.pptx",
                content=generate_fund_summary(db, upload.id, fund_name).getvalue(),
                file_type="pptx",
                category="fund_summary",
            )
        )

    for property_id in selected_properties:
        export_files.append(
            ExportFile(
                filename=f"factsheet_{_safe_name(property_id)}_{stichtag_label}.pptx",
                content=generate_property_factsheet(db, upload.id, property_id).getvalue(),
                file_type="pptx",
                category="factsheet",
            )
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for export_file in export_files:
            archive.writestr(export_file.filename, export_file.content)

    zip_filename = f"investor_pack_{label}_{stichtag_label}.zip"
    return zip_buffer.getvalue(), zip_filename, export_files
