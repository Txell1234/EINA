"""
Intelligence Unit API — status and unified pipeline for case-level intelligence.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.database import get_db
from app.dependencies import get_current_user
from models.user import User
from services.intelligence_service import IntelligenceService
from services.actor_impact_service import ActorImpactService

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence Unit"])


@router.get("/{case_id}/status")
async def get_intelligence_status(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = IntelligenceService(db)
    result = await svc.get_status(case_id)
    if not result.get("found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


@router.post("/{case_id}/run")
async def run_intelligence_pipeline(
    case_id: int,
    include_investment: bool = True,
    auto_cleanup: bool = False,
    apply_scope: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = IntelligenceService(db)
    return await svc.run_pipeline(
        case_id,
        include_investment=include_investment,
        auto_cleanup=auto_cleanup,
        apply_scope=apply_scope,
    )


@router.get("/{case_id}/actor-network")
async def get_actor_network(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Actor graph grouped by class/institution — additive view over extracted statements."""
    from services.actor_network_service import ActorNetworkService

    return await ActorNetworkService(db).build_network(case_id)


@router.get("/{case_id}/policy-industry")
async def get_policy_industry_map(
    case_id: int,
    premise: str | None = None,
    enrich: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Map policy themes/premises to companies, contractors and beneficiaries (JP + overseas)."""
    from services.policy_industry_service import PolicyIndustryService

    result = await PolicyIndustryService(db).build_map(case_id, premise=premise, enrich=enrich)
    if not result.get("found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


@router.post("/{case_id}/policy-industry/analyze")
async def analyze_policy_industry(
    case_id: int,
    body: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Premise-specific industry linkage with optional LLM enrichment (opt-in)."""
    from services.policy_industry_service import PolicyIndustryService

    premise = (body.get("premise") or body.get("premise_text") or "").strip()
    if len(premise) < 10:
        raise HTTPException(status_code=400, detail="premise és obligatori (mín. 10 caràcters)")
    enrich = bool(body.get("enrich", False))
    result = await PolicyIndustryService(db).build_map(case_id, premise=premise, enrich=enrich)
    if not result.get("found"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


@router.get("/{case_id}/actor-impact")
async def get_actor_impact(
    case_id: int,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    from services.case_recalc_service import is_actor_impact_stale

    svc = ActorImpactService(db)
    if refresh:
        data = await svc.build_assessment(case_id)
    else:
        latest = await svc.get_latest(case_id)
        if latest:
            data = latest
        else:
            data = await svc.build_assessment(case_id)
    if "data_freshness" not in data:
        data["data_freshness"] = await is_actor_impact_stale(db, case_id, data)
    return data


@router.post("/{case_id}/actor-impact/analyze")
async def analyze_actor_impact(
    case_id: int,
    project_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = ActorImpactService(db)
    return await svc.analyze_and_save(case_id, project_id=project_id)
