"""
Extraction pipeline router - OSINT → structured statements
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from models.extract import ExtractedStatement
from schemas.analysis_scope import AnalysisScope
from services.extract_service import ExtractService
from services.extract_validation import effective_grounding_score, is_verifiable_source
from services.prospective_service import ProspectiveService

from app.dependencies import get_current_user
from app.limiter import limiter
from models.user import User

router = APIRouter()


def _scope_from_query(
    apply_scope: bool,
    apply_topic_filter: bool | None,
    period_days: int | None,
    start_date: str | None,
    end_date: str | None,
    domains: str | None,
    min_relevance: float | None,
) -> tuple[bool, AnalysisScope | None]:
    if not apply_scope:
        return False, None
    dom_list = [d.strip().lower() for d in (domains or "").replace(";", ",").split(",") if d.strip()]
    return True, AnalysisScope(
        period_days=period_days,
        start_date=start_date or None,
        end_date=end_date or None,
        apply_topic_filter=True if apply_topic_filter is None else apply_topic_filter,
        domains=dom_list,
        min_relevance=min_relevance if min_relevance is not None else 0.28,
    )


@router.get("/coverage/{case_id}")
async def get_extraction_coverage(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.extraction_coverage_service import get_extraction_coverage as _coverage

    return await _coverage(db, case_id)


@router.post("/run-pending/{case_id}")
@router.get("/run-pending/{case_id}")
@limiter.limit("5/minute")
async def run_pending_extraction(
    request: Request,
    case_id: int,
    apply_scope: bool = Query(False, description="Aplicar delimitació (dates, dominis, temàtica opt-in)"),
    apply_topic_filter: bool | None = Query(None),
    period_days: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    domains: str | None = Query(None),
    min_relevance: float | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract only articles not yet processed (same pipeline as /run)."""
    svc = ExtractService(db)
    use_scope, scope = _scope_from_query(
        apply_scope, apply_topic_filter, period_days, start_date, end_date, domains, min_relevance
    )

    async def event_generator():
        try:
            async for event in svc.extract_from_case(
                case_id, apply_scope=use_scope, scope=scope
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/run/{case_id}")
@router.get("/run/{case_id}")
@limiter.limit("5/minute")
async def run_extraction(
    request: Request,
    case_id: int,
    apply_scope: bool = Query(False),
    apply_topic_filter: bool | None = Query(None),
    period_days: int | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    domains: str | None = Query(None),
    min_relevance: float | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ExtractService(db)
    use_scope, scope = _scope_from_query(
        apply_scope, apply_topic_filter, period_days, start_date, end_date, domains, min_relevance
    )

    async def event_generator():
        try:
            async for event in svc.extract_from_case(
                case_id, apply_scope=use_scope, scope=scope
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/relevance-cleanup/{case_id}")
async def reclassify_relevance(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reclassify existing statements: REMOVE those off-topic for the case."""
    svc = ExtractService(db)
    return await svc.reclassify_case_relevance(case_id)


@router.get("/statements/{case_id}")
async def list_statements(
    case_id: int,
    decision: Optional[str] = Query(None),
    relevant_only: bool = Query(False, description="Exclou REMOVE i UNVERIFIED sense focus"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    domain: Optional[str] = Query(None, description="Filtra per domini de source_url"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
    if decision:
        base = base.where(ExtractedStatement.cleanup_decision == decision)
    elif relevant_only:
        base = base.where(
            ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING", "NEEDS_REVIEW", "SYNTHETIC"])
        )
    if domain:
        base = base.where(ExtractedStatement.source_url.ilike(f"%{domain}%"))
    if date_from:
        base = base.where(ExtractedStatement.source_date >= date_from)
    if date_to:
        base = base.where(ExtractedStatement.source_date <= date_to + "T23:59:59")

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = base.order_by(ExtractedStatement.extracted_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total,
        "domain_filter": domain,
        "items": [
            {
                "id": s.id,
                "actor": s.actor,
                "actor_type": s.actor_type,
                "institution_subtype": getattr(s, "institution_subtype", None),
                "signal_type": getattr(s, "signal_type", None),
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
                "osint_result_id": s.osint_result_id,
                "source_url": s.source_url,
                "source_date": s.source_date or None,
                "source_text_excerpt": s.source_text_excerpt,
                "cleanup_decision": s.cleanup_decision,
                "source_verified": is_verifiable_source(s.source_url, s.source_text_excerpt),
                "grounding_score": effective_grounding_score(
                    s.statement or "",
                    s.source_text_excerpt,
                    s.grounding_score,
                ),
            }
            for s in rows
        ],
    }


@router.get("/provenance/statement/{statement_id}")
async def get_statement_provenance(
    statement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.source_provenance_service import statement_provenance

    try:
        return await statement_provenance(db, statement_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Declaració no trobada")


@router.get("/export-readiness/{case_id}")
async def get_export_readiness(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from services.source_provenance_service import export_readiness

    return await export_readiness(db, case_id)


@router.get("/validate/{case_id}")
async def validate_extraction(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mètriques de qualitat d'extracció (patró china-us-rhetoric validate.py)."""
    svc = ExtractService(db)
    return await svc.validate_case(case_id)


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

    try:
        project = await prospective_svc.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Projecte no trobat")

        variables = await extract_svc.get_suggested_variables(case_id)
        actors = await extract_svc.get_suggested_actors(case_id)
        result = await prospective_svc.apply_extraction(project_id, variables, actors)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No s'ha pogut aplicar l'extracció: {exc}",
        ) from exc


@router.get("/source-reliability/{case_id}")
async def get_source_reliability(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Agrupa declaracions per domini de source_url i calcula fiabilitat.
    Retorna ranking de fonts per grounding_score mitjà.
    """
    from urllib.parse import urlparse

    result = await db.execute(
        select(ExtractedStatement).where(
            ExtractedStatement.case_id == case_id,
            ExtractedStatement.cleanup_decision == "KEEP",
        )
    )
    stmts = result.scalars().all()

    domain_data: dict[str, dict] = {}
    for s in stmts:
        if not s.source_url:
            domain = "desconegut"
        else:
            try:
                parsed = urlparse(s.source_url)
                domain = parsed.netloc.replace("www.", "") or "desconegut"
            except Exception:
                domain = "desconegut"

        if domain not in domain_data:
            domain_data[domain] = {
                "domain": domain,
                "n_statements": 0,
                "grounding_scores": [],
                "hallucinations": 0,
                "topics": set(),
            }
        domain_data[domain]["n_statements"] += 1
        domain_data[domain]["grounding_scores"].append(s.grounding_score or 0.5)
        if (s.grounding_score or 0.5) < 0.08:
            domain_data[domain]["hallucinations"] += 1
        if s.topic:
            domain_data[domain]["topics"].add(s.topic)

    sources = []
    for domain, data in domain_data.items():
        scores = data["grounding_scores"]
        avg = sum(scores) / len(scores) if scores else 0.5
        sources.append({
            "domain": domain,
            "n_statements": data["n_statements"],
            "avg_grounding": round(avg, 3),
            "hallucination_rate": round(
                data["hallucinations"] / len(scores) if scores else 0, 3
            ),
            "reliability_label": (
                "Alta" if avg >= 0.6
                else "Moderada" if avg >= 0.3
                else "Baixa"
            ),
            "main_topics": list(data["topics"])[:4],
        })

    return {
        "case_id": case_id,
        "total_sources": len(sources),
        "sources": sorted(sources, key=lambda x: -x["avg_grounding"]),
    }
