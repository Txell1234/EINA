"""HTML export for prospective inquiry reports."""
from __future__ import annotations

import html
from typing import Any


def _esc(s: Any) -> str:
    return html.escape(str(s) if s is not None else "")


def build_inquiry_report_html(detail: dict[str, Any]) -> str:
    """Deterministic HTML report from inquiry detail payload."""
    q = detail.get("question", "")
    answer = detail.get("answer") or {}
    scope_audit = detail.get("scope_audit") or {}
    morph = (detail.get("artifacts") or {}).get("morph_bootstrap") or {}
    steps = detail.get("steps_log") or []

    parts = [
        "<!DOCTYPE html><html lang='ca'><head><meta charset='utf-8'>",
        "<title>Informe Inquiry Q2FS</title>",
        "<style>body{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}",
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:6px}",
        ".muted{color:#666}</style></head><body>",
        f"<h1>Informe analític Q2FS</h1>",
        f"<p class='muted'>Estat: {_esc(detail.get('status'))} · Mode: {_esc(detail.get('mode'))}</p>",
        f"<h2>Pregunta</h2><p>{_esc(q)}</p>",
    ]

    if answer:
        parts.append("<h2>Resposta (determinista)</h2>")
        parts.append(
            f"<p><strong>Probabilitat:</strong> {_esc(answer.get('probability_pct'))}% · "
            f"<strong>Possibilitat:</strong> {_esc(answer.get('possibility'))}</p>"
        )
        parts.append(f"<p>{_esc(answer.get('possibility_rationale'))}</p>")
        for c in answer.get("conclusions") or []:
            parts.append(f"<li>{_esc(c)}</li>")

    if scope_audit:
        parts.append("<h2>Filtre OSINT (scope inquiry)</h2><ul>")
        for k in ("input", "kept", "removed_topic", "removed_must_match", "queries_run"):
            if k in scope_audit:
                parts.append(f"<li>{_esc(k)}: {_esc(scope_audit[k])}</li>")
        parts.append("</ul>")
        for sample in scope_audit.get("rejected_samples") or []:
            parts.append(
                f"<p class='muted'>Descartat: {_esc(sample.get('title'))} — "
                f"{_esc('; '.join(sample.get('reasons') or []))}</p>"
            )

    if morph.get("godet_preview"):
        parts.append("<h2>Previsualització morfològica (Zwicky)</h2><table><tr>"
                     "<th>Escenari</th><th>Config</th><th>Possibilitat</th></tr>")
        for row in morph["godet_preview"]:
            parts.append(
                f"<tr><td>{_esc(row.get('name'))}</td>"
                f"<td>{_esc(row.get('config'))}</td>"
                f"<td>{_esc(row.get('possibility'))}</td></tr>"
            )
        parts.append("</table>")

    if steps:
        parts.append("<h2>Passos executats</h2><ol>")
        for s in steps:
            parts.append(f"<li>{_esc(s.get('step'))} — ok={_esc(s.get('ok'))}</li>")
        parts.append("</ol>")

    parts.append("<p class='muted'>Generat per EINA Q2FS — sense inferència LLM a conclusions.</p>")
    parts.append("</body></html>")
    return "\n".join(parts)
