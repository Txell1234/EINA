"""Prospective inquiry Q2FS API."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from models.user import User
from services.inquiry_export_service import build_inquiry_report_html, export_inquiry_pdf_bytes
from services.inquiry_orchestrator_service import InquiryOrchestratorService

router = APIRouter(prefix="/api/prospective/inquiries", tags=["Prospective Inquiry Q2FS"])


class InquiryCreateIn(BaseModel):
    case_id: int
    question: str = Field(..., min_length=15)
    mode: Literal["full", "lite"] = "full"
    include_financial: bool = False
    financial_text: str = ""


class ApplyWizardIn(BaseModel):
    project_id: int | None = None


class ApplyMonitorsIn(BaseModel):
    project_id: int


class InquiryScheduleIn(BaseModel):
    enabled: bool
    interval_hours: int = Field(24, ge=1, le=168)


@router.get("/case/{case_id}/compare")
async def compare_inquiries_for_case(
    case_id: int,
    ids: str | None = Query(None, description="IDs separats per coma (opcional)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    inquiry_ids = None
    if ids:
        inquiry_ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
    result = await InquiryOrchestratorService(db).compare_for_case(case_id, inquiry_ids=inquiry_ids)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="Cas no trobat")
    return result


@router.get("/case/{case_id}")
async def list_inquiries_for_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    return await InquiryOrchestratorService(db).list_for_case(case_id)


@router.get("/{inquiry_id}/wizard-link")
async def get_inquiry_wizard_link(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).wizard_link(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.get("/{inquiry_id}")
async def get_inquiry(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    return result


@router.post("")
async def create_inquiry(
    body: InquiryCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = InquiryOrchestratorService(db)
    try:
        row = await svc.create_inquiry(
            body.case_id,
            body.question,
            mode=body.mode,
            user_id=current_user.id,
            include_financial=body.include_financial,
            financial_text=body.financial_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"inquiry_id": row.id, "status": row.status, "parsed_trigger": row.parsed_trigger}


@router.post("/{inquiry_id}/run")
async def run_inquiry_stream(
    inquiry_id: int,
    force_refresh: bool = Query(False, description="Reexecutar passos encara que estiguin a la cache"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    svc = InquiryOrchestratorService(db)

    async def event_gen():
        async for event in svc.run_stream(inquiry_id, force_refresh=force_refresh):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/{inquiry_id}/rerun")
async def rerun_inquiry_stream(
    inquiry_id: int,
    force_refresh: bool = Query(True, description="Refrescar OSINT i pipeline en el re-run"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    svc = InquiryOrchestratorService(db)
    prep = await svc.prepare_rerun(inquiry_id)
    if not prep.get("ok"):
        raise HTTPException(status_code=404, detail=prep.get("error", "Not found"))

    async def event_gen():
        async for event in svc.run_stream(inquiry_id, force_refresh=force_refresh):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.patch("/{inquiry_id}/schedule")
async def set_inquiry_schedule(
    inquiry_id: int,
    body: InquiryScheduleIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).set_schedule(
        inquiry_id,
        enabled=body.enabled,
        interval_hours=body.interval_hours,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.get("/{inquiry_id}/audit")
async def get_inquiry_audit(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    detail = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not detail.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    return {
        "inquiry_id": inquiry_id,
        "run_count": detail.get("run_count"),
        "audit_trail": detail.get("audit_trail") or [],
        "answer_diff": detail.get("answer_diff"),
        "answer_history_count": len(detail.get("answer_history") or []),
    }


@router.get("/{inquiry_id}/morph-bootstrap")
async def get_morph_bootstrap(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).morph_bootstrap_for_inquiry(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.get("/{inquiry_id}/export/html")
async def export_inquiry_html(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    detail = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not detail.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    html = build_inquiry_report_html(detail)
    return HTMLResponse(content=html)


@router.get("/{inquiry_id}/export/pdf")
async def export_inquiry_pdf(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    detail = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not detail.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    pdf_bytes, meta = export_inquiry_pdf_bytes(detail)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=503,
            detail=f"PDF no disponible: {meta}. Usa export/html o instal·la WeasyPrint.",
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=inquiry_{inquiry_id}.pdf"},
    )


@router.get("/{inquiry_id}/cca-heatmap")
async def get_inquiry_cca_heatmap(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).morph_bootstrap_for_inquiry(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return {
        "inquiry_id": inquiry_id,
        "cca_heatmap": result.get("cca_heatmap"),
        "valid_combinations_count": result.get("valid_combinations_count"),
    }


@router.post("/{inquiry_id}/apply-to-wizard")
async def apply_inquiry_to_wizard(
    inquiry_id: int,
    body: ApplyWizardIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).apply_to_wizard(
        inquiry_id, project_id=body.project_id
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    return result


@router.post("/{inquiry_id}/apply-monitors")
async def apply_inquiry_monitors(
    inquiry_id: int,
    body: ApplyMonitorsIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).apply_monitors(
        inquiry_id, project_id=body.project_id
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Error"))
    return result


@router.post("/{inquiry_id}/synthesize")
async def synthesize_inquiry(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).synthesize(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result
