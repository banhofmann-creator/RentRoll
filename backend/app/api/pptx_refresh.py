from __future__ import annotations

import traceback
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.upload import get_session_factory
from app.config import settings
from app.core.kpi_catalog import format_value, get_kpi, resolve_kpi_value
from app.core.pptx_kpi_resolver import resolve_with_ai
from app.core.pptx_patcher import Mapping, apply_token_mappings
from app.database import get_db
from app.models.database import PptxRefreshJob, ReportingPeriod
from app.parsers.pptx_ingestor import (
    find_token_candidates,
    ingest_pptx,
    token_candidate_to_dict,
)

router = APIRouter(prefix="/pptx", tags=["pptx"])

# Optional override used by tests to inject a fake Anthropic client.  Setting
# this attribute outside the test environment is unsupported.
_ai_client_override: object | None = None


def set_ai_client_override(client: object | None) -> None:
    """Test seam: route AI scans through the provided client."""
    global _ai_client_override
    _ai_client_override = client


class ApplyMapping(BaseModel):
    address: dict | list
    kpi_id: str


class AiConfirmation(BaseModel):
    idx: int
    kpi_id: str | None = None
    scope_choice: str | None = None  # "portfolio" or "skip" for ambiguous_scope


class ApplyRequest(BaseModel):
    period_id: int
    mappings: list[ApplyMapping] | None = None
    ai_confirmations: list[AiConfirmation] | None = None


def _safe_filename(filename: str) -> str:
    return filename.replace("..", "").replace("/", "_").replace("\\", "_")


def _pptx_root() -> Path:
    return Path(settings.upload_dir) / "pptx_refresh"


def _job_dir(job_id: int) -> Path:
    return _pptx_root() / str(job_id)


def _stored_path(relative_path: str) -> Path:
    return Path(settings.upload_dir) / relative_path


def _job_to_dict(job: PptxRefreshJob) -> dict:
    proposals_json = job.proposals_json or {}
    if isinstance(proposals_json, dict):
        mode = proposals_json.get("mode", "token")
        tokens = proposals_json.get("tokens", []) or []
        unknown_tokens = proposals_json.get("unknown_tokens", []) or []
        ai_proposals = proposals_json.get("proposals", []) or []
        summary = proposals_json.get("summary", {}) or {}
    else:
        mode = "token"
        tokens = []
        unknown_tokens = []
        ai_proposals = []
        summary = {}

    token_labels = [
        token.get("kpi_id") if isinstance(token, dict) else str(token)
        for token in tokens
    ]
    return {
        "id": job.id,
        "original_filename": job.original_filename,
        "original_blob_path": job.original_blob_path,
        "reporting_period_id": job.reporting_period_id,
        "period_status_at_refresh": job.period_status_at_refresh,
        "status": job.status,
        "proposals_json": job.proposals_json,
        "confirmed_json": job.confirmed_json,
        "proposals": {
            "mode": mode,
            "tokens": token_labels,
            "unknown_tokens": unknown_tokens,
            "ai_proposals": ai_proposals,
            "summary": summary,
        },
        "output_filename": job.output_filename,
        "output_blob_path": job.output_blob_path,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finalized_at": job.finalized_at.isoformat() if job.finalized_at else None,
        "created_by": job.created_by,
    }


def _process_pptx_upload(job_id: int, file_content: bytes):
    db = get_session_factory()()
    try:
        job = db.get(PptxRefreshJob, job_id)
        if not job:
            return

        elements = ingest_pptx(file_content)
        candidates, unknown_tokens = find_token_candidates(elements)
        job.proposals_json = {
            "mode": "token",
            "tokens": [token_candidate_to_dict(candidate) for candidate in candidates],
            "unknown_tokens": unknown_tokens,
        }
        job.status = "proposed"
        db.commit()
    except Exception as e:
        db.rollback()
        job = db.get(PptxRefreshJob, job_id)
        if job:
            job.status = "error"
            job.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            db.commit()
    finally:
        db.close()


def _process_pptx_scan(job_id: int, period_id: int):
    db = get_session_factory()()
    try:
        job = db.get(PptxRefreshJob, job_id)
        if not job:
            return

        source_path = _stored_path(job.original_blob_path)
        elements = ingest_pptx(source_path.read_bytes())
        proposals = resolve_with_ai(
            db,
            elements,
            period_id,
            client=_ai_client_override,
        )
        job.proposals_json = proposals
        job.reporting_period_id = period_id
        job.status = "proposed"
        job.error_message = None
        db.commit()
    except Exception as e:
        db.rollback()
        job = db.get(PptxRefreshJob, job_id)
        if job:
            job.status = "error"
            job.error_message = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            db.commit()
    finally:
        db.close()


@router.post("/upload")
async def upload_pptx(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Only .pptx files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    safe_name = _safe_filename(file.filename)
    job = PptxRefreshJob(
        original_filename=safe_name,
        original_blob_path="pending",
        status="uploaded",
        created_by=None,
    )
    db.add(job)
    db.flush()

    job_dir = _job_dir(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    source_path = job_dir / "source.pptx"
    source_path.write_bytes(content)
    job.original_blob_path = str(Path("pptx_refresh") / str(job.id) / "source.pptx")

    db.commit()
    db.refresh(job)

    background_tasks.add_task(_process_pptx_upload, job.id, content)
    return {"id": job.id, "status": job.status}


@router.get("/{job_id}")
def get_pptx_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(PptxRefreshJob, job_id)
    if not job:
        raise HTTPException(404, "PPTX refresh job not found")
    return _job_to_dict(job)


@router.post("/{job_id}/scan")
def scan_pptx_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    period_id: int = Query(..., description="Reporting period to source KPI values from"),
    db: Session = Depends(get_db),
):
    job = db.get(PptxRefreshJob, job_id)
    if not job:
        raise HTTPException(404, "PPTX refresh job not found")
    if not job.original_blob_path or job.original_blob_path == "pending":
        raise HTTPException(400, "Source deck not stored for this job")

    period = db.get(ReportingPeriod, period_id)
    if not period:
        raise HTTPException(404, "Period not found")

    if not _stored_path(job.original_blob_path).exists():
        raise HTTPException(404, "Source deck file missing on disk")

    job.status = "scanning"
    job.error_message = None
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_process_pptx_scan, job.id, period_id)
    return _job_to_dict(job)


def _find_proposal(tokens: list[dict], address: dict | list, kpi_id: str) -> dict | None:
    for token in tokens:
        if token.get("kpi_id") != kpi_id:
            continue
        token_address = token.get("address")
        if token_address == address:
            return token
        if isinstance(address, list) and isinstance(token_address, dict):
            ordered = [
                token_address.get("slide_idx"),
                token_address.get("shape_id"),
                token_address.get("kind"),
                token_address.get("row"),
                token_address.get("col"),
                token_address.get("paragraph_idx"),
                token_address.get("run_idx"),
            ]
            if ordered == address:
                return token
    return None


def _select_token_mappings(job: PptxRefreshJob, body: ApplyRequest) -> list[dict]:
    proposals = job.proposals_json if isinstance(job.proposals_json, dict) else {}
    tokens = proposals.get("tokens", [])
    if body.mappings is None:
        return tokens

    selected = []
    for mapping in body.mappings:
        proposal = _find_proposal(tokens, mapping.address, mapping.kpi_id)
        if proposal is not None:
            selected.append(proposal)
        else:
            selected.append({
                "address": mapping.address,
                "kpi_id": mapping.kpi_id,
                "full_text": f"{{{{{mapping.kpi_id}}}}}",
            })
    return selected


def _set_job_error(db: Session, job: PptxRefreshJob, message: str) -> dict:
    job.status = "error"
    job.error_message = message
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


def _apply_token_mode(
    db: Session,
    job: PptxRefreshJob,
    period: ReportingPeriod,
    body: ApplyRequest,
) -> dict:
    selected_tokens = _select_token_mappings(job, body)
    if not selected_tokens:
        return _set_job_error(db, job, "No supported PPTX tokens found to apply")

    patch_mappings: list[Mapping] = []
    confirmed: list[dict] = []
    for token in selected_tokens:
        kpi_id = token.get("kpi_id")
        spec = get_kpi(kpi_id)
        if not spec:
            return _set_job_error(db, job, f"Unknown KPI token: {kpi_id}")

        raw_value = resolve_kpi_value(db, kpi_id, period.id)
        if raw_value is None:
            return _set_job_error(db, job, f"No value available for KPI token: {kpi_id}")

        new_value = format_value(raw_value, spec.format_hint)
        original_value = token.get("full_text") or f"{{{{{kpi_id}}}}}"
        address = token.get("address")
        patch_mappings.append(
            Mapping(address=address, original_value=original_value, new_value=new_value)
        )
        confirmed.append({
            "address": address,
            "kpi_id": kpi_id,
            "original_value": original_value,
            "new_value": new_value,
            "mode": "token",
        })

    return _patch_and_finalize(db, job, period, patch_mappings, confirmed)


def _apply_ai_mode(
    db: Session,
    job: PptxRefreshJob,
    period: ReportingPeriod,
    body: ApplyRequest,
) -> dict:
    proposals_json = job.proposals_json if isinstance(job.proposals_json, dict) else {}
    proposals = proposals_json.get("proposals") or []
    if not proposals:
        return _set_job_error(db, job, "No AI proposals available; run /scan first")

    if body.ai_confirmations is None:
        return _set_job_error(db, job, "AI mode requires `ai_confirmations` to be specified")

    by_idx = {p.get("idx"): p for p in proposals if isinstance(p, dict)}
    patch_mappings: list[Mapping] = []
    confirmed: list[dict] = []

    for confirmation in body.ai_confirmations:
        proposal = by_idx.get(confirmation.idx)
        if proposal is None:
            return _set_job_error(db, job, f"AI proposal idx {confirmation.idx} not found")

        kind = proposal.get("kind")
        kpi_id: str | None = proposal.get("kpi_id")

        if kind == "ambiguous_scope":
            if confirmation.scope_choice == "skip":
                continue
            if confirmation.scope_choice != "portfolio":
                return _set_job_error(
                    db,
                    job,
                    f"Ambiguous proposal idx {confirmation.idx} requires scope_choice='portfolio' or 'skip'",
                )
            # DD-2: never silently fall back to the AI's candidate; require the
            # client to commit to a specific KPI before we apply anything.
            if not isinstance(confirmation.kpi_id, str) or not confirmation.kpi_id:
                return _set_job_error(
                    db,
                    job,
                    f"Ambiguous proposal idx {confirmation.idx} requires an explicit kpi_id",
                )
            kpi_id = confirmation.kpi_id
        elif kind == "mapping":
            if not isinstance(kpi_id, str) or not kpi_id:
                return _set_job_error(
                    db,
                    job,
                    f"Mapping proposal idx {confirmation.idx} is incomplete",
                )
        else:
            return _set_job_error(
                db,
                job,
                f"Proposal idx {confirmation.idx} cannot be applied (kind={kind})",
            )

        # Re-resolve the value against the apply-time period.  The proposal's
        # cached new_value was computed when the deck was scanned; if the user
        # changed the period selector between scan and apply, the cached value
        # would be wrong while the audit row records the apply-time period.
        spec = get_kpi(kpi_id)
        if spec is None:
            return _set_job_error(db, job, f"Unknown KPI for proposal idx {confirmation.idx}: {kpi_id}")
        raw_value = resolve_kpi_value(db, kpi_id, period.id)
        if raw_value is None:
            return _set_job_error(
                db,
                job,
                f"No value available for {kpi_id} in period {period.id}",
            )
        new_value = format_value(raw_value, spec.format_hint)

        address = proposal.get("address")
        original_value = proposal.get("original_value")
        if address is None or not isinstance(original_value, str):
            return _set_job_error(
                db,
                job,
                f"Proposal idx {confirmation.idx} missing address/original_value",
            )

        patch_mappings.append(
            Mapping(address=address, original_value=original_value, new_value=new_value)
        )
        confirmed.append({
            "idx": confirmation.idx,
            "address": address,
            "kpi_id": kpi_id,
            "original_value": original_value,
            "new_value": new_value,
            "mode": "ai",
            "scope_choice": confirmation.scope_choice,
        })

    if not patch_mappings:
        return _set_job_error(db, job, "No AI proposals were confirmed for application")

    return _patch_and_finalize(db, job, period, patch_mappings, confirmed)


def _patch_and_finalize(
    db: Session,
    job: PptxRefreshJob,
    period: ReportingPeriod,
    patch_mappings: list[Mapping],
    confirmed: list[dict],
) -> dict:
    source_bytes = _stored_path(job.original_blob_path).read_bytes()
    refreshed_bytes, changes = apply_token_mappings(source_bytes, patch_mappings)
    failed = [change for change in changes if not change.success]
    if failed:
        first = failed[0]
        return _set_job_error(
            db, job, f"Failed to apply token {first.original_value}: {first.reason}"
        )

    job_dir = _job_dir(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    output_path = job_dir / "refreshed.pptx"
    output_path.write_bytes(refreshed_bytes)

    stem = Path(job.original_filename).stem
    job.reporting_period_id = period.id
    job.period_status_at_refresh = period.status
    job.status = "complete"
    job.confirmed_json = confirmed
    job.output_filename = f"{stem}-refreshed.pptx"
    job.output_blob_path = str(Path("pptx_refresh") / str(job.id) / "refreshed.pptx")
    job.finalized_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@router.post("/{job_id}/apply")
def apply_pptx_refresh(job_id: int, body: ApplyRequest, db: Session = Depends(get_db)):
    job = db.get(PptxRefreshJob, job_id)
    if not job:
        raise HTTPException(404, "PPTX refresh job not found")

    period = db.get(ReportingPeriod, body.period_id)
    if not period:
        raise HTTPException(404, "Period not found")

    try:
        job.status = "applying"
        job.error_message = None
        db.commit()

        proposals_json = job.proposals_json if isinstance(job.proposals_json, dict) else {}
        mode = proposals_json.get("mode", "token")
        if body.ai_confirmations is not None or mode == "ai":
            return _apply_ai_mode(db, job, period, body)
        return _apply_token_mode(db, job, period, body)
    except Exception as e:
        db.rollback()
        job = db.get(PptxRefreshJob, job_id)
        if not job:
            raise
        job.status = "error"
        job.error_message = f"{type(e).__name__}: {e}"
        db.commit()
        db.refresh(job)
        return _job_to_dict(job)


@router.get("/{job_id}/download")
def download_pptx(job_id: int, db: Session = Depends(get_db)):
    job = db.get(PptxRefreshJob, job_id)
    if not job:
        raise HTTPException(404, "PPTX refresh job not found")
    if job.status != "complete" or not job.output_blob_path or not job.output_filename:
        raise HTTPException(400, "Refreshed deck is not available")

    output_path = _stored_path(job.output_blob_path)
    if not output_path.exists():
        raise HTTPException(404, "Refreshed deck file not found")

    return StreamingResponse(
        BytesIO(output_path.read_bytes()),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{job.output_filename}"'},
    )
