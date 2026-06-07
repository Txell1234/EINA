"""Multi-inquiry executive report — aggregated HTML/PDF with comparative synthesis."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.inquiry_compare_service import build_case_inquiry_comparison
from services.inquiry_export_service import prepare_inquiry_for_export
from services.inquiry_orchestrator_service import InquiryOrchestratorService
from services.report_i18n import get_report_strings, normalize_lang
from services.report_layout import build_report_footer, svg_mini_bar_chart
from services.report_templates import get_report_css, normalize_template

_MULTI_STRINGS: dict[str, dict[str, str]] = {
    "ca": {
        "title": "Informe executiu multi-inquiry",
        "portfolio": "Portfolio d'anàlisi Q2FS",
        "comparative": "Síntesi comparativa",
        "inquiry_count": "Inquiries",
        "completed_count": "Completades",
        "avg_prob": "Probabilitat mitjana",
        "prob_range": "Rang prob.",
        "status_mix": "Estats",
        "table_id": "ID",
        "table_question": "Pregunta",
        "table_prob": "Prob.",
        "table_possibility": "Possibilitat",
        "table_delta": "Δ vs ant.",
        "table_status": "Estat",
        "per_inquiry": "Detall per inquiry",
        "cross_cutting": "Temes transversals",
        "cross_monitors": "Monitors recurrents",
        "cross_conclusions": "Conclusions compartides",
        "selection_note": "Selecció manual d'inquiries",
        "case_note": "Totes les inquiries del cas",
        "trace_note": "Síntesi determinista sense inferència LLM addicional; traçabilitat via audit trail.",
    },
    "es": {
        "title": "Informe ejecutivo multi-inquiry",
        "portfolio": "Portfolio de análisis Q2FS",
        "comparative": "Síntesis comparativa",
        "inquiry_count": "Inquiries",
        "completed_count": "Completadas",
        "avg_prob": "Probabilidad media",
        "prob_range": "Rango prob.",
        "status_mix": "Estados",
        "table_id": "ID",
        "table_question": "Pregunta",
        "table_prob": "Prob.",
        "table_possibility": "Posibilidad",
        "table_delta": "Δ vs ant.",
        "table_status": "Estado",
        "per_inquiry": "Detalle por inquiry",
        "cross_cutting": "Temas transversales",
        "cross_monitors": "Monitores recurrentes",
        "cross_conclusions": "Conclusiones compartidas",
        "selection_note": "Selección manual de inquiries",
        "case_note": "Todas las inquiries del caso",
        "trace_note": "Síntesis determinista sin inferencia LLM adicional; trazabilidad vía audit trail.",
    },
    "en": {
        "title": "Multi-inquiry executive report",
        "portfolio": "Q2FS analysis portfolio",
        "comparative": "Comparative synthesis",
        "inquiry_count": "Inquiries",
        "completed_count": "Completed",
        "avg_prob": "Average probability",
        "prob_range": "Prob. range",
        "status_mix": "Statuses",
        "table_id": "ID",
        "table_question": "Question",
        "table_prob": "Prob.",
        "table_possibility": "Possibility",
        "table_delta": "Δ vs prev.",
        "table_status": "Status",
        "per_inquiry": "Per-inquiry detail",
        "cross_cutting": "Cross-cutting themes",
        "cross_monitors": "Recurring monitors",
        "cross_conclusions": "Shared conclusions",
        "selection_note": "Manual inquiry selection",
        "case_note": "All case inquiries",
        "trace_note": "Deterministic synthesis without additional LLM inference; audit trail traceability.",
    },
}


def _esc(s: Any) -> str:
    import html

    return html.escape(str(s) if s is not None else "")


def _multi_strings(lang: str) -> dict[str, str]:
    code = normalize_lang(lang)
    return _MULTI_STRINGS.get(code, _MULTI_STRINGS["ca"])


def _portfolio_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    probs = [float(i["probability_pct"]) for i in items if i.get("probability_pct") is not None]
    statuses: dict[str, int] = {}
    for item in items:
        st = str(item.get("status") or "unknown")
        statuses[st] = statuses.get(st, 0) + 1
    completed = statuses.get("completed", 0)
    return {
        "count": len(items),
        "completed": completed,
        "avg_probability": round(sum(probs) / len(probs), 1) if probs else None,
        "min_probability": min(probs) if probs else None,
        "max_probability": max(probs) if probs else None,
        "statuses": statuses,
    }


def _cross_cutting_themes(details: list[dict[str, Any]]) -> dict[str, list[str]]:
    monitor_counts: dict[str, int] = {}
    conclusion_counts: dict[str, int] = {}
    for detail in details:
        monitors = (detail.get("artifacts") or {}).get("monitor_suggestions") or {}
        for m in monitors.get("suggested_monitors") or []:
            if isinstance(m, dict) and m.get("indicator"):
                key = str(m["indicator"]).strip()
                monitor_counts[key] = monitor_counts.get(key, 0) + 1
        answer = detail.get("answer") or {}
        for c in answer.get("conclusions") or []:
            text = str(c).strip()
            if text:
                conclusion_counts[text] = conclusion_counts.get(text, 0) + 1
    recurring_monitors = sorted(
        [k for k, v in monitor_counts.items() if v >= 2],
        key=lambda k: monitor_counts[k],
        reverse=True,
    )[:8]
    shared_conclusions = sorted(
        [k for k, v in conclusion_counts.items() if v >= 2],
        key=lambda k: conclusion_counts[k],
        reverse=True,
    )[:6]
    return {
        "monitors": recurring_monitors,
        "conclusions": shared_conclusions,
    }


def build_multi_inquiry_executive_html(
    bundle: dict[str, Any],
    *,
    lang: str | None = None,
    template: str | None = None,
) -> str:
    """Styled HTML executive brief for multiple inquiries."""
    lang_code = normalize_lang(lang or bundle.get("lang"))
    s = get_report_strings(lang_code)
    ms = _multi_strings(lang_code)
    tpl = normalize_template(template or bundle.get("template"))
    case_name = bundle.get("case_name") or ms["portfolio"]
    scope_note = bundle.get("scope_note") or ms["selection_note"]
    comparison = bundle.get("comparison") or {}
    items = comparison.get("items") or []
    stats = bundle.get("stats") or _portfolio_stats(items)
    themes = bundle.get("cross_cutting") or {}
    details = bundle.get("details") or []
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    prob_chart = ""
    series = comparison.get("probability_series") or []
    if len(series) >= 2:
        chart_vals = [(f"#{p['id']}", float(p["probability_pct"])) for p in series if p.get("probability_pct") is not None]
        prob_chart = svg_mini_bar_chart(chart_vals)

    parts = [
        f"<!DOCTYPE html><html lang='{lang_code}'><head><meta charset='utf-8'>",
        f"<title>{_esc(ms['title'])} — {_esc(case_name)}</title>",
        f"<style>{get_report_css(tpl, report_type='inquiry')}</style></head><body>",
        "<section class='cover-page executive-cover'>",
        f"<h1 class='cover-title'>{_esc(ms['title'])}</h1>",
        f"<p class='cover-sub'>{_esc(case_name)}</p>",
        f"<p class='muted'>{_esc(scope_note)} · {_esc(s.generated)} {generated}</p>",
        "</section>",
        f"<section class='executive-summary report-section'><h2>{_esc(ms['comparative'])}</h2>",
        "<div class='kpi-row'>",
        f"<div class='kpi'><span class='kpi-label'>{_esc(ms['inquiry_count'])}</span>"
        f"<span class='kpi-value'>{stats.get('count', 0)}</span></div>",
        f"<div class='kpi'><span class='kpi-label'>{_esc(ms['completed_count'])}</span>"
        f"<span class='kpi-value'>{stats.get('completed', 0)}</span></div>",
    ]
    if stats.get("avg_probability") is not None:
        parts.append(
            f"<div class='kpi'><span class='kpi-label'>{_esc(ms['avg_prob'])}</span>"
            f"<span class='kpi-value'>{stats['avg_probability']}%</span></div>"
        )
    if stats.get("min_probability") is not None and stats.get("max_probability") is not None:
        parts.append(
            f"<div class='kpi'><span class='kpi-label'>{_esc(ms['prob_range'])}</span>"
            f"<span class='kpi-value'>{stats['min_probability']}% – {stats['max_probability']}%</span></div>"
        )
    parts.append("</div>")

    status_mix = stats.get("statuses") or {}
    if status_mix:
        parts.append(f"<p><strong>{_esc(ms['status_mix'])}:</strong> ")
        parts.append(", ".join(f"{_esc(k)} ({v})" for k, v in sorted(status_mix.items())))
        parts.append("</p>")

    if prob_chart:
        parts.append(f"<div class='chart-block'>{prob_chart}</div>")

    parts.append("<table class='data-table'><thead><tr>")
    for col in ("table_id", "table_question", "table_prob", "table_possibility", "table_delta", "table_status"):
        parts.append(f"<th>{_esc(ms[col])}</th>")
    parts.append("</tr></thead><tbody>")
    for item in items:
        diff = item.get("diff_vs_previous") or {}
        delta = diff.get("probability_delta")
        delta_str = f"{delta:+.1f}" if isinstance(delta, (int, float)) else "—"
        parts.append("<tr>")
        parts.append(f"<td>#{_esc(item.get('id'))}</td>")
        parts.append(f"<td>{_esc(item.get('question'))}</td>")
        prob = item.get("probability_pct")
        parts.append(f"<td>{_esc(prob)}%</td>" if prob is not None else "<td>—</td>")
        parts.append(f"<td>{_esc(item.get('possibility') or '—')}</td>")
        parts.append(f"<td>{_esc(delta_str)}</td>")
        parts.append(f"<td>{_esc(item.get('status'))}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></section>")

    if themes.get("monitors") or themes.get("conclusions"):
        parts.append(f"<section class='report-section'><h2>{_esc(ms['cross_cutting'])}</h2>")
        if themes.get("monitors"):
            parts.append(f"<p><strong>{_esc(ms['cross_monitors'])}:</strong></p><ul>")
            for m in themes["monitors"]:
                parts.append(f"<li>{_esc(m)}</li>")
            parts.append("</ul>")
        if themes.get("conclusions"):
            parts.append(f"<p><strong>{_esc(ms['cross_conclusions'])}:</strong></p><ul>")
            for c in themes["conclusions"]:
                parts.append(f"<li>{_esc(c)}</li>")
            parts.append("</ul>")
        parts.append("</section>")

    parts.append(f"<section class='report-section'><h2>{_esc(ms['per_inquiry'])}</h2>")
    for detail in details:
        answer = detail.get("answer") or {}
        q = detail.get("question") or ""
        parts.append("<article class='inquiry-card' style='margin:1em 0;padding:1em;border:1px solid #ddd;border-radius:8px'>")
        parts.append(f"<h3>Inquiry #{_esc(detail.get('id'))} · {_esc(detail.get('status'))}</h3>")
        parts.append(f"<p><strong>{_esc(s.es_hypothesis)}:</strong> {_esc(q[:240])}</p>")
        if answer:
            parts.append(
                f"<p><strong>{_esc(s.probability)}:</strong> {_esc(answer.get('probability_pct'))}% · "
                f"<strong>{_esc(s.possibility)}:</strong> {_esc(answer.get('possibility'))}</p>"
            )
        conclusions = answer.get("conclusions") or []
        if conclusions:
            parts.append(f"<p><strong>{_esc(s.es_conclusions)}:</strong></p><ul>")
            for c in conclusions[:4]:
                parts.append(f"<li>{_esc(c)}</li>")
            parts.append("</ul>")
        parts.append("</article>")
    parts.append("</section>")

    parts.append(f"<p class='muted'><strong>{_esc(s.es_limitations)}:</strong> {_esc(ms['trace_note'])}</p>")
    parts.append(
        build_report_footer(
            tpl,
            generated_note="EINA Q2FS — informe executiu multi-inquiry",
        )
    )
    parts.append("</body></html>")
    return "\n".join(parts)


async def build_executive_report_bundle(
    db: AsyncSession,
    *,
    inquiry_ids: list[int] | None = None,
    case_id: int | None = None,
    lang: str | None = None,
    template: str | None = None,
    max_inquiries: int = 25,
) -> dict[str, Any]:
    if not inquiry_ids and case_id is None:
        raise ValueError("Cal case_id o llista d'IDs")
    orchestrator = InquiryOrchestratorService(db)
    ms = _multi_strings(lang or "ca")

    rows_for_compare: list[Any] = []
    comparison: dict[str, Any]
    resolved_case_id = case_id
    case_name = ms["portfolio"]

    if case_id is not None:
        from models.prospective_inquiry import ProspectiveInquiry
        from models.case import Case
        from sqlalchemy import select

        case_row = await db.execute(select(Case).where(Case.id == case_id))
        case = case_row.scalar_one_or_none()
        if not case:
            raise ValueError("Cas no trobat")
        case_name = case.name or f"Cas #{case_id}"
        result = await orchestrator.compare_for_case(case_id, inquiry_ids=inquiry_ids)
        comparison = {k: v for k, v in result.items() if k != "found"}
        if inquiry_ids:
            q = select(ProspectiveInquiry).where(ProspectiveInquiry.id.in_(inquiry_ids))
        else:
            q = select(ProspectiveInquiry).where(ProspectiveInquiry.case_id == case_id)
        rows_for_compare = list((await db.execute(q)).scalars().all())
        scope_note = ms["case_note"] if not inquiry_ids else ms["selection_note"]
    else:
        assert inquiry_ids
        if len(inquiry_ids) > max_inquiries:
            raise ValueError(f"Màxim {max_inquiries} inquiries per informe executiu")
        from models.prospective_inquiry import ProspectiveInquiry
        from models.case import Case
        from sqlalchemy import select

        q = select(ProspectiveInquiry).where(ProspectiveInquiry.id.in_(inquiry_ids))
        rows_for_compare = list((await db.execute(q)).scalars().all())
        if not rows_for_compare:
            raise ValueError("Cap inquiry trobada")
        case_ids = {r.case_id for r in rows_for_compare}
        if len(case_ids) == 1:
            resolved_case_id = next(iter(case_ids))
            case_row = await db.execute(select(Case).where(Case.id == resolved_case_id))
            case = case_row.scalar_one_or_none()
            if case:
                case_name = case.name or case_name
            comparison = build_case_inquiry_comparison(rows_for_compare)
        else:
            comparison = build_case_inquiry_comparison(
                sorted(rows_for_compare, key=lambda r: (r.case_id, r.created_at or datetime.min.replace(tzinfo=timezone.utc)))
            )
            case_name = f"{ms['portfolio']} ({len(case_ids)} casos)"
        scope_note = ms["selection_note"]

    ordered_ids = [item["id"] for item in comparison.get("items") or []]
    if not ordered_ids:
        ordered_ids = [r.id for r in rows_for_compare]
    if len(ordered_ids) > max_inquiries:
        raise ValueError(f"Màxim {max_inquiries} inquiries per informe executiu")

    details: list[dict[str, Any]] = []
    for iid in ordered_ids:
        detail = await orchestrator.get_detail(iid)
        if not detail.get("found"):
            continue
        enriched = await prepare_inquiry_for_export(db, detail, lang=lang)
        details.append(enriched)

    if not details:
        raise ValueError("Cap inquiry vàlida per exportar")

    items = comparison.get("items") or []
    return {
        "lang": normalize_lang(lang),
        "template": normalize_template(template),
        "case_id": resolved_case_id,
        "case_name": case_name,
        "scope_note": scope_note,
        "comparison": comparison,
        "stats": _portfolio_stats(items),
        "cross_cutting": _cross_cutting_themes(details),
        "details": details,
    }


async def build_executive_report_html(
    db: AsyncSession,
    *,
    inquiry_ids: list[int] | None = None,
    case_id: int | None = None,
    lang: str | None = None,
    template: str | None = None,
) -> str:
    bundle = await build_executive_report_bundle(
        db,
        inquiry_ids=inquiry_ids,
        case_id=case_id,
        lang=lang,
        template=template,
    )
    return build_multi_inquiry_executive_html(bundle, lang=lang, template=template)
