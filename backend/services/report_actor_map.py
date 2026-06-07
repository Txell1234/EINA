"""Case-driven actor map for Godet / prospective reports."""
from __future__ import annotations

import re
from typing import Any

from services.actor_impact_utils import canonical_actor
from services.report_i18n import get_report_strings

# Geographic hint for map highlight only — labels never replace Godet actor names.
_REGIONS: dict[str, dict[str, Any]] = {
    "china": {
        "color": "#6B5B95",
        "paths": ["M 340,95 L 520,80 L 590,165 L 575,265 L 495,310 L 395,285 L 330,200 Z"],
        "bbox": (320, 75, 600, 320),
    },
    "north_east_asia": {
        "color": "#8B7EC8",
        "paths": [
            "M 595,175 L 640,160 L 655,210 L 630,245 L 600,230 Z",
            "M 565,255 L 590,248 L 598,275 L 572,282 Z",
        ],
        "bbox": (555, 150, 665, 290),
    },
    "south_asia": {
        "color": "#C0392B",
        "paths": ["M 420,310 L 510,295 L 540,380 L 500,460 L 430,445 L 395,370 Z"],
        "bbox": (385, 290, 545, 470),
    },
    "south_east_asia": {
        "color": "#E07A5F",
        "paths": ["M 500,380 L 590,360 L 620,430 L 575,490 L 510,470 L 485,420 Z"],
        "bbox": (475, 350, 625, 500),
    },
    "oceania": {
        "color": "#F4A261",
        "paths": ["M 560,500 L 720,485 L 760,560 L 680,590 L 550,575 Z"],
        "bbox": (540, 475, 770, 600),
    },
    "central_asia": {
        "color": "#9B59B6",
        "paths": ["M 280,180 L 340,165 L 360,240 L 310,280 L 260,230 Z"],
        "bbox": (250, 155, 370, 290),
    },
    "middle_east": {
        "color": "#D35400",
        "paths": ["M 200,260 L 290,245 L 310,320 L 240,350 L 180,310 Z"],
        "bbox": (170, 235, 320, 360),
    },
    "europe": {
        "color": "#3498DB",
        "paths": ["M 80,120 L 180,100 L 210,180 L 150,220 L 70,190 Z"],
        "bbox": (60, 90, 220, 230),
    },
    "americas": {
        "color": "#2C3E50",
        "paths": ["M 20,280 L 90,260 L 110,380 L 60,420 L 15,360 Z"],
        "bbox": (5, 250, 120, 430),
    },
}

_ACTOR_TO_REGION: list[tuple[tuple[str, ...], str]] = [
    (("china", "xina", "prc", "beijing", "pekin"), "china"),
    (("japan", "japó", "japon", "tokyo", "corea", "korea", "taiwan", "taipei", "seoul"), "north_east_asia"),
    (("india", "índia", "pakistan", "bangladesh", "nepal", "delhi", "modi"), "south_asia"),
    (("asean", "vietnam", "indonesia", "thailand", "philippines", "malaysia", "singapore", "sud-est"), "south_east_asia"),
    (("australia", "austràlia", "zealand", "pacific", "oceania", "oceanía"), "oceania"),
    (("russia", "rússia", "moscow", "moscou", "kazakh", "uzbek"), "central_asia"),
    (("iran", "saudi", "israel", "turkey", "turquia", "gulf", "middle east", "orient mitjà"), "middle_east"),
    (("europe", "europa", "european union", "unió europea", "ue", "eu", "germany", "france", "italy", "itàlia"), "europe"),
    (("united states", "estats units", "usa", "u.s.", "america", "washington", "eua"), "americas"),
]

_ACTOR_COLORS = ("#6B5B95", "#C0392B", "#E07A5F", "#3498DB", "#2C3E50", "#9B59B6", "#2E7D32", "#6366F1")


def _resolve_region(actor_name: str, impact_row: dict[str, Any] | None = None) -> str | None:
    for country in (impact_row or {}).get("countries") or []:
        rid = _resolve_region(str(country))
        if rid:
            return rid
    key = canonical_actor(actor_name).lower()
    raw = (actor_name or "").lower()
    for fragments, region_id in _ACTOR_TO_REGION:
        if any(f in key or f in raw for f in fragments):
            return region_id
    return None


def _truncate(text: str, limit: int = 220) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= limit:
        return t
    return t[: limit - 1] + "…"


def _claims_for_actor(name: str, claims: list[dict[str, Any]]) -> list[str]:
    key = canonical_actor(name).lower()
    raw = name.lower()
    out: list[str] = []
    for c in claims:
        claim = str(c.get("claim") or "")
        cl = claim.lower()
        actors = [canonical_actor(a).lower() for a in (c.get("actors") or [])]
        if key in cl or raw in cl or key in actors:
            out.append(_truncate(claim))
        if len(out) >= 3:
            break
    return out


def _impact_bullets(name: str, impact_matrix: list[dict[str, Any]]) -> list[str]:
    key = canonical_actor(name)
    rows = [r for r in impact_matrix if canonical_actor(r.get("actor", "")) == key]
    rows.sort(key=lambda r: (-abs(float(r.get("impact_score") or 0)), -int(r.get("confidence") or 0)))
    out: list[str] = []
    for row in rows[:2]:
        sc = row.get("scenario_name") or "—"
        label = row.get("impact_label") or ""
        score = row.get("impact_score")
        mech = _truncate(str(row.get("mechanism") or ""), 140)
        line = f"{sc}: {label}"
        if score is not None:
            line += f" ({score:+.1f})"
        if mech:
            line += f" — {mech}"
        out.append(line)
    return out


def _evidence_bullets(impact_row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for ev in (impact_row.get("top_evidence") or [])[:2]:
        excerpt = _truncate(str(ev.get("excerpt") or ""), 180)
        if excerpt:
            out.append(excerpt)
    return out


def _bullets_for_actor(actor: dict[str, Any], bundle: dict[str, Any], s: Any) -> list[str]:
    """Only case-specific bullets — Godet goals, OSINT, claims, impact matrix."""
    bullets: list[str] = []
    impact = bundle.get("actor_impact") or {}
    claims = impact.get("claims") or []
    matrix = impact.get("impact_matrix") or []

    for goal in actor.get("strategic_goals") or []:
        g = _truncate(str(goal))
        if g and g not in bullets:
            bullets.append(g)

    mot = _truncate(actor.get("motivation") or "")
    if mot and mot not in bullets:
        bullets.append(mot)

    for claim in _claims_for_actor(actor["name"], claims):
        if claim not in bullets:
            bullets.append(claim)

    for line in _impact_bullets(actor["name"], matrix):
        if line not in bullets:
            bullets.append(line)

    for line in _evidence_bullets(actor):
        if line not in bullets:
            bullets.append(line)

    if actor.get("posture_trend") == "deteriorating":
        bullets.append(s.actor_map_posture_worse)
    elif actor.get("posture_trend") == "improving":
        bullets.append(s.actor_map_posture_better)

    if actor.get("mactor_mobilisation") is not None:
        bullets.append(
            f"{s.actor_map_mactor}: {float(actor['mactor_mobilisation']):.2f}"
        )

    if actor.get("force_score") is not None and len(bullets) < 2:
        bullets.append(
            f"{s.actor_map_force}: {float(actor['force_score']):.1f}/7 (Godet MACTOR)"
        )

    return bullets[:5]


def _actor_meta(name: str, godet: dict[str, Any], impact: dict[str, Any]) -> dict[str, Any]:
    g = godet.get(canonical_actor(name), {})
    imp = impact.get(canonical_actor(name), {})
    display = g.get("name") or imp.get("name") or name
    return {
        "name": display,
        "code": g.get("code") or imp.get("code"),
        "force_score": g.get("force_score") if g.get("force_score") is not None else imp.get("force_score"),
        "strategic_goals": g.get("strategic_goals") or imp.get("strategic_goals") or [],
        "motivation": imp.get("motivation") or "",
        "posture_trend": imp.get("posture_trend"),
        "geo_risk_score": imp.get("geo_risk_score"),
        "topics": imp.get("topics") or [],
        "statement_count": imp.get("statement_count") or 0,
        "avg_posture": imp.get("avg_posture"),
        "mactor_mobilisation": imp.get("mactor_mobilisation"),
        "mactor_avg": imp.get("mactor_avg"),
        "top_evidence": imp.get("top_evidence") or [],
        "countries": imp.get("countries") or [],
        "sources": imp.get("sources") or [],
    }


def _collect_case_actors(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """All Godet actors for this project, enriched with OSINT impact when available."""
    godet: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for a in bundle.get("actors") or []:
        name = getattr(a, "name", None) or str(a.get("name", ""))
        key = canonical_actor(name)
        if not key:
            continue
        goals = getattr(a, "strategic_goals", None) or (a.get("strategic_goals") if isinstance(a, dict) else None) or []
        order_val = getattr(a, "order_index", None)
        if order_val is None and isinstance(a, dict):
            order_val = a.get("order_index")
        godet[key] = {
            "name": name,
            "code": getattr(a, "code", None) or (a.get("code") if isinstance(a, dict) else None),
            "force_score": float(getattr(a, "force_score", None) or (a.get("force_score") if isinstance(a, dict) else None) or 3),
            "strategic_goals": goals if isinstance(goals, list) else [],
            "order": order_val if order_val is not None else len(order),
        }
        order.append(key)

    impact_by_name: dict[str, dict[str, Any]] = {}
    for row in (bundle.get("actor_impact") or {}).get("actors") or []:
        key = canonical_actor(row.get("name", ""))
        if key:
            impact_by_name[key] = row

    keys: list[str] = list(order)
    for key in impact_by_name:
        if key not in keys:
            keys.append(key)

    def sort_key(key: str) -> tuple[float, int]:
        g = godet.get(key, {})
        imp = impact_by_name.get(key, {})
        return (
            -(
                float(g.get("force_score") or 0) * 12
                + int(imp.get("statement_count") or 0) * 2
                + (float(imp.get("geo_risk_score") or 0) / 10.0)
            ),
            g.get("order", 99),
        )

    keys.sort(key=sort_key)
    return [_actor_meta(k, godet, impact_by_name) for k in keys]


def _viewbox(active_region_ids: list[str]) -> str:
    if not active_region_ids:
        return "0 0 900 650"
    x0, y0, x1, y1 = 900, 650, 0, 0
    for rid in active_region_ids:
        meta = _REGIONS.get(rid)
        if not meta:
            continue
        bx, by, bx2, by2 = meta["bbox"]
        x0, y0, x1, y1 = min(x0, bx), min(y0, by), max(x1, bx2), max(y1, by2)
    pad = 40
    w = max(x1 - x0 + 2 * pad, 120)
    h = max(y1 - y0 + 2 * pad, 120)
    return f"{x0 - pad} {y0 - pad} {w} {h}"


def _case_focus(bundle: dict[str, Any]) -> str:
    project = bundle.get("project")
    if not project:
        return ""
    for attr in ("hypothesis", "context", "title"):
        text = _truncate(str(getattr(project, attr, None) or ""), 200)
        if text:
            return text
    return ""


def build_actor_map_sections(bundle: dict[str, Any]) -> dict[str, Any]:
    """Map + cards built only from this case's Godet actors and OSINT impact."""
    lang = bundle.get("lang") or "ca"
    s = get_report_strings(lang)
    actors = _collect_case_actors(bundle)
    if not actors:
        return {"has_data": False, "callouts": [], "regions": [], "active_region_ids": []}

    callouts: list[dict[str, Any]] = []
    active_regions: set[str] = set()

    for i, actor in enumerate(actors):
        impact_row = {
            "countries": actor.get("countries"),
            "top_evidence": actor.get("top_evidence"),
        }
        region_id = _resolve_region(actor["name"], impact_row)
        bullets = _bullets_for_actor(actor, bundle, s)
        if not bullets:
            bullets = [s.actor_map_no_detail.replace("{name}", actor["name"])]

        if region_id:
            active_regions.add(region_id)
            color = _REGIONS[region_id]["color"]
        else:
            color = _ACTOR_COLORS[i % len(_ACTOR_COLORS)]

        meta_bits: list[str] = []
        if actor.get("code"):
            meta_bits.append(str(actor["code"]))
        if actor.get("statement_count"):
            meta_bits.append(f"{actor['statement_count']} {s.actor_map_statements}")
        if actor.get("geo_risk_score") is not None:
            meta_bits.append(f"{s.actor_map_geo_risk} {int(float(actor['geo_risk_score']))}/100")

        callouts.append(
            {
                "actor_name": actor["name"],
                "region_id": region_id,
                "color": color,
                "bullets": bullets,
                "meta": " · ".join(meta_bits),
            }
        )

    regions_out = []
    for rid in sorted(active_regions):
        meta = _REGIONS[rid]
        regions_out.append(
            {
                "id": rid,
                "color": meta["color"],
                "paths": meta["paths"],
                "active": True,
            }
        )

    return {
        "has_data": bool(callouts),
        "case_focus": _case_focus(bundle),
        "callouts": callouts,
        "regions": regions_out,
        "active_region_ids": sorted(active_regions),
        "viewbox": _viewbox(sorted(active_regions)),
        "mapless_count": sum(1 for c in callouts if not c.get("region_id")),
    }
