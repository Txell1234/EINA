"""Shared Godet wizard progress checklist for a prospective project."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import (
    MACTORResult,
    MICMACResult,
    MorphComponent,
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
    ProspectiveVariable,
    SMICResult,
)

GODET_STEP_ORDER = (
    "project",
    "variables",
    "micmac",
    "actors",
    "mactor",
    "morph",
    "smic",
    "scenarios",
)

GODET_STEP_ROUTES = {
    "project": "/prospective/project",
    "variables": "/prospective/variables",
    "micmac": "/prospective/micmac",
    "actors": "/prospective/actors",
    "mactor": "/prospective/mactor",
    "morph": "/prospective/morph",
    "smic": "/prospective/morph",
    "scenarios": "/prospective-analysis",
}


async def project_godet_checklist(db: AsyncSession, project_id: int) -> dict[str, Any]:
    """Return Godet checklist booleans and metadata for a project."""
    r = await db.execute(select(ProspectiveProject).where(ProspectiveProject.id == project_id))
    project = r.scalar_one_or_none()
    if not project:
        return {
            "found": False,
            "project_id": project_id,
            "checklist": {k: False for k in GODET_STEP_ORDER},
            "missing_steps": list(GODET_STEP_ORDER),
            "suggested_next_step": "project",
            "scenario_count": 0,
        }

    checklist: dict[str, bool] = {
        "project": True,
        "variables": False,
        "micmac": False,
        "actors": False,
        "mactor": False,
        "morph": False,
        "smic": False,
        "scenarios": False,
    }

    var_r = await db.execute(
        select(ProspectiveVariable.id).where(ProspectiveVariable.project_id == project_id).limit(1)
    )
    checklist["variables"] = var_r.scalar_one_or_none() is not None

    mic_r = await db.execute(
        select(MICMACResult.id).where(MICMACResult.project_id == project_id).limit(1)
    )
    checklist["micmac"] = mic_r.scalar_one_or_none() is not None

    act_r = await db.execute(
        select(ProspectiveActor.id).where(ProspectiveActor.project_id == project_id).limit(1)
    )
    checklist["actors"] = act_r.scalar_one_or_none() is not None

    mact_r = await db.execute(
        select(MACTORResult.id).where(MACTORResult.project_id == project_id).limit(1)
    )
    checklist["mactor"] = mact_r.scalar_one_or_none() is not None

    morph_r = await db.execute(
        select(MorphComponent.id).where(MorphComponent.project_id == project_id).limit(1)
    )
    checklist["morph"] = morph_r.scalar_one_or_none() is not None

    smic_r = await db.execute(
        select(SMICResult.id).where(SMICResult.project_id == project_id).limit(1)
    )
    checklist["smic"] = smic_r.scalar_one_or_none() is not None

    sc_r = await db.execute(
        select(ProspectiveScenario).where(ProspectiveScenario.project_id == project_id)
    )
    scenarios = list(sc_r.scalars().all())
    scenario_count = len(scenarios)
    checklist["scenarios"] = scenario_count >= 1

    missing = [k for k in GODET_STEP_ORDER if not checklist[k]]
    suggested = missing[0] if missing else "scenarios"

    return {
        "found": True,
        "project_id": project_id,
        "title": project.title,
        "case_id": project.case_id,
        "checklist": checklist,
        "missing_steps": missing,
        "suggested_next_step": suggested,
        "suggested_route": GODET_STEP_ROUTES.get(suggested, "/prospective/project"),
        "scenario_count": scenario_count,
    }
