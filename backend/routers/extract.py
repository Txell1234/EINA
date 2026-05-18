"""
Extract Router - endpoints for the extraction pipeline
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from models.extract import ExtractedStatement
from services.extract_service import ExtractService
from services.prospective_service import ProspectiveService

router = APIRouter()


@router.post("/run/{case_id}")
async def run_extraction(case_id: int, db: AsyncSession = Depends(get_db)):
    svc = ExtractService(db)

    async def generator():
        async for event in svc.extract_from_case(case_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/statements/{case_id}")
async def get_statements(
    case_id: int,
    decision: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
    if decision:
        q = q.where(ExtractedStatement.cleanup_decision == decision)
    result = await db.execute(q.order_by(ExtractedStatement.extracted_at.desc()))
    stmts = result.scalars().all()
    return [
        {
            "id": s.id,
            "actor": s.actor,
            "actor_type": s.actor_type,
            "actor_importance": s.actor_importance,
            "statement": s.statement,
            "topic": s.topic,
            "framing": s.framing,
            "posture_toward": s.posture_toward,
            "posture_value": s.posture_value,
            "tone": s.tone,
            "tone_intensity": s.tone_intensity,
            "grounding_score": s.grounding_score,
            "cleanup_decision": s.cleanup_decision,
            "source_url": s.source_url,
            "source_date": s.source_date,
        }
        for s in stmts
    ]


@router.post("/cleanup/{case_id}")
async def run_cleanup(case_id: int, db: AsyncSession = Depends(get_db)):
    svc = ExtractService(db)
    result = await svc.cleanup_pass(case_id)
    return result


@router.get("/preview/{case_id}")
async def preview_suggestions(case_id: int, db: AsyncSession = Depends(get_db)):
    svc = ExtractService(db)
    variables = await svc.get_suggested_variables(case_id)
    actors = await svc.get_suggested_actors(case_id)
    return {"suggested_variables": variables, "suggested_actors": actors}


@router.post("/apply/{project_id}")
async def apply_to_project(
    project_id: int,
    case_id: int = Query(..., description="Cas OSINT font"),
    db: AsyncSession = Depends(get_db),
):
    extract_svc = ExtractService(db)
    prosp_svc = ProspectiveService(db)

    variables = await extract_svc.get_suggested_variables(case_id)
    actors = await extract_svc.get_suggested_actors(case_id)

    if variables:
        await prosp_svc.save_variables(project_id, variables)
    if actors:
        await prosp_svc.save_actors(project_id, actors)

    actors_frontend = []
    for a in actors:
        fins = a.get("fins", [])
        if isinstance(fins, list):
            fins_str = ", ".join(str(x) for x in fins)
        else:
            fins_str = str(fins or "")
        actors_frontend.append(
            {
                "code": a.get("code", ""),
                "name": a.get("name", ""),
                "force": float(a.get("force", 3)),
                "fins": fins_str,
            }
        )

    return {
        "variables_applied": len(variables),
        "actors_applied": len(actors),
        "variables": variables,
        "actors": actors_frontend,
        "message": "Matrius pre-poblades. Revisa i ajusta abans de calcular MIC-MAC i MACTOR.",
    }
