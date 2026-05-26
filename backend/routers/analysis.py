"""
Direct Analysis Router
POST /api/analysis/direct — analyze raw text and return full Godet structure
POST /api/analysis/apply  — create a prospective project from analysis result
"""

import asyncio
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from models.user import User

router = APIRouter()


@router.get("/llm-config")
async def get_llm_config(current_user: User = Depends(get_current_user)):
    """Return active LLM provider and which API keys are configured."""
    from services.llm_service import provider_status

    return provider_status()


class DirectAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=100, description="Text estratègic a analitzar (mín. 100 caràcters)")
    case_id: Optional[int] = None
    run_tavily_osint: bool = Field(
        True,
        description="Si hi ha cas actiu i TAVILY_API_KEY, recollir fonts web i classificar-les al cas",
    )
    run_tavily_research: bool = Field(
        False,
        description="Recerca profunda Tavily (informe + fonts) — pot trigar diversos minuts",
    )
    run_tavily_crawl: bool = Field(
        False,
        description="Crawl de dominis preferits (think tanks, mitjans) relacionats amb el text",
    )


class ApplyAnalysisRequest(BaseModel):
    analysis: dict
    project_title: str
    case_id: Optional[int] = None
    source_text: Optional[str] = Field(
        None,
        description="Text original analitzat (per traçabilitat de declaracions)",
    )


@router.post("/direct")
@limiter.limit("3/minute")
async def analyze_text_direct(
    request: Request,
    payload: Annotated[DirectAnalysisRequest, Body()],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze raw text and extract full Godet analysis structure.
    Returns hypothesis, variables, actors, components, statements.
    """
    _ = current_user, request
    from services.direct_analysis_service import DirectAnalysisService

    svc = DirectAnalysisService()
    result = await asyncio.to_thread(svc.analyze, payload.text)

    if "error" in result and result.get("confidence", 0) == 0:
        raise HTTPException(status_code=400, detail=result["error"])

    if payload.case_id and (
        payload.run_tavily_osint or payload.run_tavily_research or payload.run_tavily_crawl
    ):
        from services.tavily_osint_service import collect_tavily_for_case

        osint_summary = await collect_tavily_for_case(
            db,
            payload.case_id,
            payload.text,
            str(result.get("hypothesis") or ""),
            run_research=payload.run_tavily_research,
            run_preferred_crawl=payload.run_tavily_crawl,
            max_queries=3 if payload.run_tavily_osint else 0,
        )
        result["osint"] = osint_summary

    return result


@router.post("/apply")
async def apply_analysis_to_project(
    payload: Annotated[ApplyAnalysisRequest, Body()],
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

    from services.extract_validation import effective_grounding_score, grounding_score, is_verifiable_source

    analysis = payload.analysis
    source_text = (payload.source_text or analysis.get("source_text") or "").strip()

    project = ProspectiveProject(
        case_id=payload.case_id,
        title=payload.project_title,
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
        statement_text = str(s.get("statement", ""))
        excerpt = source_text[:500] if source_text else ""
        score = None
        if excerpt:
            score = effective_grounding_score(
                statement_text,
                excerpt,
                grounding_score(statement_text, excerpt),
            )
        cleanup = "SYNTHETIC" if not is_verifiable_source("", excerpt) else "KEEP"
        db.add(ExtractedStatement(
            case_id=payload.case_id,
            project_id=project.id,
            actor=str(s.get("actor", "")),
            actor_type="state",
            actor_importance=3,
            statement=statement_text,
            topic=str(s.get("topic", "")),
            framing=str(s.get("framing", "neutral")),
            posture_toward=str(s.get("posture_toward", "")),
            posture_value=max(-2, min(2, int(s.get("posture_value", 0)))),
            cleanup_decision=cleanup,
            cleanup_reason="Anàlisi directa (sense article OSINT vinculat)" if cleanup == "SYNTHETIC" else "",
            grounding_score=score,
            source_url="direct-analysis:synthetic" if not source_text else "",
            source_text_excerpt=excerpt,
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
