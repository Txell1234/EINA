"""Prospective inquiry Q2FS API."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from models.user import User
from services.inquiry_export_service import build_inquiry_report_html
from services.inquiry_orchestrator_service import InquiryOrchestratorService

router = APIRouter(prefix="/api/prospective/inquiries", tags=["Prospective Inquiry Q2FS"])


class InquiryCreateIn(BaseModel):
    case_id: int
    question: str = Field(..., min_length=15)
    mode: Literal["full", "lite"] = "full"
    include_financial: bool = False
    financial_text: str = ""


@router.get("/case/{case_id}")
async def list_inquiries_for_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    return await InquiryOrchestratorService(db).list_for_case(case_id)


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
