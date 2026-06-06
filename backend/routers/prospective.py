"""
Prospective Analysis Router - MIC-MAC, MACTOR, morphological, scenarios
"""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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

from app.dependencies import get_current_user
from app.limiter import limiter
from models.user import User

logger = logging.getLogger(__name__)

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


class IncompatibilitiesRequest(BaseModel):
    incompatibilities: List[dict]


class ApplyCcaRulesRequest(BaseModel):
    rules: List[dict]


class SMICRequest(BaseModel):
    initial_probs: List[float]
    cross_matrix: List[List[float]]


class ConditionalSMICRequest(BaseModel):
    conditional_matrix: List[List[float]]


class CompatibilityPair(BaseModel):
    comp_a: str
    cfg_a: str
    comp_b: str
    cfg_b: str
    compatible: bool = True


class SaveCompatibilityRequest(BaseModel):
    pairs: List[CompatibilityPair]


class MICMACPreviewRequest(BaseModel):
    matrix: List[List[int]]


class GeopoliticalEnrichRequest(BaseModel):
    variables: List[dict]
    case_id: Optional[int] = None


@router.get("/projects/{project_id}/retrospective")
async def get_retrospective(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Build Godet retrospective for a project's case.
    Analyses temporal evolution of actor postures from OSINT extractions.
    """
    from services.retrospective_service import RetrospectiveService

    svc = ProspectiveService(db)
    project = await svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projecte no trobat")

    if not project.case_id:
        return {
            "has_data": False,
            "message": "El projecte no té cap cas associat. "
                       "Crea el projecte des d'un cas OSINT.",
        }

    retro_svc = RetrospectiveService(db)
    return await retro_svc.build_retrospective(project.case_id, project_id)


@router.post("/projects/{project_id}/geopolitical/micmac-suggestions")
async def geopolitical_micmac_suggestions(
    project_id: int,
    data: GeopoliticalEnrichRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Suggeriments de puntuació MIC-MAC des de relacions bilaterals i esdeveniments."""
    from services.prospective_geopolitical_service import ProspectiveGeopoliticalService

    svc = ProspectiveService(db)
    project = await svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    case_id = data.case_id or project.case_id
    if not case_id:
        raise HTTPException(status_code=400, detail="Cal un cas enllaçat amb dades geopolítiques")
    return await ProspectiveGeopoliticalService(db).micmac_suggestions(case_id, data.variables)


@router.get("/projects")
async def list_projects(
    case_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    projects = await svc.list_projects(case_id)
    result = []
    for p in projects:
        actors_r = await db.execute(
            select(ProspectiveActor)
            .where(ProspectiveActor.project_id == p.id)
            .order_by(ProspectiveActor.order_index)
        )
        result.append(
            {
                "id": p.id,
                "title": p.title,
                "case_id": p.case_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "actors": [
                    {"code": a.code, "name": a.name}
                    for a in actors_r.scalars().all()
                ],
            }
        )
    return result


@router.post("/projects")
async def create_project(data: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)
    project = await svc.create_project(
        case_id=data.case_id,
        title=data.title,
        hypothesis=data.hypothesis,
        context=data.context,
    )
    return {"id": project.id, "title": project.title}


@router.get("/projects/{project_id}")
async def get_project(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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

    incompatibilities = await svc.get_incompatibilities(project_id)
    morph_space = await svc.get_morph_space(project_id)
    smic = await svc.get_smic(project_id)

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
        "incompatibilities": incompatibilities,
        "morph_space": morph_space,
        "smic": smic,
    }


@router.put("/projects/{project_id}/variables")
async def save_variables(
    project_id: int,
    data: SaveVariablesRequest,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.compute_mactor(project_id, data.postures)


@router.post("/projects/{project_id}/micmac/preview")
async def preview_micmac(
    project_id: int,
    data: MICMACPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """What-if MIC-MAC preview without persisting."""
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.preview_micmac(project_id, data.matrix)


@router.put("/projects/{project_id}/compatibility")
async def save_compatibility(
    project_id: int,
    data: SaveCompatibilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.save_compatibility(project_id, [p.model_dump() for p in data.pairs])


@router.get("/projects/{project_id}/compatibility")
async def get_compatibility(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_compatibility(project_id)


@router.get("/projects/{project_id}/morphological-space")
async def get_morphological_space(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_morphological_space(project_id)


@router.put("/projects/{project_id}/compatibilities")
async def save_compatibilities(
    project_id: int,
    data: IncompatibilitiesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.save_incompatibilities(project_id, data.incompatibilities)


@router.get("/projects/{project_id}/compatibilities")
async def get_compatibilities(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_incompatibilities(project_id)


@router.get("/projects/{project_id}/morph-space")
async def get_morph_space(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_morph_space(project_id)


@router.get("/projects/{project_id}/cca-suggestions")
async def get_cca_suggestions(
    project_id: int,
    inquiry_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_cca_service import InquiryCcaService

    result = await InquiryCcaService(db).suggest_for_project(project_id, inquiry_id=inquiry_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/projects/{project_id}/cca-suggestions/preview")
async def preview_cca_suggestions(
    project_id: int,
    data: ApplyCcaRulesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_cca_service import InquiryCcaService

    result = await InquiryCcaService(db).preview_cca_impact(project_id, data.rules)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/projects/{project_id}/cca-suggestions/apply")
async def apply_cca_suggestions(
    project_id: int,
    data: ApplyCcaRulesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    from services.inquiry_cca_service import InquiryCcaService

    result = await InquiryCcaService(db).apply_selected_rules(project_id, data.rules)
    return result


@router.get("/projects/{project_id}/smic")
async def get_smic(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_smic(project_id)


@router.post("/projects/{project_id}/smic")
async def compute_smic_bayesian(
    project_id: int,
    data: ConditionalSMICRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SMIC Bayesian: conditional_matrix[i][j] = P(j | i occurs)."""
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.compute_smic(project_id, data.conditional_matrix)


@router.post("/projects/{project_id}/smic/compute")
async def compute_smic(
    project_id: int,
    data: SMICRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.save_and_compute_smic(
        project_id, data.initial_probs, data.cross_matrix
    )


@router.put("/projects/{project_id}/components")
async def save_components(
    project_id: int,
    data: SaveComponentsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    await svc.save_components(project_id, data.components)
    return {"status": "ok", "count": len(data.components)}


@router.get("/projects/{project_id}/scenarios")
async def get_scenarios(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")
    return await svc.get_scenarios(project_id)


@router.get("/projects/{project_id}/scenarios/stream")
@limiter.limit("10/minute")
async def stream_scenarios(
    request: Request,
    project_id: int,
    include_temporal_context: bool = Query(
        False, description="Incloure retrospectiva i tendències al context (opt-in)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ProspectiveService(db)
    if not await svc.get_project(project_id):
        raise HTTPException(status_code=404, detail="Projecte no trobat")

    async def event_generator():
        try:
            async for event in svc.stream_scenarios(
                project_id, include_temporal_context=include_temporal_context
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class ExpertVoteRequest(BaseModel):
    expert_id: str
    expert_name: str = "Anònim"
    votes: List[dict]


@router.post("/projects/{project_id}/panel/vote")
async def submit_expert_vote(
    project_id: int,
    data: ExpertVoteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit expert votes for MIC-MAC matrix (Delphi panel mode)."""
    svc = ProspectiveService(db)
    return await svc.submit_expert_vote(
        project_id, data.expert_id, data.expert_name, data.votes
    )


@router.get("/projects/{project_id}/panel/consensus")
async def get_panel_consensus(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get consensus matrix and disagreement analysis from all expert votes."""
    svc = ProspectiveService(db)
    return await svc.get_panel_consensus(project_id)


@router.post("/projects/{project_id}/panel/apply")
async def apply_consensus(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Apply consensus matrix as the official MIC-MAC result."""
    svc = ProspectiveService(db)
    return await svc.apply_consensus(project_id)


@router.get("/projects/{project_id}/export/pdf")
async def export_project_pdf(
    project_id: int,
    lang: str = Query("ca", pattern="^(ca|es|en)$"),
    include_decision_annex: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export prospective project as PDF. Requires weasyprint + libpango."""
    from pathlib import Path

    from fastapi.responses import Response as BinaryResponse

    try:
        from services.report_export_service import export_pdf as _pdf

        meta = await _pdf(
            db, project_id, lang=lang, include_decision_annex=include_decision_annex
        )
        data = Path(meta["file_path"]).read_bytes()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return BinaryResponse(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_prospectiu_{project_id}.pdf"
        },
    )


@router.get("/projects/{project_id}/export/docx")
async def export_project_docx(
    project_id: int,
    lang: str = Query("ca", pattern="^(ca|es|en)$"),
    include_decision_annex: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export prospective project as DOCX."""
    from pathlib import Path

    from fastapi.responses import Response as BinaryResponse

    try:
        from services.report_export_service import export_docx as _docx

        meta = await _docx(
            db, project_id, lang=lang, include_decision_annex=include_decision_annex
        )
        data = Path(meta["file_path"]).read_bytes()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return BinaryResponse(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=informe_prospectiu_{project_id}.docx"
        },
    )


@router.get("/projects/{project_id}/export/html")
async def export_project_html(
    project_id: int,
    lang: str = Query("ca", pattern="^(ca|es|en)$"),
    include_decision_annex: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export prospective project as HTML (recomanat per imprimir a PDF a Windows)."""
    from pathlib import Path

    from fastapi.responses import Response as BinaryResponse

    try:
        from services.report_export_service import export_html as _html

        meta = await _html(
            db, project_id, lang=lang, include_decision_annex=include_decision_annex
        )
        data = Path(meta["file_path"]).read_bytes()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return BinaryResponse(
        content=data,
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=informe_prospectiu_{project_id}.html"
        },
    )


@router.get("/matches/{match_id}/provenance")
async def get_match_provenance(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.source_provenance_service import match_provenance

    try:
        return await match_provenance(db, match_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Coincidència no trobada")


@router.get("/projects/{project_id}/export-readiness")
async def project_export_readiness(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from models.prospective import ProspectiveProject
    from services.source_provenance_service import export_readiness

    r = await db.execute(select(ProspectiveProject.case_id).where(ProspectiveProject.id == project_id))
    case_id = r.scalar_one_or_none()
    if not case_id:
        return {
            "project_id": project_id,
            "export_ready": False,
            "issues": [{"type": "no_case", "message": "Projecte sense cas OSINT associat"}],
            "warnings": [],
        }
    data = await export_readiness(db, case_id)
    data["project_id"] = project_id
    return data


@router.post("/projects/{project_id}/scenarios/{scenario_id}/monitors")
async def create_scenario_monitors(
    project_id: int,
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract early warning indicators from scenario and create OSINT monitors."""
    from models.prospective import ProspectiveScenario
    from services.alert_monitor_service import create_monitors_from_scenario

    r = await db.execute(
        select(ProspectiveScenario).where(
            ProspectiveScenario.id == scenario_id,
            ProspectiveScenario.project_id == project_id,
        )
    )
    sc = r.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Escenari no trobat")

    monitors = await create_monitors_from_scenario(
        db, project_id, scenario_id, sc.narrative or ""
    )
    return {"created": len(monitors), "monitors": monitors}


@router.get("/projects/{project_id}/scenarios/{scenario_id}/milestones")
async def get_scenario_milestones(
    project_id: int,
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from models.prospective import ProspectiveScenario
    from services.scenario_milestone_service import list_milestones_for_scenario

    r = await db.execute(
        select(ProspectiveScenario).where(
            ProspectiveScenario.id == scenario_id,
            ProspectiveScenario.project_id == project_id,
        )
    )
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Escenari no trobat")
    items = await list_milestones_for_scenario(db, scenario_id)
    return {"scenario_id": scenario_id, "milestones": items}


@router.post("/projects/{project_id}/scenarios/{scenario_id}/milestones/parse")
async def parse_scenario_milestones(
    project_id: int,
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-parse milestones from scenario narrative (best-effort)."""
    from models.prospective import ProspectiveScenario
    from services.scenario_milestone_service import persist_milestones_for_scenario

    r = await db.execute(
        select(ProspectiveScenario).where(
            ProspectiveScenario.id == scenario_id,
            ProspectiveScenario.project_id == project_id,
        )
    )
    sc = r.scalar_one_or_none()
    if not sc:
        raise HTTPException(status_code=404, detail="Escenari no trobat")
    milestones = await persist_milestones_for_scenario(db, scenario_id, sc.narrative or "")
    return {"scenario_id": scenario_id, "count": len(milestones), "milestones": milestones}


@router.post("/projects/{project_id}/scenarios/{scenario_id}/milestones/monitors")
async def create_milestone_monitors(
    project_id: int,
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create OSINT monitors from persisted milestones (additive)."""
    from models.prospective import ProspectiveScenario
    from services.scenario_milestone_service import create_monitors_from_milestones

    r = await db.execute(
        select(ProspectiveScenario).where(
            ProspectiveScenario.id == scenario_id,
            ProspectiveScenario.project_id == project_id,
        )
    )
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Escenari no trobat")
    monitors = await create_monitors_from_milestones(db, project_id, scenario_id)
    return {"created": len(monitors), "monitors": monitors}


@router.get("/monitors/summary")
async def monitors_summary(
    case_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summary of alert monitors with OSINT matches (match_count > 0)."""
    from services.alert_monitor_service import list_triggered_summary

    try:
        return await list_triggered_summary(db, user_id=current_user.id, case_id=case_id)
    except Exception as exc:
        logger.exception("monitors/summary failed for case_id=%s: %s", case_id, exc)
        return {
            "triggered_count": 0,
            "total_matches": 0,
            "total_monitors": 0,
            "unread_count": 0,
            "new_matches": 0,
        }


@router.get("/projects/{project_id}/monitors")
async def list_project_monitors(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all alert monitors for a project."""
    from services.alert_monitor_service import list_monitors

    return await list_monitors(db, project_id)


@router.post("/monitors/{monitor_id}/check")
async def check_monitor(monitor_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Manually run an OSINT check for a monitor."""
    from services.alert_monitor_service import run_monitor_check

    return await run_monitor_check(db, monitor_id)


class ToggleMonitorRequest(BaseModel):
    is_active: bool


@router.patch("/monitors/{monitor_id}/toggle")
async def toggle_monitor(
    monitor_id: int,
    data: ToggleMonitorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate or pause an alert monitor."""
    from models.prospective import AlertMonitor

    r = await db.execute(select(AlertMonitor).where(AlertMonitor.id == monitor_id))
    monitor = r.scalar_one_or_none()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor no trobat")
    monitor.is_active = 1 if data.is_active else 0
    await db.commit()
    return {"id": monitor_id, "is_active": bool(monitor.is_active)}


class ManualMonitorRequest(BaseModel):
    indicator: str
    keywords: List[str] = []
    osint_sources: List[str] = ["gdelt", "google_news", "reddit"]
    lookback_days: Optional[int] = None
    horizon_label: Optional[str] = None
    min_match_score: Optional[float] = None
    min_keywords_matched: Optional[int] = None


class MonitorSettingsRequest(BaseModel):
    lookback_days: Optional[int] = None
    horizon_label: Optional[str] = None
    min_match_score: Optional[float] = None
    min_keywords_matched: Optional[int] = None
    clear_thresholds: bool = False


@router.patch("/monitors/{monitor_id}/settings")
async def patch_monitor_settings(
    monitor_id: int,
    data: MonitorSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update optional monitor thresholds (NULL fields = legacy behavior)."""
    from services.alert_monitor_service import update_monitor_settings

    result = await update_monitor_settings(
        db,
        monitor_id,
        lookback_days=data.lookback_days,
        horizon_label=data.horizon_label,
        min_match_score=data.min_match_score,
        min_keywords_matched=data.min_keywords_matched,
        clear_thresholds=data.clear_thresholds,
    )
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/projects/{project_id}/monitors/manual")
async def add_manual_monitor(
    project_id: int,
    data: ManualMonitorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a manually defined alert monitor to a project."""
    from models.prospective import AlertMonitor
    from services.alert_monitor_service import _keywords as _kw

    kws = data.keywords if data.keywords else _kw(data.indicator)
    from models.prospective import ProspectiveProject
    proj_r = await db.execute(select(ProspectiveProject.case_id).where(ProspectiveProject.id == project_id))
    case_id = proj_r.scalar_one_or_none()
    monitor = AlertMonitor(
        project_id=project_id,
        case_id=case_id,
        indicator=data.indicator,
        keywords=kws,
        osint_sources=data.osint_sources,
        is_active=1,
        lookback_days=data.lookback_days,
        horizon_label=data.horizon_label,
        min_match_score=data.min_match_score,
        min_keywords_matched=data.min_keywords_matched,
    )
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    from services.alert_monitor_service import _monitor_to_dict

    return _monitor_to_dict(monitor)


class MatchStatusRequest(BaseModel):
    status: str
    action_taken: str = ""


@router.get("/monitors/{monitor_id}/matches")
async def get_monitor_matches(
    monitor_id: int,
    status: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import list_matches, repair_monitor_counts

    await repair_monitor_counts(db, monitor_id=monitor_id)
    return await list_matches(
        db,
        monitor_id=monitor_id,
        status=status,
        include_archived=include_archived,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get("/projects/{project_id}/matches")
async def get_project_matches(
    project_id: int,
    include_archived: bool = Query(False),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import list_matches

    return await list_matches(
        db,
        project_id=project_id,
        include_archived=include_archived,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get("/cases/{case_id}/alert-matches")
async def get_case_alert_matches(
    case_id: int,
    include_archived: bool = Query(False),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import list_matches

    return await list_matches(
        db,
        case_id=case_id,
        include_archived=include_archived,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.patch("/matches/{match_id}/status")
async def patch_match_status(
    match_id: int,
    data: MatchStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import update_match_status

    try:
        return await update_match_status(db, match_id, data.status, data.action_taken)
    except LookupError:
        raise HTTPException(status_code=404, detail="Coincidència no trobada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/matches/{match_id}/archive")
async def archive_alert_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import archive_match

    try:
        return await archive_match(db, match_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Coincidència no trobada")


@router.post("/matches/bulk-extract")
async def bulk_extract_alert_matches(
    case_id: int | None = Query(None),
    monitor_id: int | None = Query(None),
    limit: int = Query(25, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import bulk_extract_matches

    if case_id is None and monitor_id is None:
        raise HTTPException(status_code=400, detail="Cal case_id o monitor_id")
    return await bulk_extract_matches(db, case_id=case_id, monitor_id=monitor_id, limit=limit)


@router.post("/matches/{match_id}/extract")
async def extract_alert_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import extract_from_match

    try:
        return await extract_from_match(db, match_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Coincidència no trobada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/matches/{match_id}/analyze")
async def analyze_alert_match(
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import analyze_match

    try:
        return await analyze_match(db, match_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Coincidència no trobada")


@router.get("/monitors/{monitor_id}/matches/export")
async def export_monitor_matches(
    monitor_id: int,
    fmt: str = Query("json", pattern="^(json|csv)$"),
    include_archived: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import export_matches

    content, media_type, filename = await export_matches(
        db, monitor_id=monitor_id, include_archived=include_archived, fmt=fmt
    )
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{project_id}/matches/export")
async def export_project_matches(
    project_id: int,
    fmt: str = Query("json", pattern="^(json|csv)$"),
    include_archived: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import export_matches

    content, media_type, filename = await export_matches(
        db, project_id=project_id, include_archived=include_archived, fmt=fmt
    )
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases/{case_id}/alert-matches/export")
async def export_case_alert_matches(
    case_id: int,
    fmt: str = Query("json", pattern="^(json|csv)$"),
    include_archived: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.alert_monitor_service import export_matches

    content, media_type, filename = await export_matches(
        db, case_id=case_id, include_archived=include_archived, fmt=fmt
    )
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
