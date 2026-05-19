"""Bridge GeopoliticalAdvanced data into the Godet prospective pipeline."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.geopolitical import BilateralRelation, DiplomaticEvent, RelationStatus

COUNTRY_KEYWORDS: dict[str, list[str]] = {
    "xina": ["xina", "china", "chinese", "xinesa", "bri", "beijing", "pekin"],
    "índia": ["índia", "india", "indian", "indi", "modi", "delhi"],
    "eua": ["eua", "usa", "united states", "america", "washington"],
    "japó": ["japó", "japan", "japanese", "tokyo"],
    "austràlia": ["austràlia", "australia", "australian", "canberra"],
    "quad": ["quad", "quadrilateral"],
    "ue": ["ue", "eu", "unió europea", "european union", "europa", "europe"],
    "asean": ["asean", "sud-est asiàtic", "southeast asia"],
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def variable_text(var: dict) -> str:
    return _norm(
        f"{var.get('code', '')} {var.get('name', '')} {var.get('desc', var.get('description', ''))}"
    )


def variable_matches_country(var: dict, country: str) -> bool:
    blob = variable_text(var)
    country_n = _norm(country)
    keys = COUNTRY_KEYWORDS.get(country_n, [country_n])
    return any(k in blob for k in keys)


def _status_influence(status: RelationStatus | str | None, score: float) -> int:
    st = str(status or "stable").lower()
    if st in ("critical", "deteriorating"):
        base = 3
    elif st == "stable":
        base = 2
    else:
        base = 1
    if score < 35:
        return min(3, base + 1)
    if score > 70:
        return max(1, base - 1)
    return base


def _relation_influence(rel: BilateralRelation) -> int:
    coop = max(
        rel.political_cooperation or 0,
        rel.economic_cooperation or 0,
        rel.security_cooperation or 0,
    )
    low_coop = coop < 40
    score = rel.relation_score or 50
    inf = _status_influence(rel.status, score)
    if low_coop and inf < 3:
        inf += 1
    return min(3, max(1, inf))


class ProspectiveGeopoliticalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def micmac_suggestions(
        self, case_id: int, variables: list[dict]
    ) -> dict[str, Any]:
        rel_r = await self.db.execute(
            select(BilateralRelation).where(BilateralRelation.case_id == case_id)
        )
        evt_r = await self.db.execute(
            select(DiplomaticEvent).where(DiplomaticEvent.case_id == case_id)
        )
        relations = list(rel_r.scalars().all())
        events = list(evt_r.scalars().all())

        n = len(variables)
        matrix: dict[tuple[int, int], dict] = {}

        for rel in relations:
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    vi, vj = variables[i], variables[j]
                    linked = (
                        variable_matches_country(vi, rel.country1)
                        and variable_matches_country(vj, rel.country2)
                    ) or (
                        variable_matches_country(vi, rel.country2)
                        and variable_matches_country(vj, rel.country1)
                    )
                    if not linked:
                        continue
                    val = _relation_influence(rel)
                    reason = (
                        f"Relació {rel.country1}–{rel.country2} "
                        f"({rel.status.value if hasattr(rel.status, 'value') else rel.status}, "
                        f"score={rel.relation_score:.0f})"
                    )
                    key = (i, j)
                    if key not in matrix or matrix[key]["value"] < val:
                        matrix[key] = {
                            "row": i,
                            "col": j,
                            "value": val,
                            "reason": reason,
                            "source": "bilateral_relation",
                        }

        for evt in events:
            if str(evt.importance or "").lower() not in ("high", "medium"):
                continue
            countries = evt.countries or []
            if len(countries) < 2:
                continue
            boost = 3 if str(evt.importance).lower() == "high" else 2
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    vi, vj = variables[i], variables[j]
                    linked = any(
                        variable_matches_country(vi, c1) and variable_matches_country(vj, c2)
                        for c1 in countries
                        for c2 in countries
                        if c1 != c2
                    )
                    if not linked:
                        continue
                    key = (i, j)
                    reason = f"Esdeveniment: {evt.title[:80]}"
                    if key not in matrix or matrix[key]["value"] < boost:
                        matrix[key] = {
                            "row": i,
                            "col": j,
                            "value": boost,
                            "reason": reason,
                            "source": "diplomatic_event",
                        }

        suggestions = sorted(matrix.values(), key=lambda s: (-s["value"], s["row"], s["col"]))
        return {
            "case_id": case_id,
            "relations_count": len(relations),
            "events_count": len(events),
            "suggestions": suggestions,
            "relations_summary": [
                {
                    "country1": r.country1,
                    "country2": r.country2,
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "score": r.relation_score,
                }
                for r in relations[:20]
            ],
        }
