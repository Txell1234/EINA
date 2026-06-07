"""Structured InvestWatch-style report view for EINA UI (PRAAMS PDF + paste + crossover)."""
from __future__ import annotations

from typing import Any

from services.financial_document_service import _bullet_score, _verdict_score, is_valid_company_name

RETURN_SECTOR_ORDER = (
    "Valuation",
    "Performance",
    "Analyst view",
    "Profitability",
    "Growth",
    "Dividends",
)
RISK_SECTOR_ORDER = (
    "Default risk",
    "Volatility",
    "Stress-test",
    "Selling difficulty",
    "Country",
    "ESG",
)

_REC_CLASS = {
    "BUY": "positive",
    "HOLD": "neutral",
    "SELL": "negative",
    "REDUCE_OR_HOLD": "caution",
    "MONITOR": "caution",
}


def _score_band(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 5.5:
        return "strong"
    if score >= 4.0:
        return "mid"
    if score >= 2.5:
        return "weak"
    return "low"


def _sector_cell(label: str, *, verdict: str | None = None, score: float | None = None, summary: str | None = None) -> dict[str, Any]:
    resolved_score = score
    if resolved_score is None and verdict:
        resolved_score = _verdict_score(verdict)
    if resolved_score is None and summary:
        resolved_score = _bullet_score(summary)
    return {
        "label": label,
        "verdict": verdict or summary or "—",
        "score": round(resolved_score, 1) if resolved_score is not None else None,
        "band": _score_band(resolved_score),
        "scale": "1-7",
    }


def _match_factor_label(label: str, candidates: tuple[str, ...]) -> str | None:
    low = label.lower()
    for c in candidates:
        if c.lower() in low or low in c.lower():
            return c
    return None


def _sectors_from_scores(
    factors: list[dict[str, Any]],
    order: tuple[str, ...],
    *,
    kind: str,
) -> list[dict[str, Any]]:
    by_label: dict[str, dict[str, Any]] = {}
    for f in factors:
        raw = (f.get("label") or "").strip()
        if not raw:
            continue
        key = _match_factor_label(raw, order) or raw
        by_label[key.lower()] = _sector_cell(
            key,
            score=float(f["score"]) if f.get("score") is not None else None,
            summary=raw if f.get("score") is None else None,
        )
    out: list[dict[str, Any]] = []
    for label in order:
        cell = by_label.get(label.lower())
        if cell:
            cell = {**cell, "kind": kind}
            out.append(cell)
    for key, cell in by_label.items():
        if not any(c["label"].lower() == key for c in out):
            out.append({**cell, "kind": kind})
    return out[:6]


def _praams_sectors(metrics: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    verdicts = metrics.get("factor_verdicts") or {}
    risk_summaries = metrics.get("key_risk_summaries") or []
    return_summaries = metrics.get("key_return_summaries") or []

    risk: list[dict[str, Any]] = []
    for i, label in enumerate(RISK_SECTOR_ORDER):
        verdict = verdicts.get(label) or verdicts.get("Country risk" if label == "Country" else "")
        summary = risk_summaries[i] if i < len(risk_summaries) else None
        if verdict or summary:
            risk.append(_sector_cell(label, verdict=verdict, summary=summary))

    ret: list[dict[str, Any]] = []
    for i, label in enumerate(RETURN_SECTOR_ORDER):
        verdict = verdicts.get(label)
        summary = return_summaries[i] if i < len(return_summaries) else None
        if verdict or summary:
            ret.append(_sector_cell(label, verdict=verdict, summary=summary))

    return risk, ret


def _key_metrics_display(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for km in (metrics.get("key_metrics") or [])[:8]:
        kind = km.get("metric_kind") or "other"
        rows.append(
            {
                "label": km.get("label"),
                "value": f"{km.get('value_pct')}%",
                "kind": kind,
            }
        )
    upside = metrics.get("fair_value_upside_pct") or metrics.get("analyst_upside_pct")
    if upside is not None and not any(r.get("label") == "Upside analistes" for r in rows):
        rows.insert(
            0,
            {"label": "Upside analistes", "value": f"{upside}%", "kind": "growth"},
        )
    iw = metrics.get("investwatch_summary") or {}
    if iw.get("avg_return_score") is not None:
        rows.append(
            {
                "label": "Score retorn (proxy)",
                "value": f"{iw['avg_return_score']}/7",
                "kind": "score",
            }
        )
    if iw.get("avg_risk_score") is not None:
        rows.append(
            {
                "label": "Score risc (proxy)",
                "value": f"{iw['avg_risk_score']}/7",
                "kind": "score",
            }
        )
    return rows[:10]


def build_investwatch_report_view(
    metrics: dict[str, Any],
    *,
    report_context: dict[str, Any] | None = None,
    crossover: dict[str, Any] | None = None,
    title: str = "",
) -> dict[str, Any]:
    """Build UI-ready InvestWatch report card (EINA crossover overlay included)."""
    report_context = report_context or {}
    crossover = crossover or {}
    tiered = crossover.get("tiered_recommendations") or {}

    company = (
        report_context.get("resolved_company")
        or metrics.get("reference_entity")
        or metrics.get("company_name")
    )
    if company and not is_valid_company_name(company):
        company = report_context.get("resolved_company") or metrics.get("reference_entity")

    ticker = (
        metrics.get("primary_ticker")
        or metrics.get("suggested_ticker")
        or (report_context.get("eina_link") or {}).get("ticker")
    )

    parse_mode = metrics.get("parse_mode") or "unknown"
    iw = metrics.get("investwatch_summary") or {}
    praams_ratio = metrics.get("praams_ratio") or iw.get("praams_ratio")

    rec = (
        metrics.get("primary_recommendation")
        or metrics.get("derived_signal")
        or tiered.get("external_signal")
    )
    if rec:
        rec = str(rec).upper()

    risk_sectors: list[dict[str, Any]] = []
    return_sectors: list[dict[str, Any]] = []

    if parse_mode == "praams_investwatch":
        risk_sectors, return_sectors = _praams_sectors(metrics)
    elif parse_mode == "investwatch":
        risk_sectors = _sectors_from_scores(metrics.get("risk_factors") or [], RISK_SECTOR_ORDER, kind="risk")
        return_sectors = _sectors_from_scores(
            metrics.get("return_factors") or [], RETURN_SECTOR_ORDER, kind="return"
        )
    else:
        risk_sectors, return_sectors = _praams_sectors(metrics)
        if not return_sectors and metrics.get("return_factors"):
            return_sectors = _sectors_from_scores(
                metrics.get("return_factors") or [], RETURN_SECTOR_ORDER, kind="return"
            )
        if not risk_sectors and metrics.get("risk_factors"):
            risk_sectors = _sectors_from_scores(metrics.get("risk_factors") or [], RISK_SECTOR_ORDER, kind="risk")

    eina_link = report_context.get("eina_link") or {}
    final_numbers = crossover.get("final_numbers") or {}
    fn_expl = crossover.get("final_numbers_explanations") or {}

    eina_overlay = {
        "linked": bool(eina_link.get("found")),
        "policy_link": eina_link.get("policy_link") or "",
        "beneficiary_rationale": (eina_link.get("beneficiary_rationale") or "")[:220],
        "sectors": eina_link.get("sectors") or [],
        "external_signal": tiered.get("external_signal") or rec,
        "private_action": (tiered.get("private") or [{}])[0].get("action") if tiered.get("private") else None,
        "blended_return_index": final_numbers.get("blended_return_index"),
        "external_return_index": final_numbers.get("external_return_index"),
        "eina_confidence_avg": final_numbers.get("eina_investment_confidence_avg"),
    }

    headline_parts: list[str] = []
    if praams_ratio is not None:
        headline_parts.append(f"PRAAMS Ratio {praams_ratio}/7")
    if rec:
        headline_parts.append(rec)
    upside = metrics.get("fair_value_upside_pct") or metrics.get("analyst_upside_pct")
    if upside is not None:
        headline_parts.append(f"upside {upside}%")

    return {
        "layout": "eina_investwatch_v1",
        "company": company,
        "ticker": ticker,
        "title": title[:120] if title else "",
        "parse_mode": parse_mode,
        "praams_ratio": praams_ratio,
        "recommendation": rec,
        "recommendation_class": _REC_CLASS.get(rec or "", "neutral"),
        "analyst_upside_pct": upside,
        "investwatch_summary": iw,
        "risk_sectors": risk_sectors,
        "return_sectors": return_sectors,
        "key_risk_summaries": metrics.get("key_risk_summaries") or [],
        "key_return_summaries": metrics.get("key_return_summaries") or [],
        "key_metrics": _key_metrics_display(metrics),
        "signal": iw.get("signal"),
        "headline": " · ".join(headline_parts) if headline_parts else "Informe financer creuat",
        "narrative": report_context.get("narrative") or "",
        "narrative_source": report_context.get("narrative_source") or "rules",
        "eina_overlay": eina_overlay,
        "has_clock": bool(risk_sectors or return_sectors or praams_ratio is not None),
    }
