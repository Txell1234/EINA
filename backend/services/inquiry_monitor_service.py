"""Suggested OSINT monitors and milestones from a prospective inquiry (deterministic)."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import AlertMonitor, ProspectiveProject


def _keywords(text: str, limit: int = 6) -> list[str]:
    tokens = re.findall(r"[A-Za-zÀ-ÿ]{4,}", text.lower())
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= limit:
            break
    return out


class InquiryMonitorService:
    """Build monitor/milestone suggestions — does not auto-activate unless applied."""

    def suggest(
        self,
        *,
        question: str,
        parsed_trigger: dict[str, Any] | None = None,
        morph_bootstrap: dict[str, Any] | None = None,
        horizon_label: str = "",
    ) -> dict[str, Any]:
        parsed = parsed_trigger or {}
        terms = list(parsed.get("required_terms") or [])[:5]
        actors = list(parsed.get("actors") or [])[:4]
        horizon = horizon_label or parsed.get("horizon_label") or ""

        indicators: list[dict[str, Any]] = []

        if terms:
            indicators.append(
                {
                    "indicator": f"Declaració oficial vinculada a: {', '.join(terms[:3])}",
                    "keywords": _keywords(" ".join(terms + actors)),
                    "horizon_label": horizon or None,
                    "source": "inquiry_required_terms",
                }
            )

        for actor in actors[:2]:
            indicators.append(
                {
                    "indicator": f"Moviment o declaració de {actor} sobre la hipòtesi de la pregunta",
                    "keywords": _keywords(f"{actor} {' '.join(terms[:2])}"),
                    "horizon_label": horizon or None,
                    "source": "inquiry_actor",
                }
            )

        morph = morph_bootstrap or {}
        for row in morph.get("godet_preview") or []:
            name = str(row.get("name") or "")
            config = str(row.get("config") or "")
            if not name:
                continue
            indicators.append(
                {
                    "indicator": f"Senyal OSINT compatible amb escenari «{name}» ({config})",
                    "keywords": _keywords(f"{name} {config} {' '.join(terms[:2])}"),
                    "horizon_label": horizon or None,
                    "source": "morph_godet_preview",
                    "scenario_hint": name,
                }
            )

        if len(indicators) < 2:
            indicators.append(
                {
                    "indicator": f"Esdeveniment que confirmi o refuti: {question[:120]}",
                    "keywords": _keywords(question),
                    "horizon_label": horizon or None,
                    "source": "inquiry_question",
                }
            )

        milestones = []
        for i, ind in enumerate(indicators[:4]):
            milestones.append(
                {
                    "order_index": i,
                    "title": ind["indicator"][:200],
                    "trigger_indicator": ind["indicator"],
                    "horizon_label": ind.get("horizon_label"),
                    "reversibility": "medium",
                    "source": ind.get("source"),
                }
            )

        return {
            "methodology": "deterministic_monitor_suggestions",
            "llm_used": False,
            "suggested_monitors": indicators[:6],
            "suggested_milestones": milestones,
            "count": len(indicators[:6]),
        }

    async def apply_to_project(
        self,
        db: AsyncSession,
        *,
        case_id: int,
        project_id: int,
        suggestions: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist suggested monitors on an existing project (additive, inactive by default)."""
        r = await db.execute(
            select(ProspectiveProject).where(
                ProspectiveProject.id == project_id,
                ProspectiveProject.case_id == case_id,
            )
        )
        project = r.scalar_one_or_none()
        if not project:
            return {"ok": False, "error": "Projecte no trobat per aquest cas"}

        created = []
        for ind in suggestions.get("suggested_monitors") or []:
            kws = ind.get("keywords") or _keywords(ind.get("indicator", ""))
            db.add(
                AlertMonitor(
                    project_id=project_id,
                    case_id=case_id,
                    indicator=str(ind.get("indicator", ""))[:500],
                    keywords=kws,
                    osint_sources=["gdelt", "google_news"],
                    is_active=0,
                    horizon_label=ind.get("horizon_label"),
                )
            )
            created.append({"indicator": ind.get("indicator"), "keywords": kws, "is_active": 0})

        await db.commit()
        return {"ok": True, "project_id": project_id, "monitors_created": len(created), "monitors": created}
