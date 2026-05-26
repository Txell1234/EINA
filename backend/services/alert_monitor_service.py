"""
Alert Monitor Service — scenario indicators → OSINT checks → persisted evidence (AlertMatch).
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.osint_data_utils import flatten_osint_items, text_from_osint_item
from services.article_enrichment_service import enrich_single_article

logger = logging.getLogger(__name__)


def _default_monitor_sources() -> list[str]:
    from services.tavily_pipeline_service import tavily_configured

    sources = ["gdelt", "google_news", "reddit"]
    if tavily_configured():
        sources.append("tavily")
    return sources


_STOP = {
    "de", "del", "la", "el", "els", "les", "un", "una", "i", "o", "a", "en", "per", "amb",
    "que", "es", "ha", "han", "si", "però", "com", "tot", "entre", "sobre", "augment",
    "increment", "reducció", "canvi", "nova", "nou", "the", "of", "in", "at", "by", "an",
    "or", "and", "to", "is", "are", "that", "with", "nova", "nous", "noves",
}

MATCH_STATUSES_ACTIVE = frozenset({"new", "reviewed", "actioned", "dismissed"})
MATCH_STATUSES_ALL = MATCH_STATUSES_ACTIVE | {"archived"}


def _keywords(text: str) -> list[str]:
    caps = re.findall(r"[A-ZÀÁÂÃÄÅ][a-zàáâãäå]{2,}", text)
    words = [
        w for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", text.lower()) if w not in _STOP
    ]
    return list(dict.fromkeys(caps + words))[:4]


def _match_article(article: dict[str, Any], keywords: list[str]) -> tuple[list[str], float]:
    if not keywords:
        return [], 0.0
    haystack = " ".join(
        [
            str(article.get("title") or ""),
            str(article.get("summary") or ""),
            str(article.get("body") or ""),
            str(article.get("description") or ""),
            str(article.get("source") or ""),
            str(article.get("url") or ""),
        ]
    ).lower()
    matched = [k for k in keywords if k.lower() in haystack]
    score = len(matched) / max(len(keywords), 1)
    return matched, round(score, 3)


def _monitor_gdelt_days(monitor: Any) -> int:
    if getattr(monitor, "lookback_days", None):
        try:
            return max(1, min(365, int(monitor.lookback_days)))
        except (TypeError, ValueError):
            pass
    label = (getattr(monitor, "horizon_label", None) or "").lower()
    horizon_days = {"3m": 90, "6m": 180, "12m": 365, "18m": 540}
    return horizon_days.get(label, 7)


def _passes_monitor_thresholds(
    monitor: Any,
    matched_kws: list[str],
    score: float,
) -> bool:
    min_score = getattr(monitor, "min_match_score", None)
    if min_score is not None and score < float(min_score):
        return False
    min_kw = getattr(monitor, "min_keywords_matched", None)
    if min_kw is not None and len(matched_kws) < int(min_kw):
        return False
    return True


def _monitor_to_dict(m: Any) -> dict[str, Any]:
    return {
        "id": m.id,
        "indicator": m.indicator,
        "keywords": m.keywords,
        "osint_sources": m.osint_sources,
        "is_active": bool(m.is_active),
        "match_count": m.match_count,
        "unread_count": m.unread_count or 0,
        "case_id": m.case_id,
        "scenario_id": m.scenario_id,
        "last_checked": m.last_checked.isoformat() if m.last_checked else None,
        "last_match": m.last_match.isoformat() if m.last_match else None,
        "lookback_days": m.lookback_days,
        "horizon_label": m.horizon_label,
        "min_match_score": m.min_match_score,
        "min_keywords_matched": m.min_keywords_matched,
    }


def _match_to_dict(m: Any, *, monitor_indicator: str = "", scenario_name: str = "") -> dict[str, Any]:
    return {
        "id": m.id,
        "monitor_id": m.monitor_id,
        "project_id": m.project_id,
        "case_id": m.case_id,
        "scenario_id": m.scenario_id,
        "monitor_indicator": monitor_indicator,
        "scenario_name": scenario_name,
        "title": m.title,
        "url": m.url,
        "excerpt": m.excerpt,
        "source_type": m.source_type,
        "published_at": m.published_at,
        "osint_query_id": m.osint_query_id,
        "osint_result_id": m.osint_result_id,
        "matched_keywords": m.matched_keywords or [],
        "match_score": m.match_score,
        "status": m.status,
        "reviewed_at": m.reviewed_at.isoformat() if m.reviewed_at else None,
        "action_taken": m.action_taken,
        "extracted_statement_id": m.extracted_statement_id,
        "analysis_summary": m.analysis_summary,
        "first_seen_at": m.first_seen_at.isoformat() if m.first_seen_at else None,
        "last_seen_at": m.last_seen_at.isoformat() if m.last_seen_at else None,
        "seen_count": m.seen_count,
        "has_source": bool(m.url),
    }


async def _resolve_case_id(db: AsyncSession, project_id: int) -> int | None:
    from models.prospective import ProspectiveProject

    r = await db.execute(select(ProspectiveProject.case_id).where(ProspectiveProject.id == project_id))
    row = r.scalar_one_or_none()
    return row


async def _sync_monitor_counts(db: AsyncSession, monitor_id: int) -> None:
    from models.prospective import AlertMatch, AlertMonitor

    total_r = await db.execute(
        select(func.count())
        .select_from(AlertMatch)
        .where(
            AlertMatch.monitor_id == monitor_id,
            AlertMatch.status.in_(list(MATCH_STATUSES_ACTIVE)),
        )
    )
    unread_r = await db.execute(
        select(func.count())
        .select_from(AlertMatch)
        .where(AlertMatch.monitor_id == monitor_id, AlertMatch.status == "new")
    )
    monitor_r = await db.execute(select(AlertMonitor).where(AlertMonitor.id == monitor_id))
    monitor = monitor_r.scalar_one_or_none()
    if monitor:
        monitor.match_count = total_r.scalar() or 0
        monitor.unread_count = unread_r.scalar() or 0


async def repair_monitor_counts(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    monitor_id: int | None = None,
) -> int:
    """Recompute match_count/unread_count from alert_matches (fixes stale counters)."""
    from models.prospective import AlertMonitor

    q = select(AlertMonitor.id)
    if monitor_id is not None:
        q = q.where(AlertMonitor.id == monitor_id)
    elif project_id is not None:
        q = q.where(AlertMonitor.project_id == project_id)

    ids = list((await db.execute(q)).scalars().all())
    for mid in ids:
        await _sync_monitor_counts(db, mid)
    if ids:
        await db.commit()
    return len(ids)


async def create_monitors_from_scenario(
    db: AsyncSession, project_id: int, scenario_id: int, narrative: str
) -> list[dict]:
    from models.prospective import AlertMonitor

    case_id = await _resolve_case_id(db, project_id)
    indicators = re.findall(r"→\s*(.+?)(?:\n|$)", narrative)
    if not indicators:
        indicators = [
            line.strip().lstrip("•-–").strip()
            for line in narrative.splitlines()
            if any(
                kw in line.lower()
                for kw in [
                    "augment", "presència", "declaració", "acord", "sanció", "conflicte",
                ]
            )
            and len(line.strip()) > 20
        ][:5]

    created = []
    for ind in indicators:
        ind = ind.strip()
        if not ind or len(ind) < 10:
            continue
        kws = _keywords(ind)
        db.add(
            AlertMonitor(
                project_id=project_id,
                scenario_id=scenario_id,
                case_id=case_id,
                indicator=ind,
                keywords=kws,
                osint_sources=_default_monitor_sources(),
                is_active=1,
            )
        )
        created.append({"indicator": ind, "keywords": kws})

    await db.commit()
    logger.info(
        "Created %d monitors for project %d / scenario %s",
        len(created), project_id, scenario_id,
    )
    return created


async def run_monitor_check(db: AsyncSession, monitor_id: int) -> dict[str, Any]:
    from models.prospective import AlertMatch, AlertMonitor, ProspectiveScenario
    from services.osint_service import OSINTService

    r = await db.execute(select(AlertMonitor).where(AlertMonitor.id == monitor_id))
    monitor = r.scalar_one_or_none()
    if not monitor or not monitor.is_active:
        return {"status": "skipped"}

    if not monitor.case_id:
        monitor.case_id = await _resolve_case_id(db, monitor.project_id)

    case_id = monitor.case_id
    keywords = list(monitor.keywords or [])
    if not keywords:
        keywords = _keywords(monitor.indicator or "")

    scenario_name = ""
    if monitor.scenario_id:
        sc_r = await db.execute(
            select(ProspectiveScenario.name).where(ProspectiveScenario.id == monitor.scenario_id)
        )
        scenario_name = sc_r.scalar_one_or_none() or ""

    osint = OSINTService(db)
    query_str = " ".join(keywords[:3])
    new_matches: list[dict[str, Any]] = []
    sources_checked: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for src in monitor.osint_sources or _default_monitor_sources():
        try:
            params: dict[str, Any] = {"query": query_str}
            if src == "gdelt":
                params["days"] = _monitor_gdelt_days(monitor)
                params["max_results"] = 50
            elif src == "tavily":
                params["max_results"] = 15
                params["search_depth"] = "advanced"
                params["topic"] = "news"
            res = await osint.execute_query(
                query_type=src, query_params=params, case_id=case_id
            )
            data = res.get("data")
            articles = flatten_osint_items(data) if isinstance(data, dict) else []
            src_matches = 0

            for article in articles:
                matched_kws, score = _match_article(article, keywords)
                if not matched_kws:
                    continue
                if not _passes_monitor_thresholds(monitor, matched_kws, score):
                    continue

                url = str(article.get("url") or "").strip()
                title = str(article.get("title") or "")[:500]
                excerpt = text_from_osint_item(article)[:500]

                if url and len(excerpt.strip()) < 200:
                    try:
                        enriched = await enrich_single_article(
                            {**article, "title": title, "url": url, "summary": excerpt}
                        )
                        excerpt = text_from_osint_item(enriched)[:500]
                    except Exception as exc:
                        logger.debug("Alert match enrich skipped: %s", exc)

                if not url and not title:
                    continue

                if url:
                    existing_r = await db.execute(
                        select(AlertMatch).where(
                            AlertMatch.monitor_id == monitor_id,
                            AlertMatch.url == url,
                        )
                    )
                else:
                    existing_r = await db.execute(
                        select(AlertMatch).where(
                            AlertMatch.monitor_id == monitor_id,
                            AlertMatch.title == title,
                        )
                    )
                existing = existing_r.scalar_one_or_none()

                if existing:
                    existing.last_seen_at = now
                    existing.seen_count = (existing.seen_count or 1) + 1
                    if existing.status == "archived":
                        existing.status = "new"
                    if score > (existing.match_score or 0):
                        existing.match_score = score
                        existing.matched_keywords = matched_kws
                else:
                    match = AlertMatch(
                        monitor_id=monitor_id,
                        project_id=monitor.project_id,
                        case_id=case_id,
                        scenario_id=monitor.scenario_id,
                        title=title,
                        url=url,
                        excerpt=excerpt,
                        source_type=src,
                        published_at=str(article.get("date") or ""),
                        osint_query_id=res.get("query_id"),
                        osint_result_id=res.get("result_id"),
                        matched_keywords=matched_kws,
                        match_score=score,
                        status="new",
                    )
                    db.add(match)
                    await db.flush()
                    new_matches.append(
                        _match_to_dict(
                            match,
                            monitor_indicator=monitor.indicator or "",
                            scenario_name=scenario_name,
                        )
                    )
                    src_matches += 1

            sources_checked.append({
                "source": src,
                "articles_scanned": len(articles),
                "matches": src_matches,
                "query_id": res.get("query_id"),
            })
        except Exception as exc:
            logger.warning("Monitor %d / src %s: %s", monitor_id, src, exc)
            sources_checked.append({"source": src, "error": str(exc)})

    monitor.last_checked = now
    if new_matches:
        monitor.last_match = now

    await db.commit()
    await _sync_monitor_counts(db, monitor_id)
    await db.commit()

    total_r = await db.execute(
        select(func.count())
        .select_from(AlertMatch)
        .where(
            AlertMatch.monitor_id == monitor_id,
            AlertMatch.status.in_(list(MATCH_STATUSES_ACTIVE)),
        )
    )

    return {
        "monitor_id": monitor_id,
        "indicator": monitor.indicator,
        "case_id": case_id,
        "scenario_name": scenario_name,
        "keywords": keywords,
        "new_matches": len(new_matches),
        "total_unique_matches": total_r.scalar() or 0,
        "matches": new_matches,
        "sources_checked": sources_checked,
        "last_checked": monitor.last_checked.isoformat() if monitor.last_checked else None,
    }


async def list_monitors(db: AsyncSession, project_id: int) -> list[dict]:
    from models.prospective import AlertMonitor

    await repair_monitor_counts(db, project_id=project_id)
    rows = (
        await db.execute(
            select(AlertMonitor)
            .where(AlertMonitor.project_id == project_id)
            .order_by(AlertMonitor.created_at.desc())
        )
    ).scalars().all()
    return [_monitor_to_dict(m) for m in rows]


async def update_monitor_settings(
    db: AsyncSession,
    monitor_id: int,
    *,
    lookback_days: int | None = None,
    horizon_label: str | None = None,
    min_match_score: float | None = None,
    min_keywords_matched: int | None = None,
    clear_thresholds: bool = False,
) -> dict[str, Any]:
    from models.prospective import AlertMonitor

    r = await db.execute(select(AlertMonitor).where(AlertMonitor.id == monitor_id))
    monitor = r.scalar_one_or_none()
    if not monitor:
        return {"error": "Monitor no trobat"}

    if clear_thresholds:
        monitor.lookback_days = None
        monitor.horizon_label = None
        monitor.min_match_score = None
        monitor.min_keywords_matched = None
    else:
        if lookback_days is not None:
            monitor.lookback_days = lookback_days if lookback_days > 0 else None
        if horizon_label is not None:
            monitor.horizon_label = horizon_label.strip() or None
        if min_match_score is not None:
            monitor.min_match_score = min_match_score if min_match_score >= 0 else None
        if min_keywords_matched is not None:
            monitor.min_keywords_matched = (
                min_keywords_matched if min_keywords_matched > 0 else None
            )

    await db.commit()
    await db.refresh(monitor)
    return _monitor_to_dict(monitor)


async def list_matches(
    db: AsyncSession,
    *,
    monitor_id: int | None = None,
    project_id: int | None = None,
    case_id: int | None = None,
    status: str | None = None,
    include_archived: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    from models.prospective import AlertMatch, AlertMonitor, ProspectiveScenario

    filters = []
    if monitor_id is not None:
        filters.append(AlertMatch.monitor_id == monitor_id)
    if project_id is not None:
        filters.append(AlertMatch.project_id == project_id)
    if case_id is not None:
        filters.append(AlertMatch.case_id == case_id)
    if status:
        filters.append(AlertMatch.status == status)
    elif not include_archived:
        filters.append(AlertMatch.status.in_(list(MATCH_STATUSES_ACTIVE)))
    if date_from:
        filters.append(AlertMatch.published_at >= date_from)
    if date_to:
        filters.append(AlertMatch.published_at <= date_to + "T23:59:59")

    count_q = select(func.count()).select_from(AlertMatch)
    for f in filters:
        count_q = count_q.where(f)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(AlertMatch, AlertMonitor, ProspectiveScenario)
        .join(AlertMonitor, AlertMatch.monitor_id == AlertMonitor.id)
        .outerjoin(ProspectiveScenario, AlertMatch.scenario_id == ProspectiveScenario.id)
    )
    for f in filters:
        q = q.where(f)
    q = q.order_by(AlertMatch.first_seen_at.desc()).offset(skip).limit(min(limit, 500))
    rows = (await db.execute(q)).all()

    items = [
        _match_to_dict(
            match,
            monitor_indicator=monitor.indicator or "",
            scenario_name=(scenario.name if scenario else "") or "",
        )
        for match, monitor, scenario in rows
    ]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total,
        "items": items,
    }


async def update_match_status(
    db: AsyncSession, match_id: int, status: str, action_taken: str = ""
) -> dict[str, Any]:
    from models.prospective import AlertMatch

    if status not in MATCH_STATUSES_ALL:
        raise ValueError(f"Estat invàlid: {status}")

    r = await db.execute(select(AlertMatch).where(AlertMatch.id == match_id))
    match = r.scalar_one_or_none()
    if not match:
        raise LookupError("Coincidència no trobada")

    match.status = status
    match.reviewed_at = datetime.now(timezone.utc)
    if action_taken:
        match.action_taken = action_taken
    await db.commit()
    await _sync_monitor_counts(db, match.monitor_id)
    await db.commit()
    return {"id": match_id, "status": status, "action_taken": match.action_taken}


async def archive_match(db: AsyncSession, match_id: int) -> dict[str, Any]:
    return await update_match_status(db, match_id, "archived", action_taken="archived")


async def extract_from_match(db: AsyncSession, match_id: int) -> dict[str, Any]:
    from models.prospective import AlertMatch
    from services.extract_service import ExtractService

    r = await db.execute(select(AlertMatch).where(AlertMatch.id == match_id))
    match = r.scalar_one_or_none()
    if not match:
        raise LookupError("Coincidència no trobada")
    if not match.case_id:
        raise ValueError("La coincidència no té cas associat")

    text = match.excerpt or match.title
    if not text.strip():
        raise ValueError("Sense text per extreure")

    if match.url and len(text.strip()) < 200:
        enriched = await enrich_single_article(
            {
                "title": match.title,
                "url": match.url,
                "summary": match.excerpt or "",
                "date": match.published_at,
            }
        )
        text = text_from_osint_item(enriched)
        if enriched.get("body") or enriched.get("summary"):
            match.excerpt = text[:500]

    svc = ExtractService(db)
    result = await svc.extract_single_article(
        case_id=match.case_id,
        title=match.title,
        url=match.url,
        date=match.published_at,
        text=text,
    )
    stmt_id = result.get("statement_id")
    if stmt_id:
        match.extracted_statement_id = stmt_id
        match.status = "actioned"
        match.action_taken = "extracted"
        match.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        await _sync_monitor_counts(db, match.monitor_id)
        await db.commit()
        from services.case_recalc_service import maybe_recalc_after_data_change

        await maybe_recalc_after_data_change(db, match.case_id, reason="alert_extract")

    return {
        "match_id": match_id,
        "case_id": match.case_id,
        "extracted_statement_id": stmt_id,
        "statements_created": result.get("statements_created", 0),
        "statements": result.get("statements", []),
    }


async def bulk_extract_matches(
    db: AsyncSession,
    *,
    case_id: int | None = None,
    monitor_id: int | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Extract statements from pending alert matches (new/reviewed, no statement yet)."""
    from models.prospective import AlertMatch

    q = select(AlertMatch).where(
        AlertMatch.extracted_statement_id.is_(None),
        AlertMatch.status.in_(["new", "reviewed"]),
    )
    if case_id is not None:
        q = q.where(AlertMatch.case_id == case_id)
    if monitor_id is not None:
        q = q.where(AlertMatch.monitor_id == monitor_id)
    q = q.order_by(AlertMatch.match_score.desc()).limit(max(1, min(limit, 50)))

    rows = (await db.execute(q)).scalars().all()
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    total_statements = 0

    for match in rows:
        try:
            out = await extract_from_match(db, match.id)
            total_statements += int(out.get("statements_created") or 0)
            results.append(out)
        except Exception as exc:
            errors.append({"match_id": match.id, "error": str(exc)})

    if total_statements > 0 and case_id is not None:
        from services.case_recalc_service import maybe_recalc_after_data_change

        await maybe_recalc_after_data_change(db, case_id, reason="alert_bulk_extract")

    return {
        "processed": len(results),
        "errors": errors,
        "statements_created": total_statements,
        "results": results,
    }


async def analyze_match(db: AsyncSession, match_id: int) -> dict[str, Any]:
    from models.prospective import AlertMatch, AlertMonitor, ProspectiveScenario
    from services.llm_service import LLMService, llm_config_error_message

    r = await db.execute(
        select(AlertMatch, AlertMonitor, ProspectiveScenario)
        .join(AlertMonitor, AlertMatch.monitor_id == AlertMonitor.id)
        .outerjoin(ProspectiveScenario, AlertMatch.scenario_id == ProspectiveScenario.id)
        .where(AlertMatch.id == match_id)
    )
    row = r.first()
    if not row:
        raise LookupError("Coincidència no trobada")
    match, monitor, scenario = row

    llm = LLMService(mode="extract")
    if not llm.configured:
        return {"error": llm_config_error_message(), "match_id": match_id}

    prompt = f"""Analitza aquesta coincidència OSINT dins el context d'un indicador d'alerta prospectiva.

INDICADOR D'ALERTA: {monitor.indicator}
ESCENARI: {scenario.name if scenario else '—'}
KEYWORDS COINCIDENTS: {', '.join(match.matched_keywords or [])}
FONT: {match.source_type} · {match.published_at}
URL: {match.url}

TITULAR: {match.title}
TEXT: {match.excerpt}

Respon en català amb JSON:
{{
  "summary": "2-3 frases sobre què implica per als actors",
  "affected_actors": ["actor1", "actor2"],
  "risk_level": "low|medium|high",
  "recommended_actions": ["acció 1", "acció 2"],
  "links_to_hypothesis": "com es relaciona amb l'indicador d'alerta"
}}"""

    try:
        raw = await llm.acomplete(prompt, max_tokens=800)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        analysis = json.loads(cleaned)
    except Exception as exc:
        fallback = raw[:600] if "raw" in locals() else str(exc)
        analysis = {"summary": fallback, "parse_error": True}

    summary_text = analysis.get("summary") or json.dumps(analysis, ensure_ascii=False)
    match.analysis_summary = summary_text
    if match.status == "new":
        match.status = "reviewed"
    match.action_taken = match.action_taken or "analyzed"
    match.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await _sync_monitor_counts(db, match.monitor_id)
    await db.commit()

    return {
        "match_id": match_id,
        "analysis": analysis,
        "analysis_summary": summary_text,
    }


def export_matches_csv(items: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    fields = [
        "id", "monitor_indicator", "scenario_name", "title", "url", "excerpt",
        "source_type", "published_at", "matched_keywords", "match_score", "status",
        "first_seen_at", "analysis_summary",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        row = dict(item)
        row["matched_keywords"] = ", ".join(row.get("matched_keywords") or [])
        writer.writerow(row)
    return buf.getvalue()


async def export_matches(
    db: AsyncSession,
    *,
    monitor_id: int | None = None,
    project_id: int | None = None,
    case_id: int | None = None,
    include_archived: bool = True,
    fmt: str = "json",
) -> tuple[str, str, str]:
    """Return (content, media_type, filename)."""
    data = await list_matches(
        db,
        monitor_id=monitor_id,
        project_id=project_id,
        case_id=case_id,
        include_archived=include_archived,
        skip=0,
        limit=10_000,
    )
    items = data["items"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if fmt == "csv":
        return (
            export_matches_csv(items),
            "text/csv; charset=utf-8",
            f"alert_matches_{stamp}.csv",
        )
    return (
        json.dumps({"exported_at": datetime.now(timezone.utc).isoformat(), "items": items}, ensure_ascii=False, indent=2),
        "application/json; charset=utf-8",
        f"alert_matches_{stamp}.json",
    )


async def list_triggered_summary(
    db: AsyncSession,
    user_id: int | None = None,
    case_id: int | None = None,
) -> dict[str, int]:
    from models.case import Case
    from models.prospective import AlertMatch, AlertMonitor, ProspectiveProject

    query = select(AlertMonitor).join(
        ProspectiveProject, AlertMonitor.project_id == ProspectiveProject.id
    )
    if case_id is not None:
        query = query.where(ProspectiveProject.case_id == case_id)
    elif user_id is not None:
        query = query.join(Case, ProspectiveProject.case_id == Case.id).where(
            Case.user_id == user_id
        )

    monitors = (await db.execute(query)).scalars().all()
    for mid in {m.id for m in monitors}:
        await _sync_monitor_counts(db, mid)
    if monitors:
        await db.commit()
        for m in monitors:
            await db.refresh(m)

    triggered = [m for m in monitors if (m.match_count or 0) > 0]
    unread = sum(m.unread_count or 0 for m in monitors)

    new_matches = 0
    if case_id is not None:
        nm_r = await db.execute(
            select(func.count())
            .select_from(AlertMatch)
            .where(AlertMatch.case_id == case_id, AlertMatch.status == "new")
        )
        new_matches = nm_r.scalar() or 0

    return {
        "triggered_count": len(triggered),
        "total_matches": sum(m.match_count or 0 for m in triggered),
        "total_monitors": len(monitors),
        "unread_count": unread,
        "new_matches": new_matches,
    }


async def _run_single_monitor_check(
    monitor_id: int, db: AsyncSession | None = None
) -> dict[str, Any]:
    if db is not None:
        try:
            return await run_monitor_check(db, monitor_id)
        except Exception as exc:
            logger.warning("Monitor %d failed: %s", monitor_id, exc)
            return {"status": "error", "monitor_id": monitor_id, "message": str(exc)}

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            return await run_monitor_check(session, monitor_id)
        except Exception as exc:
            logger.warning("Monitor %d failed: %s", monitor_id, exc)
            return {"status": "error", "monitor_id": monitor_id, "message": str(exc)}


async def run_all_active_monitors(db: AsyncSession | None = None) -> dict:
    from app.database import AsyncSessionLocal
    from models.prospective import AlertMonitor

    if db is None:
        async with AsyncSessionLocal() as session:
            monitor_ids = (
                await session.execute(
                    select(AlertMonitor.id).where(AlertMonitor.is_active == 1)
                )
            ).scalars().all()
    else:
        monitor_ids = (
            await db.execute(
                select(AlertMonitor.id).where(AlertMonitor.is_active == 1)
            )
        ).scalars().all()

    results: list[dict[str, Any]] = []
    total_new = 0
    for monitor_id in monitor_ids:
        r = await _run_single_monitor_check(monitor_id, db=db)
        results.append(r)
        total_new += r.get("new_matches", 0)
        if db is None:
            await asyncio.sleep(1.5)

    return {"checked": len(results), "new_matches": total_new, "results": results}
