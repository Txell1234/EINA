"""
Prospective Analysis Router
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from models.prospective import ProspectiveScenario
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
    return {
        "id": project.id,
        "title": project.title,
        "hypothesis": project.hypothesis,
        "context": project.context,
        "case_id": project.case_id,
    }


@router.put("/projects/{project_id}/variables")
async def save_variables(
    project_id: int,
    data: SaveVariablesRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    n = await svc.save_variables(project_id, data.variables)
    return {"saved": n}


@router.post("/projects/{project_id}/micmac")
async def compute_micmac(
    project_id: int,
    data: MICMACRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    result = await svc.compute_micmac(project_id, data.matrix)
    return result


@router.put("/projects/{project_id}/actors")
async def save_actors(
    project_id: int,
    data: SaveActorsRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    n = await svc.save_actors(project_id, data.actors)
    return {"saved": n}


@router.put("/projects/{project_id}/objectives")
async def save_objectives(
    project_id: int,
    data: SaveObjectivesRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    n = await svc.save_objectives(project_id, data.objectives)
    return {"saved": n}


@router.post("/projects/{project_id}/mactor")
async def compute_mactor(
    project_id: int,
    data: MACTORRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    result = await svc.compute_mactor(project_id, data.postures)
    return result


@router.put("/projects/{project_id}/components")
async def save_components(
    project_id: int,
    data: SaveComponentsRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    n = await svc.save_components(project_id, data.components)
    return {"saved": n}


@router.get("/projects/{project_id}/scenarios/stream")
async def stream_scenarios(project_id: int, db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)

    async def generator():
        async for chunk in svc.generate_scenarios_stream(project_id):
            yield chunk

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/projects/{project_id}/scenarios")
async def get_scenarios(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProspectiveScenario)
        .where(ProspectiveScenario.project_id == project_id)
        .order_by(ProspectiveScenario.generated_at)
    )
    scenarios = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "type": s.scenario_type,
            "probability": s.probability,
            "narrative": s.narrative,
            "config": s.morphological_config,
        }
        for s in scenarios
    ]
