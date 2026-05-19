"""
Alert Monitor Service — turns scenario early warning indicators
into automated OSINT queries.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_STOP = {
    "de", "del", "la", "el", "els", "les", "un", "una", "i", "o", "a", "en", "per", "amb",
    "que", "es", "ha", "han", "si", "però", "com", "tot", "entre", "sobre", "augment",
    "increment", "reducció", "canvi", "nova", "nou", "the", "of", "in", "at", "by", "an",
    "or", "and", "to", "is", "are", "that", "with", "nova", "nous", "noves",
}


def _keywords(text: str) -> list[str]:
    caps = re.findall(r"[A-ZÀÁÂÃÄÅ][a-zàáâãäå]{2,}", text)
    words = [
        w for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", text.lower()) if w not in _STOP
    ]
    return list(dict.fromkeys(caps + words))[:4]


async def create_monitors_from_scenario(
    db: AsyncSession, project_id: int, scenario_id: int, narrative: str
) -> list[dict]:
    from models.prospective import AlertMonitor

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
                indicator=ind,
                keywords=kws,
                osint_sources=["gdelt", "google_news", "reddit"],
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
    from models.prospective import AlertMonitor
    from services.osint_service import OSINTService

    r = await db.execute(select(AlertMonitor).where(AlertMonitor.id == monitor_id))
    monitor = r.scalar_one_or_none()
    if not monitor or not monitor.is_active:
        return {"status": "skipped"}

    osint = OSINTService(db)
    query = " ".join((monitor.keywords or [])[:3])
    matches = 0
    sources = []

    for src in monitor.osint_sources or ["gdelt"]:
        try:
            params: dict = {"query": query}
            if src == "gdelt":
                params["days"] = 3
            res = await osint.execute_query(
                query_type=src, query_params=params, case_id=None
            )
            count = 0
            data = res.get("data")
            if isinstance(data, dict):
                count = data.get("count", 0) or len(data.get("articles", []))
            matches += count
            sources.append({"source": src, "count": count})
        except Exception as exc:
            logger.warning("Monitor %d / src %s: %s", monitor_id, src, exc)
            sources.append({"source": src, "error": str(exc)})

    monitor.last_checked = datetime.now(timezone.utc)
    if matches > 0:
        monitor.last_match = datetime.now(timezone.utc)
        monitor.match_count = (monitor.match_count or 0) + matches
    await db.commit()

    return {
        "monitor_id": monitor_id,
        "indicator": monitor.indicator,
        "keywords": monitor.keywords,
        "matches_found": matches,
        "sources": sources,
        "last_checked": monitor.last_checked.isoformat(),
    }


async def list_monitors(db: AsyncSession, project_id: int) -> list[dict]:
    from models.prospective import AlertMonitor

    rows = (
        await db.execute(
            select(AlertMonitor)
            .where(AlertMonitor.project_id == project_id)
            .order_by(AlertMonitor.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": m.id,
            "indicator": m.indicator,
            "keywords": m.keywords,
            "osint_sources": m.osint_sources,
            "is_active": bool(m.is_active),
            "match_count": m.match_count,
            "last_checked": m.last_checked.isoformat() if m.last_checked else None,
            "last_match": m.last_match.isoformat() if m.last_match else None,
        }
        for m in rows
    ]


async def run_all_active_monitors(db: AsyncSession) -> dict:
    """Run OSINT checks for every active monitor."""
    from models.prospective import AlertMonitor

    rows = (
        await db.execute(select(AlertMonitor).where(AlertMonitor.is_active == 1))
    ).scalars().all()
    results = []
    for monitor in rows:
        try:
            r = await run_monitor_check(db, monitor.id)
            results.append(r)
        except Exception as exc:
            logger.warning("Monitor %d failed: %s", monitor.id, exc)
    return {"checked": len(results), "results": results}
