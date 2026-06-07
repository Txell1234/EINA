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
from services.inquiry_export_service import (
    build_inquiry_report_html,
    export_inquiry_docx_bytes,
    export_inquiry_pdf_bytes,
    prepare_inquiry_for_export,
)
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


class ParsePreviewIn(BaseModel):
    question: str = Field(..., min_length=15)
    case_id: int | None = None


class BatchRerunIn(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=10)
    force_refresh: bool = True


class BatchScheduleIn(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=50)
    enabled: bool
    interval_hours: int = Field(24, ge=1, le=168)


class BatchCreateIn(BaseModel):
    case_id: int
    questions: list[str] = Field(..., min_length=1, max_length=10)
    mode: Literal["full", "lite"] = "full"


class ReportMetaIn(BaseModel):
    is_saved: bool | None = None
    keep_forever: bool | None = None
    archived: bool | None = None
    report_title: str | None = Field(None, max_length=200)
    export_template: str | None = None
    notes: str | None = Field(None, max_length=500)


@router.get("/export/templates")
async def list_export_templates(current_user: User = Depends(get_current_user)):
    _ = current_user
    from services.report_templates import list_templates

    return {"templates": list_templates()}


@router.get("/reports/library")
async def inquiry_report_library(
    case_id: int | None = Query(None),
    saved_only: bool = Query(True),
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_report_meta_service import list_report_library

    return await list_report_library(
        db,
        case_id=case_id,
        saved_only=saved_only,
        include_archived=include_archived,
        limit=limit,
    )


@router.post("/create/batch")
async def create_inquiries_batch(
    body: BatchCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = InquiryOrchestratorService(db)
    created: list[dict[str, int | str]] = []
    for q in body.questions:
        question = q.strip()
        if len(question) < 15:
            continue
        try:
            row = await svc.create_inquiry(
                body.case_id,
                question,
                mode=body.mode,
                user_id=current_user.id,
            )
            created.append({"inquiry_id": row.id, "status": row.status, "question": question[:80]})
        except ValueError:
            continue
    if not created:
        raise HTTPException(status_code=400, detail="Cap pregunta vàlida (mínim 15 caràcters)")
    return {"created": created, "count": len(created)}


@router.get("/dashboard")
async def inquiry_dashboard(
    status: str | None = Query(None),
    case_id: int | None = Query(None),
    q: str | None = Query(None, description="Search question text"),
    mode: Literal["full", "lite"] | None = Query(None),
    scheduled_only: bool = Query(False),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    llm_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_dashboard_service import InquiryDashboardService

    return await InquiryDashboardService(db).list_dashboard(
        status=status,
        case_id=case_id,
        search=q,
        mode=mode,
        scheduled_only=scheduled_only,
        min_confidence=min_confidence,
        llm_only=llm_only,
        limit=limit,
    )


@router.post("/parse-preview")
async def parse_inquiry_preview(
    body: ParsePreviewIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from models.case import Case
    from services.parse_trigger_service import ParseTriggerService
    from sqlalchemy import select

    case_name = ""
    case_description = ""
    if body.case_id:
        r = await db.execute(select(Case).where(Case.id == body.case_id))
        case = r.scalar_one_or_none()
        if case:
            case_name = case.name or ""
            case_description = case.description or ""

    return await ParseTriggerService().parse_hybrid(
        body.question,
        case_name=case_name,
        case_description=case_description,
    )


@router.post("/rerun/batch")
async def rerun_inquiries_batch(
    body: BatchRerunIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_dashboard_service import InquiryDashboardService

    try:
        return await InquiryDashboardService(db).rerun_batch(
            body.ids,
            force_refresh=body.force_refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/batch-schedule")
async def batch_schedule_inquiries(
    body: BatchScheduleIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_dashboard_service import InquiryDashboardService

    try:
        return await InquiryDashboardService(db).batch_schedule(
            body.ids,
            enabled=body.enabled,
            interval_hours=body.interval_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/export/batch")
async def export_inquiries_batch(
    ids: str = Query(..., description="IDs separats per coma"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_dashboard_service import InquiryDashboardService

    inquiry_ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
    if not inquiry_ids:
        raise HTTPException(status_code=400, detail="IDs invalids")
    try:
        payload = await InquiryDashboardService(db).export_batch_zip(inquiry_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=inquiries_batch.zip"},
    )


@router.get("/export/executive")
async def export_executive_multi_inquiry(
    ids: str | None = Query(None, description="IDs separats per coma"),
    case_id: int | None = Query(None),
    lang: str = Query("ca"),
    output: Literal["html", "pdf"] = Query("html"),
    template: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_executive_report_service import build_executive_report_html

    inquiry_ids = None
    if ids:
        inquiry_ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
    if not inquiry_ids and case_id is None:
        raise HTTPException(status_code=400, detail="Cal case_id o ids")

    try:
        html_str = await build_executive_report_html(
            db,
            inquiry_ids=inquiry_ids,
            case_id=case_id,
            lang=lang,
            template=template,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if output == "pdf":
        from services.export_backends import ExportBackendError, render_pdf_from_html
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            render_pdf_from_html(html_str, tmp_path)
            pdf_bytes = tmp_path.read_bytes()
        except ExportBackendError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        finally:
            tmp_path.unlink(missing_ok=True)
        stamp = case_id or "selection"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=executive_inquiries_{stamp}.pdf"},
        )

    stamp = case_id or "selection"
    return HTMLResponse(
        content=html_str,
        headers={"Content-Disposition": f"inline; filename=executive_inquiries_{stamp}.html"},
    )


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


@router.get("/{inquiry_id}/scope-audit")
async def get_inquiry_scope_audit(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).scope_audit_detail(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    return result


@router.get("/{inquiry_id}/godet-status")
async def get_inquiry_godet_status(
    inquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    result = await InquiryOrchestratorService(db).godet_status(inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
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


@router.patch("/{inquiry_id}/report-meta")
async def patch_inquiry_report_meta(
    inquiry_id: int,
    body: ReportMetaIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_report_meta_service import update_report_meta

    result = await update_report_meta(
        db,
        inquiry_id,
        is_saved=body.is_saved,
        keep_forever=body.keep_forever,
        archived=body.archived,
        report_title=body.report_title,
        export_template=body.export_template,
        notes=body.notes,
    )
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Inquiry no trobada"))
    return result


@router.get("/{inquiry_id}/export/html")
async def export_inquiry_html(
    inquiry_id: int,
    lang: str | None = Query(None, description="ca | es | en"),
    template: str = Query("eina", description="eina | intelligence | economist | graphics"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    detail = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not detail.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    detail = await prepare_inquiry_for_export(db, detail, lang=lang)
    html = build_inquiry_report_html(detail, lang=lang, template=template)
    return HTMLResponse(content=html)


@router.get("/{inquiry_id}/export/pdf")
async def export_inquiry_pdf(
    inquiry_id: int,
    lang: str | None = Query(None, description="ca | es | en"),
    template: str = Query("eina", description="eina | intelligence | economist | graphics"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    detail = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not detail.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    detail = await prepare_inquiry_for_export(db, detail, lang=lang)
    pdf_bytes, meta = export_inquiry_pdf_bytes(detail, lang=lang, template=template)
    if pdf_bytes is None:
        raise HTTPException(
            status_code=503,
            detail=f"PDF no disponible: {meta}. Instal·la WeasyPrint (Linux/Docker) o Playwright (Windows: pip install playwright && python -m playwright install chromium).",
        )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=inquiry_{inquiry_id}.pdf"},
    )


@router.get("/{inquiry_id}/export/docx")
async def export_inquiry_docx(
    inquiry_id: int,
    lang: str | None = Query(None, description="ca | es | en"),
    template: str = Query("eina", description="eina | intelligence | economist | graphics"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    detail = await InquiryOrchestratorService(db).get_detail(inquiry_id)
    if not detail.get("found"):
        raise HTTPException(status_code=404, detail="Inquiry no trobada")
    detail = await prepare_inquiry_for_export(db, detail, lang=lang)
    try:
        docx_bytes = export_inquiry_docx_bytes(detail, lang=lang, template=template)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DOCX no disponible: {exc}") from exc
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=inquiry_{inquiry_id}.docx"},
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
