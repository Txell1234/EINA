"""Financial external report upload and crossover with EINA conclusions."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from models.user import User
from services.financial_crossover_service import FinancialCrossoverService
from services.financial_document_service import extract_text_from_bytes

router = APIRouter(prefix="/api/cases", tags=["Financial crossover"])


class FinancialReportTextIn(BaseModel):
    text: str = Field(..., min_length=50)
    source: str = Field(default="custom", max_length=64)
    title: str = Field(default="", max_length=200)
    source_url: str = Field(default="", max_length=500)
    enrich_llm: bool = False


class FinancialCrossoverIn(BaseModel):
    report_id: int | None = None
    text: str | None = Field(None, min_length=50)
    source: str = "custom"
    external_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    enrich_llm: bool = False


@router.get("/{case_id}/financial-reports")
async def list_financial_reports(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FinancialCrossoverService(db).list_reports(case_id)


@router.post("/{case_id}/financial-reports")
async def upload_financial_report_text(
    case_id: int,
    body: FinancialReportTextIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paste financial research text (PRAAMS InvestWatch, informes, notes)."""
    svc = FinancialCrossoverService(db)
    result = await svc.ingest_text(
        case_id,
        body.text,
        source=body.source,
        title=body.title,
        source_url=body.source_url,
        user_id=current_user.id,
        enrich_llm=body.enrich_llm,
    )
    return result


@router.post("/{case_id}/financial-reports/upload")
async def upload_financial_report_file(
    case_id: int,
    file: UploadFile = File(...),
    source: Annotated[str, Form()] = "custom",
    title: Annotated[str, Form()] = "",
    enrich_llm: Annotated[bool, Form()] = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload .txt, .md, .html or .pdf financial report."""
    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(status_code=400, detail="Fitxer massa gran (màx. 5 MB)")
    try:
        text = extract_text_from_bytes(data, file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if len(text.strip()) < 50:
        raise HTTPException(status_code=400, detail="No s'ha extret prou text del fitxer")

    svc = FinancialCrossoverService(db)
    return await svc.ingest_text(
        case_id,
        text,
        source=source,
        title=title or (file.filename or ""),
        filename=file.filename or "",
        user_id=current_user.id,
        enrich_llm=enrich_llm,
    )


@router.post("/{case_id}/financial-crossover")
async def run_financial_crossover(
    case_id: int,
    body: FinancialCrossoverIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cross-reference external financial report with EINA scenarios, SMIC, investments and Policy×Industry.
    Returns blended probabilities/indices with traceable reasoning (rule-based only, no LLM conclusions).
    """
    _ = current_user
    result = await FinancialCrossoverService(db).cross_reference(
        case_id,
        report_id=body.report_id,
        inline_text=body.text,
        source=body.source,
        external_weight=body.external_weight,
        enrich_llm=body.enrich_llm,
    )
    if not result.get("found"):
        raise HTTPException(status_code=400, detail=result.get("error", "Crossover failed"))
    return result
