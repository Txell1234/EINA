"""
Policy–industry linkage: companies, contractors and beneficiaries per premise/theme.
Additive layer over OSINT extraction and case topic profiles.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.qualitative import Premise
from schemas.actor_typology import THEME_LABELS
from services.actor_impact_utils import canonical_actor
from services.case_topic_relevance import build_case_topic_profile
from services.policy_industry_profiles import (
    all_reference_names,
    looks_like_company,
    profiles_for_themes,
)

logger = logging.getLogger(__name__)

_POLICY_THEMES = frozenset(
    {"rearmament", "defense_procurement", "indo_pacific", "supply_chain", "market_entry", "regulatory"}
)

_ROLE_LABELS: dict[str, str] = {
    "prime_contractor": "Contractista principal",
    "subcontractor": "Subcontractista",
    "supplier": "Proveïdor",
    "investor": "Inversor",
    "beneficiary": "Beneficiari indirecte",
    "offset_partner": "Partner offset",
    "integrator": "Integrador de sistemes",
}


def _normalize_company_key(name: str) -> str:
    return canonical_actor(name) or (name or "").strip().lower()


def _region_from_country(country: str) -> str:
    return "domestic" if (country or "").upper() in ("JP", "JPN", "JAPAN", "JAPÓ", "JAPO") else "overseas"


def _score_premise_match(premise: str, company: dict[str, Any]) -> float:
    if not premise:
        return 0.0
    blob = premise.lower()
    score = 0.0
    for token in [
        company.get("name", ""),
        *(company.get("aliases") or []),
        *(company.get("sectors") or []),
        company.get("policy_link", ""),
    ]:
        for word in re.findall(r"[a-zà-ÿ0-9]{4,}", (token or "").lower()):
            if word in blob:
                score += 1.0
    for theme in company.get("matched_themes") or []:
        if theme.replace("_", " ") in blob or theme in blob:
            score += 2.0
    return score


def _statement_to_company(stmt: ExtractedStatement, ref_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    actor = (stmt.actor or "").strip()
    if not actor:
        return None
    actor_type = (stmt.actor_type or "").lower()
    inst = (getattr(stmt, "institution_subtype", None) or "").lower()
    is_corp = actor_type == "company" or inst == "corporate" or looks_like_company(actor)
    if not is_corp:
        return None

    key = actor.lower()
    ref = ref_index.get(key)
    if not ref:
        for alias_key, prof in ref_index.items():
            if alias_key in key or key in alias_key:
                ref = prof
                break

    country = ref.get("country", "XX") if ref else "XX"
    if country == "XX" and any(t in actor.lower() for t in ("japan", "japó", "japo", "tokyo")):
        country = "JP"

    return {
        "name": ref["name"] if ref else actor,
        "country": country,
        "region": _region_from_country(country) if country != "XX" else "unknown",
        "roles": list(ref.get("roles") or ["beneficiary"]) if ref else ["beneficiary"],
        "sectors": list(ref.get("sectors") or []),
        "beneficiary_rationale": ref.get("beneficiary_rationale") if ref else (
            f"Mencionada en declaracions OSINT sobre {stmt.topic or 'política/defensa'}."
        ),
        "policy_link": ref.get("policy_link", "") if ref else (stmt.topic or ""),
        "contractor_relationships": list(ref.get("contractor_relationships") or []) if ref else [],
        "confidence": "high" if ref else "medium",
        "source": "osint",
        "matched_themes": list(ref.get("matched_themes") or []),
        "evidence": [
            {
                "statement_id": stmt.id,
                "excerpt": (stmt.statement or "")[:280],
                "url": stmt.source_url or "",
                "topic": stmt.topic or "",
                "posture_value": stmt.posture_value,
            }
        ],
    }


def _merge_companies(existing: dict[str, dict[str, Any]], incoming: dict[str, Any]) -> None:
    key = _normalize_company_key(incoming["name"])
    if not key:
        return
    if key not in existing:
        existing[key] = incoming
        return
    cur = existing[key]
    for role in incoming.get("roles") or []:
        if role not in cur["roles"]:
            cur["roles"].append(role)
    for sec in incoming.get("sectors") or []:
        if sec not in cur["sectors"]:
            cur["sectors"].append(sec)
    for th in incoming.get("matched_themes") or []:
        if th not in cur.get("matched_themes", []):
            cur.setdefault("matched_themes", []).append(th)
    cur["evidence"] = (cur.get("evidence") or []) + (incoming.get("evidence") or [])
    if incoming.get("source") == "osint":
        cur["confidence"] = "high" if cur.get("source") == "reference" else cur.get("confidence", "medium")
    for rel in incoming.get("contractor_relationships") or []:
        partners = {r.get("partner") for r in cur.get("contractor_relationships") or []}
        if rel.get("partner") not in partners:
            cur.setdefault("contractor_relationships", []).append(rel)


def _reference_to_company(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": ref["name"],
        "country": ref.get("country", "XX"),
        "region": ref.get("region", _region_from_country(ref.get("country", "XX"))),
        "roles": list(ref.get("roles") or []),
        "sectors": list(ref.get("sectors") or []),
        "beneficiary_rationale": ref.get("beneficiary_rationale", ""),
        "policy_link": ref.get("policy_link", ""),
        "contractor_relationships": list(ref.get("contractor_relationships") or []),
        "confidence": "medium",
        "source": "reference",
        "matched_themes": list(ref.get("matched_themes") or []),
        "evidence": [],
    }


async def _load_recent_premises(db: AsyncSession, case_id: int, limit: int = 5) -> list[dict[str, Any]]:
    r = await db.execute(
        select(Premise)
        .where(Premise.case_id == case_id)
        .order_by(Premise.id.desc())
        .limit(limit)
    )
    return [{"id": p.id, "text": (p.premise_text or "")[:500]} for p in r.scalars().all()]


async def _llm_enrich(
    *,
    case_name: str,
    case_description: str,
    premise: str,
    themes: list[str],
    companies: list[dict[str, Any]],
) -> dict[str, Any] | None:
    from services.llm_service import LLMService, resolve_provider

    if not resolve_provider():
        return None

    llm = LLMService(mode="extract")
    company_names = [c["name"] for c in companies[:20]]
    system = """You are a defense-industry and geopolitical policy analyst.
Return ONLY valid JSON mapping policy premises to industrial stakeholders.
Focus on WHO benefits and WHY (contractors, suppliers, offset partners) — domestic and overseas.
Cite policy mechanisms (budget, procurement, alliances, export controls)."""
    user = json.dumps(
        {
            "case": case_name,
            "context": case_description[:1500],
            "premise": premise[:2000],
            "themes": themes,
            "known_companies": company_names,
            "instruction": (
                "Add or refine companies with beneficiary_rationale and policy_link. "
                "Include contractor_relationships where relevant."
            ),
        },
        ensure_ascii=False,
    )
    try:
        raw = await asyncio.to_thread(
            llm.complete,
            user,
            system,
            4096,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("policy_industry LLM enrich failed: %s", exc)
        return None


class PolicyIndustryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_map(
        self,
        case_id: int,
        *,
        premise: str | None = None,
        enrich: bool = False,
    ) -> dict[str, Any]:
        from models.case import Case

        case_r = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_r.scalar_one_or_none()
        if not case:
            return {"case_id": case_id, "found": False}

        profile = build_case_topic_profile(case.name or "", case.description or "")
        themes = set(profile.themes) & _POLICY_THEMES
        if not themes:
            themes = set(profile.themes) or {"rearmament"} if "jap" in (case.description or "").lower() else set()

        ref_index = all_reference_names()
        merged: dict[str, dict[str, Any]] = {}

        for ref in profiles_for_themes(themes):
            _merge_companies(merged, _reference_to_company(ref))

        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING"]))
        )
        for stmt in stmts_r.scalars().all():
            comp = _statement_to_company(stmt, ref_index)
            if comp:
                _merge_companies(merged, comp)

        companies = list(merged.values())
        active_premise = (premise or "").strip()

        premises = await _load_recent_premises(self.db, case_id)
        premise_links: list[dict[str, Any]] = []

        if active_premise:
            ranked = sorted(
                companies,
                key=lambda c: _score_premise_match(active_premise, c),
                reverse=True,
            )
            for c in ranked[:15]:
                score = _score_premise_match(active_premise, c)
                if score > 0 or c.get("source") == "reference":
                    premise_links.append(
                        {
                            "company": c["name"],
                            "relevance_score": round(score, 1),
                            "why": c.get("beneficiary_rationale", ""),
                            "policy_mechanism": c.get("policy_link", ""),
                        }
                    )
        else:
            for p in premises:
                for c in companies:
                    score = _score_premise_match(p["text"], c)
                    if score >= 2:
                        premise_links.append(
                            {
                                "premise_id": p["id"],
                                "premise_excerpt": p["text"][:120],
                                "company": c["name"],
                                "relevance_score": round(score, 1),
                                "why": c.get("beneficiary_rationale", ""),
                            }
                        )

        llm_block: dict[str, Any] | None = None
        if enrich and active_premise:
            llm_block = await _llm_enrich(
                case_name=case.name or "",
                case_description=case.description or "",
                premise=active_premise,
                themes=sorted(themes),
                companies=companies,
            )
            if llm_block:
                for extra in llm_block.get("companies") or []:
                    if isinstance(extra, dict) and extra.get("name"):
                        row = {
                            "name": extra["name"],
                            "country": extra.get("country", "XX"),
                            "region": extra.get("region") or _region_from_country(extra.get("country", "XX")),
                            "roles": extra.get("roles") or ["beneficiary"],
                            "sectors": extra.get("sectors") or [],
                            "beneficiary_rationale": extra.get("beneficiary_rationale", extra.get("why", "")),
                            "policy_link": extra.get("policy_link", ""),
                            "contractor_relationships": extra.get("contractor_relationships") or [],
                            "confidence": "medium",
                            "source": "llm",
                            "matched_themes": extra.get("themes") or [],
                            "evidence": [],
                        }
                        _merge_companies(merged, row)
                companies = list(merged.values())

        domestic = [c for c in companies if c.get("region") == "domestic"]
        overseas = [c for c in companies if c.get("region") == "overseas"]
        unknown = [c for c in companies if c.get("region") not in ("domestic", "overseas")]

        supply_links: list[dict[str, Any]] = []
        for c in companies:
            for rel in c.get("contractor_relationships") or []:
                supply_links.append(
                    {
                        "from": c["name"],
                        "to": rel.get("partner"),
                        "type": rel.get("type"),
                        "from_region": c.get("region"),
                        "to_region": rel.get("region"),
                    }
                )

        return {
            "case_id": case_id,
            "found": True,
            "case_name": case.name,
            "focus_label": profile.focus_label,
            "themes": sorted(themes),
            "theme_labels": {t: THEME_LABELS.get(t, t) for t in themes},
            "premise": active_premise or None,
            "premises_in_case": premises,
            "analysis_lenses": ["public_sector", "private_sector", "supply_chain", "market_entry"],
            "summary": {
                "companies_total": len(companies),
                "domestic": len(domestic),
                "overseas": len(overseas),
                "from_osint": sum(1 for c in companies if c.get("source") == "osint"),
                "from_reference": sum(1 for c in companies if c.get("source") == "reference"),
                "from_llm": sum(1 for c in companies if c.get("source") == "llm"),
                "premise_links": len(premise_links),
            },
            "companies": sorted(companies, key=lambda x: (x.get("region", ""), x.get("name", ""))),
            "by_region": {
                "domestic": domestic,
                "overseas": overseas,
                "unknown": unknown,
            },
            "premise_links": premise_links[:30],
            "supply_links": supply_links,
            "role_labels": _ROLE_LABELS,
            "llm_enrichment": llm_block,
            "enrich_available": bool(enrich),
        }
