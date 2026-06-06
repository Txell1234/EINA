"""HTML/PDF export for prospective inquiry reports."""
from __future__ import annotations

import asyncio
import html
import tempfile
from pathlib import Path
from typing import Any

from services.export_backends import ExportBackendError, render_pdf_from_html


def _esc(s: Any) -> str:
    return html.escape(str(s) if s is not None else "")


def build_inquiry_report_html(detail: dict[str, Any]) -> str:
    """Deterministic HTML report from inquiry detail payload."""
    q = detail.get("question", "")
    answer = detail.get("answer") or {}
    scope_audit = detail.get("scope_audit") or {}
    artifacts = detail.get("artifacts") or {}
    morph = artifacts.get("morph_bootstrap") or {}
    monitors = artifacts.get("monitor_suggestions") or {}
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
        parts.append("<ul>")
        for c in answer.get("conclusions") or []:
            parts.append(f"<li>{_esc(c)}</li>")
        parts.append("</ul>")

    if scope_audit:
        parts.append("<h2>Filtre OSINT (scope inquiry)</h2><ul>")
        for k in ("input", "kept", "removed_topic", "removed_must_match", "queries_run"):
            if k in scope_audit:
                parts.append(f"<li>{_esc(k)}: {_esc(scope_audit[k])}</li>")
        parts.append("</ul>")

    if monitors.get("suggested_monitors"):
        parts.append("<h2>Monitors suggerits</h2><ul>")
        for m in monitors["suggested_monitors"]:
            parts.append(f"<li>{_esc(m.get('indicator'))}</li>")
        parts.append("</ul>")

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


async def export_inquiry_pdf(detail: dict[str, Any], *, output_dir: Path | None = None) -> dict[str, Any]:
    """Export inquiry report as PDF via WeasyPrint; returns metadata or error."""
    html_str = build_inquiry_report_html(detail)
    inquiry_id = detail.get("id", "inquiry")
    out_dir = output_dir or Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"inquiry_{inquiry_id}.pdf"
    try:
        await asyncio.to_thread(render_pdf_from_html, html_str, pdf_path)
        return {"ok": True, "format": "pdf", "file_path": str(pdf_path.resolve())}
    except ExportBackendError as exc:
        return {
            "ok": False,
            "format": "pdf",
            "error": str(exc),
            "fallback": "html",
            "html": html_str,
        }


def export_inquiry_pdf_bytes(detail: dict[str, Any]) -> tuple[bytes | None, str]:
    """Sync PDF bytes for download response."""
    import tempfile

    html_str = build_inquiry_report_html(detail)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        render_pdf_from_html(html_str, tmp_path)
        return tmp_path.read_bytes(), "application/pdf"
    except ExportBackendError as exc:
        return None, str(exc)
    finally:
        tmp_path.unlink(missing_ok=True)