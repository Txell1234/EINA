"""
Extraction pipeline router - OSINT → structured statements
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from models.extract import ExtractedStatement
from services.extract_service import ExtractService
from services.prospective_service import ProspectiveService

from app.dependencies import get_current_user
from app.limiter import limiter
from models.user import User

router = APIRouter()


@router.post("/run/{case_id}")
@limiter.limit("5/minute")
async def run_extraction(
    request: Request,
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ExtractService(db)

    async def event_generator():
        try:
            async for event in svc.extract_from_case(case_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/statements/{case_id}")
async def list_statements(
    case_id: int,
    decision: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
    if decision:
        q = q.where(ExtractedStatement.cleanup_decision == decision)
    q = q.order_by(ExtractedStatement.extracted_at.desc())
    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "id": s.id,
            "actor": s.actor,
            "actor_type": s.actor_type,
            "actor_importance": s.actor_importance,
            "context": s.context,
            "statement": s.statement,
            "topic": s.topic,
            "framing": s.framing,
            "posture_toward": s.posture_toward,
            "posture_value": s.posture_value,
            "tone": s.tone,
            "tone_intensity": s.tone_intensity,
            "relevance_signals": s.relevance_signals,
            "grounding_score": s.grounding_score,
            "cleanup_decision": s.cleanup_decision,
            "cleanup_reason": s.cleanup_reason,
            "source_url": s.source_url,
            "source_date": s.source_date,
        }
        for s in rows
    ]


@router.post("/cleanup/{case_id}")
async def run_cleanup(case_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ExtractService(db)
    return await svc.cleanup_pass(case_id)


@router.get("/preview/{case_id}")
async def preview_suggestions(case_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ExtractService(db)
    variables = await svc.get_suggested_variables(case_id)
    actors = await svc.get_suggested_actors(case_id)
    return {"suggested_variables": variables, "suggested_actors": actors}


@router.post("/apply/{project_id}")
async def apply_to_project(
    project_id: int,
    case_id: int = Query(..., description="Cas OSINT font"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    extract_svc = ExtractService(db)
    prospective_svc = ProspectiveService(db)

    project = await prospective_svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projecte no trobat")

    variables = await extract_svc.get_suggested_variables(case_id)
    actors = await extract_svc.get_suggested_actors(case_id)
    result = await prospective_svc.apply_extraction(project_id, variables, actors)
    return result
