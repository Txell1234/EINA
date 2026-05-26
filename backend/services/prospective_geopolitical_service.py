"""Bridge GeopoliticalAdvanced data into the Godet prospective pipeline."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.geopolitical import BilateralRelation, DiplomaticEvent, RelationStatus

logger = logging.getLogger(__name__)

# Canonical English key → aliases (CA/EN, actors OSINT, noms de països a BD)
COUNTRY_ALIASES: dict[str, list[str]] = {
    "china": [
        "china", "chinese", "xina", "xinesa", "xines", "bri", "beijing", "pekin",
        "govern de la xina", "people's republic",
    ],
    "india": ["india", "indian", "índia", "indi", "modi", "delhi", "new delhi"],
    "united states": [
        "united states", "usa", "u.s.", "us ", " eua", "eua", "america", "american",
        "washington", "govern dels eua", "donald trump", "u.s. president",
    ],
    "japan": ["japan", "japanese", "japó", "japon", "japones", "japonès", "japonesa", "tokyo", "govern del japó"],
    "australia": ["australia", "australian", "austràlia", "canberra"],
    "south korea": ["south korea", "korea", "corea del sud", "corea", "seoul"],
    "taiwan": ["taiwan", "taiwanese", "taipei"],
    "europe": ["europe", "european", "europa", "ue", "eu", "unió europea", "european union"],
    "asean": ["asean", "sud-est asiàtic", "southeast asia"],
    "quad": ["quad", "quadrilateral"],
    "italy": ["italy", "italian", "itàlia", "italia", "rome"],
    "iran": ["iran", "iranian", "irgc", "tehran"],
    "russia": ["russia", "russian", "rússia", "moscow", "moscou"],
    "uk": ["united kingdom", "uk", "britain", "british", "london"],
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value).lower()
    raw = str(value).lower()
    if "." in raw:
        return raw.rsplit(".", 1)[-1]
    return raw


def _aliases_for(label: str) -> list[str]:
    n = _norm(label)
    for canonical, aliases in COUNTRY_ALIASES.items():
        group = [canonical, *aliases]
        if any(a in n or n in a for a in group):
            return group
    return [n]


def variable_text(var: dict) -> str:
    return _norm(
        f"{var.get('code', '')} {var.get('name', '')} {var.get('desc', var.get('description', ''))}"
    )


def variable_matches_country(var: dict, country: str) -> bool:
    blob = variable_text(var)
    return any(alias in blob for alias in _aliases_for(country))


def _status_influence(status: RelationStatus | str | None, score: float) -> int:
    st = _enum_value(status) or "stable"
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


def _posture_to_influence(posture_value: int | None) -> int:
    pv = abs(int(posture_value or 0))
    if pv >= 2:
        return 3
    if pv == 1:
        return 2
    return 1


def _merge_suggestion(
    matrix: dict[tuple[int, int], dict],
    row: int,
    col: int,
    value: int,
    reason: str,
    source: str,
) -> None:
    key = (row, col)
    if key not in matrix or matrix[key]["value"] < value:
        matrix[key] = {
            "row": row,
            "col": col,
            "value": min(3, max(1, value)),
            "reason": reason,
            "source": source,
        }


class ProspectiveGeopoliticalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def micmac_suggestions(
        self, case_id: int, variables: list[dict]
    ) -> dict[str, Any]:
        if not variables:
            return {
                "case_id": case_id,
                "relations_count": 0,
                "events_count": 0,
                "statements_count": 0,
                "suggestions": [],
                "message": "Afegeix almenys una variable abans d'enriquir.",
                "sources_used": [],
            }

        rel_r = await self.db.execute(
            select(BilateralRelation).where(BilateralRelation.case_id == case_id)
        )
        evt_r = await self.db.execute(
            select(DiplomaticEvent).where(DiplomaticEvent.case_id == case_id)
        )
        stmt_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision != "REMOVE")
            .limit(400)
        )
        relations = list(rel_r.scalars().all())
        events = list(evt_r.scalars().all())
        statements = list(stmt_r.scalars().all())

        n = len(variables)
        matrix: dict[tuple[int, int], dict] = {}
        sources_used: list[str] = []

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
                        f"({_enum_value(rel.status)}, score={rel.relation_score:.0f})"
                    )
                    _merge_suggestion(matrix, i, j, val, reason, "bilateral_relation")
            if relations:
                sources_used.append("bilateral_relation")

        for evt in events:
            imp = _enum_value(evt.importance)
            if imp not in ("high", "medium"):
                continue
            countries = evt.countries or []
            if len(countries) < 2:
                continue
            boost = 3 if imp == "high" else 2
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
                    reason = f"Esdeveniment: {(evt.title or '')[:80]}"
                    _merge_suggestion(matrix, i, j, boost, reason, "diplomatic_event")
            if events:
                sources_used.append("diplomatic_event")

        stmt_hits = 0
        for stmt in statements:
            actor = stmt.actor or ""
            target = stmt.posture_toward or ""
            if not actor or not target:
                continue
            val = _posture_to_influence(stmt.posture_value)
            excerpt = (stmt.statement or "")[:100]
            for i in range(n):
                if not variable_matches_country(variables[i], actor):
                    continue
                for j in range(n):
                    if i == j:
                        continue
                    if not variable_matches_country(variables[j], target):
                        continue
                    reason = f"Postura {actor} → {target}: {excerpt}"
                    _merge_suggestion(matrix, i, j, val, reason, "extracted_statement")
                    stmt_hits += 1

        if stmt_hits:
            sources_used.append("extracted_statement")

        suggestions = sorted(matrix.values(), key=lambda s: (-s["value"], s["row"], s["col"]))

        message: str | None = None
        if not suggestions:
            if not statements and not relations and not events:
                message = (
                    "No hi ha dades geopolítiques al cas. Executa l'extracció (Pas 0) "
                    "o recollida OSINT abans d'enriquir."
                )
            else:
                message = (
                    "Cap variable coincideix amb actors/països de les dades del cas. "
                    "Inclou noms com «Japó», «Xina», «EUA» al nom o descripció de cada variable."
                )

        return {
            "case_id": case_id,
            "relations_count": len(relations),
            "events_count": len(events),
            "statements_count": len(statements),
            "suggestions": suggestions,
            "sources_used": list(dict.fromkeys(sources_used)),
            "message": message,
            "relations_summary": [
                {
                    "country1": r.country1,
                    "country2": r.country2,
                    "status": _enum_value(r.status),
                    "score": r.relation_score,
                }
                for r in relations[:20]
            ],
        }
