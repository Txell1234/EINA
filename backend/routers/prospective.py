"""
Prospective Analysis Router - MIC-MAC, MACTOR, morphological, scenarios
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from models.prospective import (
    MACTORObjective,
    ProspectiveActor,
    ProspectiveVariable,
    MorphComponent,
)
from services.prospective_service import ProspectiveService

router = APIRouter()


class ProjectCreate(BaseModel):
    case_id: Optional[int] = None
    title: str
    hypothesis: str = ""
    context: str = ""


class SaveVariablesRequest(BaseModel):
    variables: List[dict]


class MICMACRequest(BaseModel):
    matrix: List[List[int]]


class SaveActorsRequest(BaseModel):
    actors: List[dict]


class SaveObjectivesRequest(BaseModel):
    objectives: List[dict]


class MACTORRequest(BaseModel):
    postures: List[List[int]]


class SaveComponentsRequest(BaseModel):
    components: List[dict]


@router.get("/projects")
async def list_projects(
    case_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    projects = await svc.list_projects(case_id)
    return [
        {
            "id": p.id,
            "title": p.title,
            "case_id": p.case_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.post("/projects")
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)
    project = await svc.create_project(
        case_id=data.case_id,
        title=data.title,
        hypothesis=data.hypothesis,
        context=data.context,
    )
    return {"id": project.id, "title": project.title}


@router.get("/projects/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)
    project = await svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projecte no trobat")

    vars_r = await db.execute(
        select(ProspectiveVariable)
        .where(ProspectiveVariable.project_id == project_id)
        .order_by(ProspectiveVariable.order_index)
    )
    actors_r = await db.execute(
        select(ProspectiveActor)
        .where(ProspectiveActor.project_id == project_id)
        .order_by(ProspectiveActor.order_index)
    )
    objectives_r = await db.execute(
        select(MACTORObjective)
        .where(MACTORObjective.project_id == project_id)
        .order_by(MACTORObjective.order_index)
    )
    morph_r = await db.execute(
        select(MorphComponent)
        .where(MorphComponent.project_id == project_id)
        .order_by(MorphComponent.order_index)
    )

    return {
        "id": project.id,
        "title": project.title,
        "hypothesis": project.hypothesis,
        "context": project.context,
        "case_id": project.case_id,
        "variables": [
            {
                "code": v.code,
                "name": v.name,
                "type": v.var_type,
                "desc": v.description,
            }
            for v in vars_r.scalars().all()
        ],
        "actors": [
            {
                "code": a.code,
                "name": a.name,
                "force": a.force_score,
                "fins": ", ".join(a.strategic_goals or []),
            }
            for a in actors_r.scalars().all()
        ],
        "objectives": [
            {"id": o.code, "name": o.name} for o in objectives_r.scalars().all()
        ],
        "components": [
            {
                "id": m.code,
                "name": m.name,
                "configs": m.configurations or [],
            }
            for m in morph_r.scalars().all()
        ],
    }


@router.put("/projects/{project_id}/variables")
async def save_variables(
    project_id: int,
    data: SaveVariablesRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    await svc.save_variables(project_id, data.variables)
    return {"status": "ok", "count": len(data.variables)}


@router.post("/projects/{project_id}/micmac")
async def compute_micmac(
    project_id: int,
    data: MICMACRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.compute_micmac(project_id, data.matrix)


@router.put("/projects/{project_id}/actors")
async def save_actors(
    project_id: int,
    data: SaveActorsRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    await svc.save_actors(project_id, data.actors)
    return {"status": "ok", "count": len(data.actors)}


@router.put("/projects/{project_id}/objectives")
async def save_objectives(
    project_id: int,
    data: SaveObjectivesRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    await svc.save_objectives(project_id, data.objectives)
    return {"status": "ok", "count": len(data.objectives)}


@router.post("/projects/{project_id}/mactor")
async def compute_mactor(
    project_id: int,
    data: MACTORRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.compute_mactor(project_id, data.postures)


@router.put("/projects/{project_id}/components")
async def save_components(
    project_id: int,
    data: SaveComponentsRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    await svc.save_components(project_id, data.components)
    return {"status": "ok", "count": len(data.components)}


@router.get("/projects/{project_id}/scenarios")
async def get_scenarios(project_id: int, db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_scenarios(project_id)


@router.get("/projects/{project_id}/scenarios/stream")
async def stream_scenarios(project_id: int, db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")

    async def event_generator():
        try:
            async for event in svc.stream_scenarios(project_id):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
