"""EIU-style outlook sections for Godet / prospective analytical reports."""
from __future__ import annotations

import re
from typing import Any

from services.report_i18n import get_report_strings


def _parse_probability_pct(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return max(0, min(100, int(round(float(raw)))))
    text = str(raw)
    m = re.search(r"(\d{1,3})\s*%?", text)
    if m:
        return max(0, min(100, int(m.group(1))))
    return None


def build_outlook_sections(bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Build «What to watch / Key risks / Key opportunities / Scenarios» blocks
    inspired by EIU regional outlook reports (e.g. Asia outlook 2026).
    """
    s = get_report_strings(bundle.get("lang"))
    project = bundle["project"]
    impact = bundle.get("actor_impact") or {}
    inv = bundle.get("investment") or {}
    scenarios = bundle.get("scenarios") or []
    profiles = bundle.get("variable_profiles") or []
    summary_impact = impact.get("summary") or {}
    exec_summary = bundle.get("executive_summary") or {}

    theme = (project.hypothesis or project.title or "").strip()
    if len(theme) > 160:
        theme = theme[:157] + "…"

    what_to_watch: list[str] = []
    if summary_impact.get("most_likely_scenario"):
        what_to_watch.append(
            f"{s.outlook_dominant_scenario}: {summary_impact['most_likely_scenario']}"
        )
    ranked = sorted(
        profiles,
        key=lambda p: float(p.get("motricity") or 0),
        reverse=True,
    )
    for p in ranked[:3]:
        line = f"{p.get('name')} ({p.get('code')})"
        if p.get("motricity") is not None:
            line += f" — {s.outlook_motricity} {p['motricity']}"
        if p.get("motivation"):
            line += f". {str(p['motivation'])[:140]}"
        what_to_watch.append(line)
    for claim in (impact.get("claims") or [])[:2]:
        text = (claim.get("claim") or "").strip()
        if text and text not in what_to_watch:
            what_to_watch.append(text[:220])
    if not what_to_watch and project.context:
        what_to_watch.append(str(project.context)[:280])
    if not what_to_watch:
        what_to_watch = [s.no_data]

    key_risks: list[str] = []
    for risk in (inv.get("risks") or [])[:4]:
        desc = (risk.get("description") or "").strip()
        key_risks.append(
            f"{risk.get('risk_type', s.outlook_risk)} ({risk.get('risk_level', '—')}): {desc[:240]}"
        )
    for p in ranked:
        sec = str(p.get("sector") or "").lower()
        dep = p.get("dependence")
        if dep is not None and float(dep) >= 0.55:
            key_risks.append(
                f"{p.get('name')}: {s.outlook_high_dependence} ({dep}). "
                f"{str(p.get('motivation') or '')[:120]}"
            )
        if len(key_risks) >= 5:
            break
    for claim in (impact.get("claims") or []):
        c = (claim.get("claim") or "").lower()
        if any(w in c for w in ("risc", "risk", "tensió", "tension", "conflicte", "conflict")):
            key_risks.append(str(claim.get("claim"))[:240])
        if len(key_risks) >= 6:
            break
    if not key_risks:
        key_risks = [
            f"{s.outlook_risk_default} "
            f"({summary_impact.get('overall_confidence', '—')}% {s.outlook_confidence})."
        ]

    key_opportunities: list[str] = []
    for opp in (inv.get("opportunities") or [])[:4]:
        key_opportunities.append(
            f"{opp.get('title', s.outlook_opportunity)}: {(opp.get('description') or '')[:220]}"
        )
    for rec in (inv.get("recommendations") or [])[:3]:
        key_opportunities.append(
            f"{rec.get('type', 'HOLD')}: {(rec.get('rationale') or '')[:200]}"
        )
    for sc in scenarios:
        poss = str(getattr(sc, "possibility", "") or "").upper()
        if poss in ("PLAUSIBLE", "VERY_PLAUSIBLE", "CERTAIN"):
            key_opportunities.append(
                f"{s.outlook_scenario_window} {sc.name} ({poss}). "
                f"{(getattr(sc, 'possibility_rationale', None) or '')[:160]}"
            )
        if len(key_opportunities) >= 5:
            break
    if not key_opportunities:
        key_opportunities = [project.hypothesis or s.no_data]

    scenario_rows: list[dict[str, Any]] = []
    for sc in scenarios[:8]:
        pct = _parse_probability_pct(getattr(sc, "probability", None))
        scenario_rows.append(
            {
                "name": sc.name,
                "type": sc.scenario_type or "—",
                "possibility": getattr(sc, "possibility", None) or "PLAUSIBLE",
                "likelihood_pct": pct,
                "likelihood_label": f"{pct}%" if pct is not None else str(sc.probability or "—"),
                "excerpt": (sc.narrative or getattr(sc, "possibility_rationale", None) or "")[:320],
            }
        )

    smic = bundle.get("smic") or {}
    if not scenario_rows and smic.get("initial_probs"):
        probs = smic["initial_probs"]
        if isinstance(probs, dict):
            for name, val in list(probs.items())[:6]:
                pct = _parse_probability_pct(float(val) * 100 if float(val) <= 1 else val)
                scenario_rows.append(
                    {
                        "name": str(name),
                        "type": "SMIC",
                        "possibility": "PLAUSIBLE",
                        "likelihood_pct": pct,
                        "likelihood_label": f"{pct}%" if pct is not None else "—",
                        "excerpt": "",
                    }
                )

    toc = []
    has_actors = bool(bundle.get("actors")) or bool((bundle.get("actor_impact") or {}).get("actors"))
    if has_actors:
        toc.append({"id": "actor-map", "label": s.actor_map_title})
    toc.extend([
        {"id": "what-to-watch", "label": s.outlook_what_to_watch},
        {"id": "key-risks", "label": s.outlook_key_risks},
        {"id": "key-opportunities", "label": s.outlook_key_opportunities},
    ])
    if scenario_rows:
        toc.append({"id": "scenarios-outlook", "label": s.outlook_scenarios})

    return {
        "theme_subtitle": theme,
        "what_to_watch": what_to_watch[:5],
        "key_risks": key_risks[:6],
        "key_opportunities": key_opportunities[:6],
        "scenarios": scenario_rows,
        "toc": toc,
        "executive_sections": exec_summary.get("sections") or [],
    }


def parse_macro_outlook_text(text: str) -> dict[str, Any] | None:
    """
    Extract EIU-style macro outlook structure (e.g. Asia outlook 2026).
    Used for reference imports and future briefing enrichment — not financial parse.
    """
    if not text or len(text) < 200:
        return None
    low = text.lower()
    if "what to watch" not in low and "key risks" not in low:
        return None

    title_m = re.search(
        r"^([A-Za-z][^\n]{8,80})\s*\n(?:[^\n]{0,40}\n)?(?:Trade|Policy|Outlook)",
        text[:1200],
        re.M | re.I,
    )
    title = title_m.group(1).strip() if title_m else None
    if not title:
        m2 = re.search(r"(Asia outlook \d{4}|Outlook \d{4}[^\n]*)", text[:800], re.I)
        title = m2.group(1).strip() if m2 else "Macro outlook"

    def _section(name: str) -> list[str]:
        idx = re.search(rf"^{re.escape(name)}\s*$", text, re.I | re.M)
        if not idx:
            idx = re.search(rf"\b{re.escape(name)}\b", text, re.I)
            if not idx:
                return []
            start = idx.end()
        else:
            start = idx.end()
        rest = text[start:]
        end_m = re.search(
            r"\n(?:Key risks|Key opportunities|What to watch|Asia outlook|Country Analysis|\d+\s*\n)",
            rest,
            re.I,
        )
        block = rest[: end_m.start()] if end_m else rest[:3500]
        bullets = []
        for line in block.splitlines():
            line = line.strip().lstrip("•·▪-*").strip()
            if len(line) > 35 and not line.startswith("Source:"):
                bullets.append(line[:320])
        if not bullets:
            paras = [p.strip() for p in re.split(r"\n\s*\n", block) if len(p.strip()) > 50]
            bullets = [p[:320] for p in paras[:4]]
        return bullets[:6]

    scenarios: list[dict[str, Any]] = []
    for m in re.finditer(
        r"([^\n(]{4,80})\s*\(likelihood:\s*(\d{1,3})\s*%\)",
        text,
        re.I,
    ):
        scenarios.append(
            {
                "name": m.group(1).strip(),
                "likelihood_pct": int(m.group(2)),
                "likelihood_label": f"{m.group(2)}%",
            }
        )

    return {
        "parse_mode": "macro_outlook",
        "title": title,
        "what_to_watch": _section("What to watch in 2026") or _section("What to watch"),
        "key_risks": _section("Key risks"),
        "key_opportunities": _section("Key opportunities"),
        "scenarios": scenarios[:8],
    }
