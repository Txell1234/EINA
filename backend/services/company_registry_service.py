"""Aggregate companies linked to a case from Godet, Q2FS, OSINT and Policy×Industry."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import ProspectiveActor, ProspectiveProject
from models.prospective_inquiry import ProspectiveInquiry
from services.actor_impact_utils import canonical_actor
from services.policy_industry_profiles import looks_like_company
from services.policy_industry_service import PolicyIndustryService, _ROLE_LABELS

_REGISTRY_ROLE_LABELS: dict[str, str] = {
    **_ROLE_LABELS,
    "strategic_actor": "Actor estratègic Godet",
    "market_opportunity": "Oportunitat de mercat",
    "affected": "Afectada / exposada",
}

_CREATION_KEYWORDS = (
    "market entry",
    "entrada a mercat",
    "nova empresa",
    "new company",
    "startup",
    "spin-off",
    "spinoff",
    "licitació",
    "procurement opening",
    "joint venture",
    "greenfield",
    "entrant",
    "new market",
    "creació d'empreses",
    "creation d'entreprises",
)


def _company_key(name: str) -> str:
    return canonical_actor(name) or (name or "").strip().lower()


def _detect_creation_signal(*texts: str) -> tuple[bool, str | None]:
    blob = " ".join(t for t in texts if t).lower()
    for kw in _CREATION_KEYWORDS:
        if kw in blob:
            return True, kw
    return False, None


def _empty_entry(name: str) -> dict[str, Any]:
    from services.policy_industry_profiles import ticker_for_company

    key = _company_key(name)
    return {
        "key": key,
        "name": name,
        "ticker": ticker_for_company(name) or "",
        "country": "XX",
        "region": "unknown",
        "roles": [],
        "sectors": [],
        "beneficiary_rationale": "",
        "policy_link": "",
        "creation_signal": False,
        "creation_note": None,
        "linked_aspects": [],
        "origins": [],
        "sources": [],
        "confidence": "medium",
        "evidence_count": 0,
        "contractor_relationships": [],
    }


def _merge_registry(existing: dict[str, dict[str, Any]], incoming: dict[str, Any]) -> None:
    key = incoming.get("key") or _company_key(incoming.get("name", ""))
    if not key:
        return
    incoming["key"] = key
    if key not in existing:
        existing[key] = incoming
        return
    cur = existing[key]
    for field in ("country", "region", "beneficiary_rationale", "policy_link"):
        if not cur.get(field) or cur.get(field) in ("XX", "unknown", ""):
            if incoming.get(field) and incoming[field] not in ("XX", "unknown", ""):
                cur[field] = incoming[field]
    for role in incoming.get("roles") or []:
        if role not in cur["roles"]:
            cur["roles"].append(role)
    for sec in incoming.get("sectors") or []:
        if sec not in cur["sectors"]:
            cur["sectors"].append(sec)
    for asp in incoming.get("linked_aspects") or []:
        ids = {(a.get("type"), a.get("id")) for a in cur.get("linked_aspects") or []}
        if (asp.get("type"), asp.get("id")) not in ids:
            cur.setdefault("linked_aspects", []).append(asp)
    for origin in incoming.get("origins") or []:
        if origin not in cur["origins"]:
            cur["origins"].append(origin)
    cur["sources"] = (cur.get("sources") or []) + (incoming.get("sources") or [])
    cur["evidence_count"] = cur.get("evidence_count", 0) + incoming.get("evidence_count", 0)
    if incoming.get("creation_signal"):
        cur["creation_signal"] = True
        cur["creation_note"] = incoming.get("creation_note") or cur.get("creation_note")
    for rel in incoming.get("contractor_relationships") or []:
        partners = {r.get("partner") for r in cur.get("contractor_relationships") or []}
        if rel.get("partner") not in partners:
            cur.setdefault("contractor_relationships", []).append(rel)
    if incoming.get("confidence") == "high":
        cur["confidence"] = "high"
    elif incoming.get("origins") and "osint" in incoming["origins"] and cur.get("confidence") != "high":
        cur["confidence"] = "high"


def _policy_origin(source: str | None) -> str:
    src = (source or "reference").lower()
    if src in ("osint", "llm", "reference"):
        return src if src != "reference" else "policy_industry"
    return "policy_industry"


def _from_policy_company(c: dict[str, Any], *, aspect: dict[str, Any] | None = None) -> dict[str, Any]:
    name = c.get("name") or ""
    created, note = _detect_creation_signal(
        c.get("beneficiary_rationale") or "",
        c.get("policy_link") or "",
    )
    origin = _policy_origin(c.get("source"))
    entry = _empty_entry(name)
    entry.update(
        {
            "country": c.get("country", "XX"),
            "region": c.get("region", "unknown"),
            "roles": list(c.get("roles") or ["beneficiary"]),
            "sectors": list(c.get("sectors") or []),
            "beneficiary_rationale": c.get("beneficiary_rationale") or "",
            "policy_link": c.get("policy_link") or "",
            "creation_signal": created,
            "creation_note": note,
            "origins": [origin],
            "confidence": c.get("confidence", "medium"),
            "evidence_count": len(c.get("evidence") or []),
            "contractor_relationships": list(c.get("contractor_relationships") or []),
            "ticker": c.get("ticker") or entry.get("ticker") or "",
            "sources": [
                {
                    "origin": origin,
                    "excerpt": (ev.get("excerpt") or ev.get("topic") or "")[:200],
                    "field": "evidence",
                }
                for ev in (c.get("evidence") or [])[:5]
            ],
        }
    )
    if aspect:
        entry["linked_aspects"] = [aspect]
    if created and "market_opportunity" not in entry["roles"]:
        entry["roles"].append("market_opportunity")
    return entry


async def _resolve_project_id(
    db: AsyncSession,
    case_id: int,
    project_id: int | None,
) -> int | None:
    if project_id:
        r = await db.execute(
            select(ProspectiveProject.id).where(
                ProspectiveProject.id == project_id,
                ProspectiveProject.case_id == case_id,
            )
        )
        return r.scalar_one_or_none()
    r = await db.execute(
        select(ProspectiveProject.id)
        .where(ProspectiveProject.case_id == case_id)
        .order_by(ProspectiveProject.created_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()


async def load_company_registry(
    db: AsyncSession,
    case_id: int,
    *,
    project_id: int | None = None,
    premise: str | None = None,
) -> dict[str, Any]:
    from models.case import Case

    case_r = await db.execute(select(Case).where(Case.id == case_id))
    if not case_r.scalar_one_or_none():
        return {"case_id": case_id, "found": False}

    merged: dict[str, dict[str, Any]] = {}

    policy = await PolicyIndustryService(db).build_map(case_id, premise=premise)
    if policy.get("found"):
        for c in policy.get("companies") or []:
            _merge_registry(merged, _from_policy_company(c))

    pid = await _resolve_project_id(db, case_id, project_id)

    if pid:
        ar = await db.execute(select(ProspectiveActor).where(ProspectiveActor.project_id == pid))
        for pa in ar.scalars().all():
            if not looks_like_company(pa.name):
                continue
            goals = pa.strategic_goals if isinstance(pa.strategic_goals, list) else []
            goal_text = " ".join(str(g) for g in goals)
            created, note = _detect_creation_signal(goal_text)
            entry = _empty_entry(pa.name)
            entry["roles"] = ["strategic_actor"]
            entry["origins"] = ["godet_actor"]
            entry["linked_aspects"] = [
                {"type": "godet", "id": pid, "label": f"Actor Godet · projecte #{pid}"},
            ]
            entry["sources"] = [
                {
                    "origin": "godet_actor",
                    "excerpt": goal_text[:200] if goal_text else f"Força {pa.force_score}",
                    "field": "strategic_goals",
                }
            ]
            entry["beneficiary_rationale"] = (
                f"Actor estratègic al projecte Godet (força {pa.force_score})."
            )
            entry["creation_signal"] = created
            entry["creation_note"] = note
            if created:
                entry["roles"].append("market_opportunity")
            _merge_registry(merged, entry)

    inq_r = await db.execute(
        select(ProspectiveInquiry)
        .where(ProspectiveInquiry.case_id == case_id)
        .order_by(ProspectiveInquiry.created_at.desc())
        .limit(10)
    )
    for inq in inq_r.scalars().all():
        artifacts = inq.artifacts if isinstance(inq.artifacts, dict) else {}
        pi = artifacts.get("policy_industry") or {}
        if not isinstance(pi, dict):
            continue
        aspect = {"type": "inquiry", "id": inq.id, "label": f"Q2FS #{inq.id}"}
        for c in pi.get("companies") or []:
            if isinstance(c, dict) and c.get("name"):
                entry = _from_policy_company(c, aspect=aspect)
                if "inquiry" not in entry["origins"]:
                    entry["origins"].append("inquiry")
                _merge_registry(merged, entry)

    companies = sorted(merged.values(), key=lambda x: (x.get("region", ""), x.get("name", "")))
    domestic = [c for c in companies if c.get("region") == "domestic"]
    overseas = [c for c in companies if c.get("region") == "overseas"]
    with_creation = [c for c in companies if c.get("creation_signal")]

    return {
        "case_id": case_id,
        "project_id": pid,
        "found": True,
        "summary": {
            "total": len(companies),
            "domestic": len(domestic),
            "overseas": len(overseas),
            "with_creation_signal": len(with_creation),
            "from_policy_industry": sum(
                1 for c in companies if "policy_industry" in c.get("origins", [])
            ),
            "from_godet": sum(1 for c in companies if "godet_actor" in c.get("origins", [])),
            "from_inquiry": sum(1 for c in companies if "inquiry" in c.get("origins", [])),
        },
        "role_labels": _REGISTRY_ROLE_LABELS,
        "companies": companies,
        "by_region": {"domestic": domestic, "overseas": overseas},
        "creation_opportunities": with_creation,
    }
