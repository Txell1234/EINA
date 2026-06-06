"""Unified scope: dates, topic, domain/source — applied before search and analysis."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case, CasePrompt
from models.osint import OSINTResult
from schemas.analysis_scope import AnalysisScope, CaseScopeProfile
from services.case_topic_relevance import (
    build_case_topic_profile,
    is_article_on_topic,
)
from services.inquiry_scope import (
    InquiryScopeProfile,
    build_inquiry_scope,
    is_article_in_inquiry_scope,
    score_inquiry_relevance,
)
from schemas.actor_typology import build_analytical_profile
from services.osint_data_utils import (
    _strip_accents,
    build_osint_search_queries,
    build_primary_osint_query,
    extract_search_keywords,
    flatten_osint_items,
    text_from_osint_item,
)

logger = logging.getLogger(__name__)


async def load_active_inquiry_scope(db: AsyncSession, case_id: int) -> InquiryScopeProfile | None:
    """Latest inquiry scope for case (any non-failed status)."""
    from models.prospective_inquiry import ProspectiveInquiry

    r = await db.execute(
        select(ProspectiveInquiry)
        .where(ProspectiveInquiry.case_id == case_id)
        .where(ProspectiveInquiry.status.notin_(["failed"]))
        .order_by(ProspectiveInquiry.created_at.desc())
        .limit(1)
    )
    row = r.scalar_one_or_none()
    if not row or not row.inquiry_scope:
        return None
    data = row.inquiry_scope
    if isinstance(data, dict) and data.get("question"):
        from services.inquiry_scope import inquiry_scope_from_stored

        return inquiry_scope_from_stored(data)
    if row.question:
        return build_inquiry_scope(row.question)
    return None


async def should_auto_apply_scope(db: AsyncSession, case_id: int) -> bool:
    """True when case has prompt or active inquiry — scope should apply by default."""
    if await load_active_inquiry_scope(db, case_id):
        return True
    prompt_r = await db.execute(
        select(CasePrompt.id).where(CasePrompt.case_id == case_id).limit(1)
    )
    return prompt_r.scalar_one_or_none() is not None


async def resolve_scope_for_case(
    db: AsyncSession,
    case_id: int,
    *,
    override: AnalysisScope | None = None,
) -> tuple[AnalysisScope, InquiryScopeProfile | None]:
    """Effective analysis scope; stricter when inquiry active."""
    inquiry = await load_active_inquiry_scope(db, case_id)
    if override:
        return override, inquiry
    prof = await load_case_scope_profile(db, case_id)
    scope = prof.default_scope.model_copy()
    if inquiry:
        scope.apply_topic_filter = True
        scope.min_relevance = inquiry.min_relevance
    elif await should_auto_apply_scope(db, case_id):
        scope.apply_topic_filter = True
        scope.min_relevance = max(scope.min_relevance, 0.35)
    return scope, inquiry


async def load_case_scope_profile(db: AsyncSession, case_id: int) -> CaseScopeProfile:
    case_r = await db.execute(select(Case).where(Case.id == case_id))
    case = case_r.scalar_one_or_none()
    if not case:
        return CaseScopeProfile(
            case_id=case_id,
            focus_label="",
            suggested_query="",
            keywords=[],
            primary_geos=[],
            themes=[],
            default_scope=AnalysisScope(),
        )

    prompt_r = await db.execute(
        select(CasePrompt)
        .where(CasePrompt.case_id == case_id)
        .order_by(CasePrompt.created_at.desc())
        .limit(1)
    )
    prompt = prompt_r.scalar_one_or_none()
    extra = (prompt.prompt[:800] if prompt and prompt.prompt else "")

    inquiry = await load_active_inquiry_scope(db, case_id)

    profile = build_case_topic_profile(case.name or "", case.description or "", extra)
    queries = build_osint_search_queries(
        case.name or "",
        case.description or "",
        extra,
        max_queries=3,
    )
    suggested = build_primary_osint_query(
        case.name or "",
        case.description or "",
        extra,
    )
    if inquiry and inquiry.osint_queries:
        queries = inquiry.osint_queries
        suggested = inquiry.osint_queries[0]

    # Keywords for topic filter: geos + themes + entities (not full token dump)
    from services.case_topic_relevance import _THEMATIC_CLUSTERS

    meaningful_kw: list[str] = []
    seen_kw: set[str] = set()
    for g in sorted(profile.primary_geos):
        if g not in seen_kw:
            seen_kw.add(g)
            meaningful_kw.append(g)
    for th in sorted(profile.themes):
        for term in _THEMATIC_CLUSTERS.get(th, [])[:5]:
            t = _strip_accents(term)
            if t not in seen_kw:
                seen_kw.add(t)
                meaningful_kw.append(t)
    for kw in sorted(profile.keywords, key=len, reverse=True):
        if any(c.isdigit() for c in kw) or len(kw) < 5:
            continue
        if kw not in seen_kw:
            seen_kw.add(kw)
            meaningful_kw.append(kw)
        if len(meaningful_kw) >= 25:
            break

    case_type_val = case.case_type.value if case.case_type else "general"
    analytical = build_analytical_profile(case_type=case_type_val, themes=profile.themes)

    min_rel = inquiry.min_relevance if inquiry else 0.28

    return CaseScopeProfile(
        case_id=case_id,
        focus_label=profile.focus_label,
        suggested_query=suggested,
        suggested_queries=queries,
        keywords=meaningful_kw,
        primary_geos=sorted(profile.primary_geos)[:10],
        themes=sorted(profile.themes),
        case_type=case_type_val,
        analytical_profile=analytical.model_dump(),
        default_scope=AnalysisScope(
            period_days=90,
            apply_topic_filter=True,
            min_relevance=min_rel,
        ),
    )


def scope_to_time_range(scope: AnalysisScope) -> dict[str, str] | None:
    if scope.start_date and scope.end_date:
        return {"start": scope.start_date, "end": scope.end_date}
    if scope.period_days:
        from datetime import timedelta

        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=int(scope.period_days))
        return {"start": start.isoformat(), "end": end.isoformat()}
    return None


def _parse_article_date(raw: Any) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y-%m"):
        try:
            if fmt.endswith("%z"):
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            if len(s) == 7 and fmt == "%Y-%m":
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return datetime.strptime(s[:19], fmt.replace("%z", "")).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _article_in_date_range(article: dict[str, Any], scope: AnalysisScope) -> bool:
    tr = scope_to_time_range(scope)
    if not tr:
        return True
    raw = article.get("published_date") or article.get("date") or article.get("created_at")
    dt = _parse_article_date(raw)
    if not dt:
        return True
    try:
        start = datetime.fromisoformat(tr["start"]).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(tr["end"]).replace(tzinfo=timezone.utc)
        end = end.replace(hour=23, minute=59, second=59)
        return start <= dt.replace(tzinfo=timezone.utc) <= end
    except ValueError:
        return True


def _article_matches_domain(article: dict[str, Any], domains: list[str]) -> bool:
    if not domains:
        return True
    url = str(article.get("url") or article.get("source") or "").lower()
    return any(d.strip().lower() in url for d in domains if d.strip())


def filter_articles_by_scope(
    articles: list[dict[str, Any]],
    *,
    case_profile: Any | None,
    scope: AnalysisScope,
    inquiry: InquiryScopeProfile | None = None,
    audit_sample_limit: int = 8,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Filter OSINT articles by date, domain and case/inquiry topic."""
    kept: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "input": len(articles),
        "removed_date": 0,
        "removed_domain": 0,
        "removed_topic": 0,
        "removed_must_match": 0,
        "inquiry_mode": bool(inquiry),
    }
    rejected_samples: list[dict[str, Any]] = []

    for art in articles:
        if not _article_in_date_range(art, scope):
            stats["removed_date"] += 1
            continue
        if not _article_matches_domain(art, scope.domains):
            stats["removed_domain"] += 1
            continue
        if scope.apply_topic_filter and (case_profile or inquiry):
            text = text_from_osint_item(art)
            title = str(art.get("title") or "")
            if inquiry:
                diag = score_inquiry_relevance(
                    text, title, inquiry=inquiry, min_score=scope.min_relevance
                )
                ok = diag["passed"]
                if not ok and not diag.get("passed_must_match"):
                    stats["removed_must_match"] += 1
            else:
                ok = is_article_on_topic(
                    text, title, case_profile, min_score=scope.min_relevance
                )
                diag = {"score": scope.min_relevance if ok else 0, "reasons": []}
            if not ok:
                stats["removed_topic"] += 1
                if len(rejected_samples) < audit_sample_limit:
                    rejected_samples.append(
                        {
                            "title": title[:120],
                            "url": art.get("url", ""),
                            "score": diag.get("score"),
                            "reasons": diag.get("reasons", [])[:3],
                            "required_hits": diag.get("required_hits"),
                        }
                    )
                continue
        kept.append(art)

    stats["kept"] = len(kept)
    stats["rejected_samples"] = rejected_samples
    return kept, stats


async def apply_scope_to_osint_result(
    db: AsyncSession,
    result_id: int,
    case_id: int,
    scope: AnalysisScope,
) -> dict[str, Any]:
    """Post-filter stored OSINT result articles by scope."""
    r = await db.execute(select(OSINTResult).where(OSINTResult.id == result_id))
    result = r.scalar_one_or_none()
    if not result or not isinstance(result.data, dict):
        return {"filtered": False, "reason": "no_data"}

    case_r = await db.execute(select(Case).where(Case.id == case_id))
    case = case_r.scalar_one_or_none()
    prompt_r = await db.execute(
        select(CasePrompt).where(CasePrompt.case_id == case_id).order_by(CasePrompt.created_at.desc()).limit(1)
    )
    prompt = prompt_r.scalar_one_or_none()
    case_profile = build_case_topic_profile(
        case.name if case else "",
        (case.description or "") if case else "",
        (prompt.prompt[:800] if prompt and prompt.prompt else ""),
    )
    inquiry = await load_active_inquiry_scope(db, case_id)

    data = dict(result.data)
    articles = flatten_osint_items(data)
    if not articles:
        return {"filtered": False, "reason": "no_articles"}

    filtered, stats = filter_articles_by_scope(
        articles,
        case_profile=case_profile,
        scope=scope,
        inquiry=inquiry,
    )

    if "articles" in data:
        data["articles"] = filtered
    elif "results" in data:
        data["results"] = filtered
    else:
        data["articles"] = filtered

    data["_scope_filter"] = {
        **stats,
        "scope": scope.model_dump(),
        "inquiry_question": inquiry.question if inquiry else None,
    }
    result.data = data
    await db.commit()
    return {"filtered": True, **stats}


async def auto_apply_scope_for_case_result(
    db: AsyncSession,
    result_id: int,
    case_id: int,
) -> dict[str, Any]:
    """Apply scope after OSINT ingest when case has prompt/inquiry."""
    if not await should_auto_apply_scope(db, case_id):
        return {"filtered": False, "reason": "no_auto_scope"}
    scope, _ = await resolve_scope_for_case(db, case_id)
    return await apply_scope_to_osint_result(db, result_id, case_id, scope)


def merge_scope_into_query_params(
    query_params: dict[str, Any],
    scope: AnalysisScope | None,
) -> dict[str, Any]:
    """Inject scope flags into OSINT query_params for downstream hooks."""
    if not scope:
        return query_params
    out = dict(query_params)
    if scope.period_days and "days" not in out:
        out["days"] = min(int(scope.period_days), 90)
    if scope.apply_topic_filter:
        out["apply_topic_filter"] = True
        out["scope_min_relevance"] = scope.min_relevance
    if scope.domains:
        out["scope_domains"] = scope.domains
    if scope.start_date:
        out["scope_start_date"] = scope.start_date
    if scope.end_date:
        out["scope_end_date"] = scope.end_date
    out["_analysis_scope"] = scope.model_dump()
    return out


def scope_from_query_params(query_params: dict[str, Any] | None) -> AnalysisScope | None:
    if not query_params:
        return None
    raw = query_params.get("_analysis_scope")
    if isinstance(raw, dict):
        try:
            return AnalysisScope(**raw)
        except Exception:
            pass
    has_dates = bool(query_params.get("scope_start_date") or query_params.get("scope_end_date"))
    has_domains = bool(query_params.get("scope_domains"))
    has_topic = bool(query_params.get("apply_topic_filter"))
    has_period = query_params.get("days") is not None
    if not (has_topic or has_dates or has_domains or has_period):
        return None
    domains_raw = query_params.get("scope_domains") or []
    if isinstance(domains_raw, str):
        domains_raw = [d.strip() for d in domains_raw.split(",") if d.strip()]
    return AnalysisScope(
        period_days=query_params.get("days"),
        start_date=query_params.get("scope_start_date"),
        end_date=query_params.get("scope_end_date"),
        apply_topic_filter=has_topic,
        domains=list(domains_raw),
        min_relevance=float(query_params.get("scope_min_relevance") or 0.28),
    )
