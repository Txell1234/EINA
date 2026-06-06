"""Resum executiu per informes d'inquiry Q2FS."""
from __future__ import annotations

import html
from typing import Any

from services.report_i18n import ReportLang, get_report_strings, normalize_lang


def _esc(s: Any) -> str:
    return html.escape(str(s) if s is not None else "")


def build_inquiry_executive_summary(detail: dict[str, Any], lang: str | None = None) -> str:
    """HTML block with executive summary for inquiry export."""
    lang_code: ReportLang = normalize_lang(lang)
    s = get_report_strings(lang_code)
    answer = detail.get("answer") or {}
    scope = detail.get("scope_audit") or {}
    artifacts = detail.get("artifacts") or {}
    morph = artifacts.get("morph_bootstrap") or {}
    monitors = artifacts.get("monitor_suggestions") or {}
    financial = artifacts.get("financial_crossover") or {}

    conclusions = answer.get("conclusions") or []
    reasoning = answer.get("reasoning") or []
    monitor_list = monitors.get("suggested_monitors") or []
    godet_rows = morph.get("godet_preview") or []

    parts = [
        f"<section class='executive-summary'><h2>{_esc(s.executive_summary)}</h2>",
        f"<p><strong>{_esc(s.es_hypothesis)}:</strong> {_esc(detail.get('question'))}</p>",
        f"<p><strong>{_esc(s.es_context)}:</strong> "
        f"Mode {_esc(detail.get('mode'))} · Estat {_esc(detail.get('status'))}</p>",
    ]

    if answer:
        parts.append(
            f"<p><strong>{_esc(s.probability)}:</strong> {_esc(answer.get('probability_pct'))}% · "
            f"<strong>{_esc(s.possibility)}:</strong> {_esc(answer.get('possibility'))}</p>"
        )
        if answer.get("possibility_rationale"):
            parts.append(f"<p>{_esc(answer.get('possibility_rationale'))}</p>")

    if scope:
        kept = scope.get("kept")
        rejected = (scope.get("removed_topic") or 0) + (scope.get("removed_must_match") or 0)
        parts.append(
            f"<p><strong>{_esc(s.es_osint)}:</strong> "
            f"{_esc(scope.get('queries_run', 0))} consultes · "
            f"{_esc(kept)} articles conservats · {_esc(rejected)} rebutjats per scope</p>"
        )

    if financial.get("found"):
        parts.append(
            f"<p><strong>Crossover financer:</strong> mode {_esc(financial.get('mode'))} · "
            f"{_esc(len(financial.get('rows') or financial.get('items') or []))} fileres</p>"
        )

    if godet_rows:
        parts.append(f"<p><strong>{_esc(s.es_scenarios)}:</strong></p><ul>")
        for row in godet_rows[:4]:
            parts.append(
                f"<li>{_esc(row.get('name'))}: {_esc(row.get('config'))} "
                f"({_esc(row.get('possibility'))})</li>"
            )
        parts.append("</ul>")

    if conclusions:
        parts.append(f"<p><strong>{_esc(s.es_conclusions)}:</strong></p><ul>")
        for c in conclusions[:6]:
            parts.append(f"<li>{_esc(c)}</li>")
        parts.append("</ul>")

    if reasoning:
        parts.append(f"<p><strong>Raonament traçable:</strong></p><ul>")
        for r in reasoning[:4]:
            if isinstance(r, dict):
                parts.append(
                    f"<li>{_esc(r.get('conclusion'))} — {_esc(r.get('because'))}</li>"
                )
        parts.append("</ul>")

    if monitor_list:
        parts.append("<p><strong>Monitors de vigilància:</strong></p><ul>")
        for m in monitor_list[:5]:
            if isinstance(m, dict):
                parts.append(f"<li>{_esc(m.get('indicator'))}</li>")
        parts.append("</ul>")

    parts.append(
        f"<p class='muted'><strong>{_esc(s.es_limitations)}:</strong> "
        "Conclusions deterministes sense inferència LLM addicional; traçabilitat via audit trail.</p>"
    )
    parts.append("</section>")
    return "\n".join(parts)
