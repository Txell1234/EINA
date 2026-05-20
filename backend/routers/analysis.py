"""
Direct Analysis Router
POST /api/analysis/direct — analyze raw text and return full Godet structure
POST /api/analysis/apply  — create a prospective project from analysis result
"""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from models.user import User

router = APIRouter()


class DirectAnalysisRequest(BaseModel):
    text: str
    case_id: Optional[int] = None


class ApplyAnalysisRequest(BaseModel):
    analysis: dict
    project_title: str
    case_id: Optional[int] = None


@router.post("/direct")
@limiter.limit("3/minute")
async def analyze_text_direct(
    request: Request,
    data: DirectAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze raw text and extract full Godet analysis structure.
    Returns hypothesis, variables, actors, components, statements.
    """
    _ = db, current_user
    from services.direct_analysis_service import DirectAnalysisService

    svc = DirectAnalysisService()
    result = await asyncio.to_thread(svc.analyze, data.text)

    if "error" in result and result.get("confidence", 0) == 0:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/apply")
async def apply_analysis_to_project(
    data: ApplyAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a prospective project from a direct analysis result.
    Pre-populates all Godet steps: hypothesis, variables, actors, components.
    """
    _ = current_user
    from models.extract import ExtractedStatement
    from models.prospective import (
        MACTORObjective,
        MorphComponent,
        ProspectiveActor,
        ProspectiveProject,
        ProspectiveVariable,
    )

    analysis = data.analysis

    project = ProspectiveProject(
        case_id=data.case_id,
        title=data.project_title,
        hypothesis=analysis.get("hypothesis", ""),
        context=analysis.get("context", ""),
    )
    db.add(project)
    await db.flush()

    for i, v in enumerate(analysis.get("variables", [])):
        db.add(ProspectiveVariable(
            project_id=project.id,
            code=str(v.get("code", chr(65 + i))),
            name=str(v.get("name", "")),
            var_type=str(v.get("type", "I")),
            description=str(v.get("desc", "")),
            order_index=i,
        ))

    for i, a in enumerate(analysis.get("actors", [])):
        db.add(ProspectiveActor(
            project_id=project.id,
            code=str(a.get("code", chr(65 + i))),
            name=str(a.get("name", "")),
            strategic_goals=a.get("strategic_goals", []),
            force_score=float(a.get("force", 3)),
            order_index=i,
        ))

    seen_goals: set[str] = set()
    obj_index = 0
    for a in analysis.get("actors", []):
        for goal in a.get("strategic_goals", []):
            if goal not in seen_goals and obj_index < 6:
                seen_goals.add(goal)
                db.add(MACTORObjective(
                    project_id=project.id,
                    code=f"O{obj_index + 1}",
                    name=goal[:80],
                    order_index=obj_index,
                ))
                obj_index += 1

    for i, c in enumerate(analysis.get("components", [])):
        db.add(MorphComponent(
            project_id=project.id,
            code=str(c.get("code", f"C{i + 1}")),
            name=str(c.get("name", "")),
            configurations=c.get("configurations", []),
            order_index=i,
        ))

    for s in analysis.get("statements", []):
        db.add(ExtractedStatement(
            case_id=data.case_id,
            project_id=project.id,
            actor=str(s.get("actor", "")),
            actor_type="state",
            actor_importance=3,
            statement=str(s.get("statement", "")),
            topic=str(s.get("topic", "")),
            framing=str(s.get("framing", "neutral")),
            posture_toward=str(s.get("posture_toward", "")),
            posture_value=max(-2, min(2, int(s.get("posture_value", 0)))),
            cleanup_decision="KEEP",
            grounding_score=1.0,
        ))

    await db.commit()
    await db.refresh(project)

    return {
        "project_id": project.id,
        "title": project.title,
        "variables_created": len(analysis.get("variables", [])),
        "actors_created": len(analysis.get("actors", [])),
        "components_created": len(analysis.get("components", [])),
        "statements_created": len(analysis.get("statements", [])),
        "objectives_created": obj_index,
        "message": (
            f"Projecte '{project.title}' creat amb tots els elements. "
            f"Accedeix al wizard per completar la matriu MIC-MAC i les postures MACTOR."
        ),
    }
