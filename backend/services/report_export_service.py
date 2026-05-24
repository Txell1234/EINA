"""
Prospective Report Export — PDF (WeasyPrint) and DOCX (python-docx).

Loads data from SQLAlchemy models under models.prospective.
Blocking render calls run in asyncio.to_thread.
"""
from __future__ import annotations

import asyncio
import html
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.export_backends import ExportBackendError, render_pdf_from_html
from services.report_enrichment import enrich_project_bundle

from models.prospective import (
    MACTORObjective,
    MACTORPosture,
    MACTORResult,
    MICMACResult,
    MorphComponent,
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
    ProspectiveVariable,
)

logger = logging.getLogger(__name__)

_DOCX_HINT = "pip install 'python-docx>=1.1.0'"


def _load_docx():
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt, RGBColor
    except ImportError as exc:
        raise ExportBackendError("python-docx", str(exc), hint=_DOCX_HINT) from exc
    primary_rgb = RGBColor(0x1E, 0x3A, 0x5F)
    return Document, WD_ALIGN_PARAGRAPH, Pt, RGBColor, primary_rgb


def _ensure_reports_dir(base_dir: str | Path | None = None) -> Path:
    directory = Path(base_dir or "reports")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def _load_project_bundle(db: AsyncSession, project_id: int) -> Optional[dict[str, Any]]:
    """Fetch project and related rows needed for exports."""
    project_r = await db.execute(select(ProspectiveProject).where(ProspectiveProject.id == project_id))
    project = project_r.scalar_one_or_none()
    if not project:
        return None

    vars_q = (
        await db.execute(
            select(ProspectiveVariable)
            .where(ProspectiveVariable.project_id == project_id)
            .order_by(ProspectiveVariable.order_index)
        )
    ).scalars().all()

    actors_q = (
        await db.execute(
            select(ProspectiveActor)
            .where(ProspectiveActor.project_id == project_id)
            .order_by(ProspectiveActor.order_index)
        )
    ).scalars().all()

    objectives_q = (
        await db.execute(
            select(MACTORObjective)
            .where(MACTORObjective.project_id == project_id)
            .order_by(MACTORObjective.order_index)
        )
    ).scalars().all()

    posture_rows = (
        await db.execute(select(MACTORPosture).where(MACTORPosture.project_id == project_id))
    ).scalars().all()

    micmac_r = await db.execute(select(MICMACResult).where(MICMACResult.project_id == project_id))
    micmac = micmac_r.scalar_one_or_none()

    mactor_r = await db.execute(select(MACTORResult).where(MACTORResult.project_id == project_id))
    mactor_result = mactor_r.scalar_one_or_none()

    morph_q = (
        await db.execute(
            select(MorphComponent)
            .where(MorphComponent.project_id == project_id)
            .order_by(MorphComponent.order_index)
        )
    ).scalars().all()

    scenarios_q = (
        await db.execute(
            select(ProspectiveScenario)
            .where(ProspectiveScenario.project_id == project_id)
            .order_by(ProspectiveScenario.id)
        )
    ).scalars().all()

    actor_codes = [a.code for a in actors_q]
    objective_codes = [o.code for o in objectives_q]
    posture_map = {(p.actor_code, p.objective_code): p.posture_value for p in posture_rows}
    postures_matrix: list[list[int]] = []
    for ac in actor_codes:
        row = []
        for oc in objective_codes:
            row.append(int(posture_map.get((ac, oc), 0)))
        postures_matrix.append(row)

    return await enrich_project_bundle(
        db,
        {
        "project": project,
        "variables": list(vars_q),
        "actors": list(actors_q),
        "objectives": list(objectives_q),
        "actor_codes": actor_codes,
        "objective_codes": objective_codes,
        "postures_matrix": postures_matrix,
        "micmac": micmac,
        "mactor_result": mactor_result,
        "components": list(morph_q),
        "scenarios": list(scenarios_q),
        },
    )


def _format_sectors_table(sectors: Any) -> list[list[str]]:
    if not isinstance(sectors, list):
        return []
    rows: list[list[str]] = []
    for s in sectors:
        if isinstance(s, dict):
            rows.append(
                [
                    str(s.get("code", "")),
                    str(s.get("sector", "")),
                    str(s.get("motricitat", s.get("motricite", ""))),
                    str(s.get("dependencia", s.get("dependence", ""))),
                ]
            )
    return rows


def _posture_label(value: int) -> str:
    labels = {
        2: "+2 molt favorable",
        1: "+1 favorable",
        0: "0 neutral",
        -1: "-1 contrari",
        -2: "-2 molt contrari",
    }
    return labels.get(value, str(value))


def _append_case_briefing_html(parts: list[str], bundle: dict[str, Any]) -> None:
    case = bundle.get("case")
    if not case:
        return
    parts.append("<h1>Briefing del cas OSINT</h1>")
    parts.append(f"<p><strong>Nom:</strong> {_escape(case.name)}</p>")
    if case.description:
        parts.append(f"<p><strong>Descripció completa:</strong></p><p>{_escape(case.description)}</p>")
    prompt = bundle.get("case_prompt")
    if prompt and prompt.ai_analysis:
        parts.append("<h2>Pla de recerca (IA)</h2>")
        parts.append(f"<pre class='json'>{_escape(_json_block(prompt.ai_analysis))}</pre>")


def _append_osint_sources_html(parts: list[str], bundle: dict[str, Any]) -> None:
    articles: list = bundle.get("osint_articles") or []
    errors: list = bundle.get("osint_query_errors") or []
    parts.append("<h1>Fonts OSINT i recollida</h1>")

    if not articles and not errors:
        parts.append("<p class='muted'>Sense fonts OSINT vinculades al cas.</p>")
        return

    parts.append(
        f"<p class='muted'>{len(articles)} articles recollits · "
        f"{len(errors)} consulta(s) amb error</p>"
    )

    if articles:
        parts.append("<h2>Articles i fonts recollides</h2>")
        parts.append(
            '<table class="grid"><thead><tr>'
            "<th>Tipus consulta</th><th>Font</th><th>Títol</th><th>URL</th>"
            "<th>Data</th><th>Consulta</th>"
            "</tr></thead><tbody>"
        )
        for a in articles[:200]:
            url = a.get("url") or ""
            url_cell = f'<a href="{_escape(url)}">{_escape(url[:80])}</a>' if url else "—"
            params = _escape(_json_block(a.get("query_params") or {}))[:80]
            parts.append(
                f"<tr><td>{_escape(a.get('query_type'))}</td>"
                f"<td>{_escape(a.get('source') or '—')}</td>"
                f"<td>{_escape(a.get('title') or '—')}</td><td>{url_cell}</td>"
                f"<td>{_escape(a.get('date') or '—')}</td>"
                f"<td>{params}</td></tr>"
            )
        parts.append("</tbody></table>")
        if len(articles) > 200:
            parts.append(f"<p class='muted'>(Mostrant 200 de {len(articles)} articles)</p>")

    if errors:
        parts.append("<h2>Errors de recollida</h2>")
        parts.append(
            '<table class="grid"><thead><tr>'
            "<th>Tipus consulta</th><th>Paràmetres</th><th>Error</th><th>Estat</th>"
            "</tr></thead><tbody>"
        )
        for e in errors:
            params = _escape(_json_block(e.get("query_params") or {}))[:120]
            parts.append(
                f"<tr><td>{_escape(e.get('query_type'))}</td><td>{params}</td>"
                f"<td>{_escape(e.get('error') or '—')}</td>"
                f"<td>{_escape(e.get('result_status'))}</td></tr>"
            )
        parts.append("</tbody></table>")


def _append_extraction_html(parts: list[str], bundle: dict[str, Any]) -> None:
    statements: list = bundle.get("statements") or []
    parts.append("<h1>Extracció estructurada (declaracions)</h1>")
    if not statements:
        parts.append("<p class='muted'>Cap declaració extreta. Executa l'extracció OSINT abans de l'anàlisi.</p>")
        return
    parts.append(f"<p class='muted'>Total: {len(statements)} declaracions</p>")
    parts.append(
        '<table class="grid"><thead><tr>'
        "<th>Actor</th><th>Declaració</th><th>Postura</th><th>Tema</th>"
        "<th>Font (URL)</th><th>Data</th><th>Grounding</th><th>Estat</th>"
        "</tr></thead><tbody>"
    )
    for s in statements[:120]:
        url = s.source_url or ""
        url_cell = f'<a href="{_escape(url)}">{_escape(url[:60])}</a>' if url else "—"
        parts.append(
            f"<tr><td>{_escape(s.actor)}</td><td>{_escape(s.statement[:400])}</td>"
            f"<td>{_escape(_posture_label(int(s.posture_value or 0)))} → {_escape(s.posture_toward)}</td>"
            f"<td>{_escape(s.topic)}</td><td>{url_cell}</td>"
            f"<td>{_escape(s.source_date)}</td>"
            f"<td>{_escape(str(s.grounding_score))}</td>"
            f"<td>{_escape(s.cleanup_decision)}</td></tr>"
        )
    if len(statements) > 120:
        parts.append(f"</tbody></table><p class='muted'>(Mostrant 120 de {len(statements)})</p>")
    else:
        parts.append("</tbody></table>")


def _append_retrospective_html(parts: list[str], bundle: dict[str, Any]) -> None:
    retro = bundle.get("retrospective")
    parts.append("<h1>Anàlisi retrospectiva</h1>")
    if not retro or not retro.get("has_data"):
        parts.append(f"<p class='muted'>{_escape((retro or {}).get('message', 'Sense dades retrospectives.'))}</p>")
        return
    parts.append(
        f"<p class='muted'>{retro.get('total_statements', 0)} declaracions · "
        f"rang: {_escape(str(retro.get('date_range')))}</p>"
    )
    key_events = retro.get("key_events") or []
    if key_events:
        parts.append("<h2>Esdeveniments clau (|postura| ≥ 2)</h2>")
        parts.append('<table class="grid"><thead><tr><th>Data</th><th>Actor</th><th>Declaració</th><th>Font</th></tr></thead><tbody>')
        for ev in key_events[:30]:
            parts.append(
                f"<tr><td>{_escape(ev.get('date'))}</td><td>{_escape(ev.get('actor'))}</td>"
                f"<td>{_escape(str(ev.get('statement', ''))[:300])}</td>"
                f"<td>{_escape(ev.get('source_url'))}</td></tr>"
            )
        parts.append("</tbody></table>")
    evidence = (retro.get("micmac_evidence") or {})
    pairs = evidence.get("pairs") or []
    if pairs:
        parts.append("<h2>Evidència OSINT per relacions MIC-MAC</h2>")
        if evidence.get("interpretation"):
            parts.append(f"<p>{_escape(evidence['interpretation'])}</p>")
        parts.append('<table class="grid"><thead><tr><th>De (tema)</th><th>Cap a</th><th>N. declaracions</th><th>Confiança</th></tr></thead><tbody>')
        for p in pairs[:40]:
            parts.append(
                f"<tr><td>{_escape(p.get('from_topic'))}</td><td>{_escape(p.get('to_topic'))}</td>"
                f"<td>{p.get('n_statements')}</td><td>{p.get('confidence')}</td></tr>"
            )
        parts.append("</tbody></table>")


def _append_qual_quant_html(parts: list[str], bundle: dict[str, Any]) -> None:
    qual: list = bundle.get("qualitative_analyses") or []
    quant: list = bundle.get("quantitative_analyses") or []
    if not qual and not quant:
        return
    parts.append("<h1>Raonament qualitatiu i quantitatiu</h1>")
    if qual:
        parts.append("<h2>Anàlisi qualitativa</h2>")
        for i, q in enumerate(qual, 1):
            parts.append(f"<h3>Anàlisi {i}</h3>")
            if q.get("framework_name"):
                parts.append(f"<p><strong>Marc:</strong> {_escape(q['framework_name'])} ({_escape(q.get('framework_type'))})</p>")
            parts.append(f"<p><strong>Premissa:</strong> {_escape(q.get('premise'))}</p>")
            parts.append(f"<p><strong>Conclusions:</strong> {_escape(q.get('conclusions'))}</p>")
            if q.get("evidence"):
                parts.append(f"<pre class='json'>{_escape(_json_block(q['evidence']))}</pre>")
            parts.append(f"<p class='muted'>Confiança: {q.get('confidence_score')}</p>")
    if quant:
        parts.append("<h2>Anàlisi quantitativa (KPIs)</h2>")
        parts.append('<table class="grid"><thead><tr><th>KPI</th><th>Tipus</th><th>Valor</th><th>Unitat</th></tr></thead><tbody>')
        for q in quant:
            parts.append(
                f"<tr><td>{_escape(q.get('kpi_name'))}</td><td>{_escape(q.get('metric_type') or q.get('kpi_type'))}</td>"
                f"<td>{_escape(q.get('value'))}</td><td>{_escape(q.get('unit'))}</td></tr>"
            )
        parts.append("</tbody></table>")


def _append_micmac_reasoning_html(parts: list[str], bundle: dict[str, Any]) -> None:
    suggestions = bundle.get("micmac_suggestions")
    if not suggestions or not suggestions.get("suggestions"):
        return
    parts.append("<h2>Raonament geopolític (suggeriments matriu MIC-MAC)</h2>")
    parts.append(
        f"<p class='muted'>{suggestions.get('relations_count', 0)} relacions bilaterals · "
        f"{suggestions.get('events_count', 0)} esdeveniments diplomàtics</p>"
    )
    parts.append('<table class="grid"><thead><tr><th>Fila</th><th>Columna</th><th>Valor</th><th>Raonament</th><th>Font</th></tr></thead><tbody>')
    vars_list = bundle.get("variables") or []
    for s in suggestions.get("suggestions", [])[:50]:
        row_i, col_i = s.get("row"), s.get("col")
        row_code = vars_list[row_i].code if isinstance(row_i, int) and row_i < len(vars_list) else str(row_i)
        col_code = vars_list[col_i].code if isinstance(col_i, int) and col_i < len(vars_list) else str(col_i)
        parts.append(
            f"<tr><td>{_escape(row_code)}</td><td>{_escape(col_code)}</td>"
            f"<td>{s.get('value')}</td><td>{_escape(s.get('reason'))}</td>"
            f"<td>{_escape(s.get('source'))}</td></tr>"
        )
    parts.append("</tbody></table>")


def _doc_table(doc: Any, headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        doc.add_paragraph("Sense dades.")
        return
    table = doc.add_table(rows=1, cols=len(headers))
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)[:500]


def _append_case_briefing_docx(doc: Any, bundle: dict[str, Any]) -> None:
    case = bundle.get("case")
    if not case:
        return
    doc.add_heading("Briefing del cas OSINT", level=1)
    doc.add_paragraph(f"Nom: {case.name}")
    if case.description:
        doc.add_paragraph("Descripció completa:")
        doc.add_paragraph(case.description)
    prompt = bundle.get("case_prompt")
    if prompt and prompt.ai_analysis:
        doc.add_heading("Pla de recerca (IA)", level=2)
        doc.add_paragraph(_json_block(prompt.ai_analysis))


def _append_osint_sources_docx(doc: Any, bundle: dict[str, Any]) -> None:
    articles: list = bundle.get("osint_articles") or []
    errors: list = bundle.get("osint_query_errors") or []
    doc.add_heading("Fonts OSINT i recollida", level=1)
    if not articles and not errors:
        doc.add_paragraph("Sense fonts OSINT vinculades al cas.")
        return
    doc.add_paragraph(f"{len(articles)} articles recollits · {len(errors)} consulta(s) amb error")
    if articles:
        doc.add_heading("Articles i fonts recollides", level=2)
        rows = [
            [
                str(a.get("query_type", "")),
                str(a.get("source") or "—"),
                str(a.get("title") or "—")[:120],
                str(a.get("url") or "—")[:120],
                str(a.get("date") or "—"),
            ]
            for a in articles[:150]
        ]
        _doc_table(doc, ["Tipus", "Font", "Títol", "URL", "Data"], rows)
        if len(articles) > 150:
            doc.add_paragraph(f"(Mostrant 150 de {len(articles)} articles)")
    if errors:
        doc.add_heading("Errors de recollida", level=2)
        err_rows = [
            [
                str(e.get("query_type", "")),
                _json_block(e.get("query_params") or {})[:80],
                str(e.get("error") or "—")[:200],
                str(e.get("result_status", "")),
            ]
            for e in errors
        ]
        _doc_table(doc, ["Tipus", "Paràmetres", "Error", "Estat"], err_rows)


def _append_extraction_docx(doc: Any, bundle: dict[str, Any]) -> None:
    statements: list = bundle.get("statements") or []
    doc.add_heading("Extracció estructurada (declaracions)", level=1)
    if not statements:
        doc.add_paragraph("Cap declaració extreta.")
        return
    doc.add_paragraph(f"Total: {len(statements)} declaracions")
    rows = [
        [
            s.actor,
            (s.statement or "")[:200],
            f"{_posture_label(int(s.posture_value or 0))} → {s.posture_toward or ''}",
            s.topic or "",
            (s.source_url or "—")[:80],
            s.source_date or "",
            str(s.grounding_score or ""),
            s.cleanup_decision or "",
        ]
        for s in statements[:80]
    ]
    _doc_table(
        doc,
        ["Actor", "Declaració", "Postura", "Tema", "URL", "Data", "Grounding", "Estat"],
        rows,
    )
    if len(statements) > 80:
        doc.add_paragraph(f"(Mostrant 80 de {len(statements)})")


def _append_retrospective_docx(doc: Any, bundle: dict[str, Any]) -> None:
    retro = bundle.get("retrospective")
    doc.add_heading("Anàlisi retrospectiva", level=1)
    if not retro or not retro.get("has_data"):
        doc.add_paragraph((retro or {}).get("message", "Sense dades retrospectives."))
        return
    doc.add_paragraph(
        f"{retro.get('total_statements', 0)} declaracions · Rang: {retro.get('date_range')}"
    )
    for ev in (retro.get("key_events") or [])[:20]:
        doc.add_paragraph(
            f"• [{ev.get('date', '?')}] {ev.get('actor', '')}: {(ev.get('statement') or '')[:180]} "
            f"(Font: {ev.get('source_url', '—')})"
        )
    evidence = retro.get("micmac_evidence") or {}
    if evidence.get("interpretation"):
        doc.add_paragraph(evidence["interpretation"])
    pairs = evidence.get("pairs") or []
    if pairs:
        doc.add_heading("Evidència OSINT per MIC-MAC", level=2)
        _doc_table(
            doc,
            ["De (tema)", "Cap a", "N. declaracions", "Confiança"],
            [[p.get("from_topic", ""), p.get("to_topic", ""), str(p.get("n_statements", "")), str(p.get("confidence", ""))] for p in pairs[:30]],
        )


def _append_qual_quant_docx(doc: Any, bundle: dict[str, Any]) -> None:
    qual: list = bundle.get("qualitative_analyses") or []
    quant: list = bundle.get("quantitative_analyses") or []
    if not qual and not quant:
        return
    doc.add_heading("Raonament qualitatiu i quantitatiu", level=1)
    for i, q in enumerate(qual, 1):
        doc.add_heading(f"Anàlisi qualitativa {i}", level=2)
        if q.get("framework_name"):
            doc.add_paragraph(f"Marc: {q['framework_name']} ({q.get('framework_type')})")
        doc.add_paragraph(f"Premissa: {q.get('premise', '')}")
        doc.add_paragraph(f"Conclusions: {q.get('conclusions', '')}")
        if q.get("evidence"):
            doc.add_paragraph(_json_block(q["evidence"]))
    if quant:
        doc.add_heading("Anàlisi quantitativa (KPIs)", level=2)
        _doc_table(
            doc,
            ["KPI", "Tipus", "Valor", "Unitat"],
            [[q.get("kpi_name", ""), q.get("metric_type") or q.get("kpi_type", ""), q.get("value", ""), q.get("unit") or ""] for q in quant],
        )


def _append_micmac_reasoning_docx(doc: Any, bundle: dict[str, Any]) -> None:
    suggestions = bundle.get("micmac_suggestions")
    if not suggestions or not suggestions.get("suggestions"):
        return
    doc.add_heading("Raonament geopolític (suggeriments MIC-MAC)", level=2)
    vars_list = bundle.get("variables") or []
    rows = []
    for s in suggestions.get("suggestions", [])[:40]:
        row_i, col_i = s.get("row"), s.get("col")
        row_code = vars_list[row_i].code if isinstance(row_i, int) and row_i < len(vars_list) else str(row_i)
        col_code = vars_list[col_i].code if isinstance(col_i, int) and col_i < len(vars_list) else str(col_i)
        rows.append([row_code, col_code, str(s.get("value", "")), str(s.get("reason", "")), str(s.get("source", ""))])
    _doc_table(doc, ["Fila", "Columna", "Valor", "Raonament", "Font"], rows)


def _json_block(data: Any) -> str:
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except TypeError:
        return str(data)


def _escape(s: Optional[str]) -> str:
    if s is None:
        return ""
    return html.escape(str(s))


def _html_report(bundle: dict[str, Any]) -> str:
    project: ProspectiveProject = bundle["project"]
    vars_list: list = bundle["variables"]
    actors_list: list = bundle["actors"]
    objectives_list: list = bundle["objectives"]
    micmac: Optional[MICMACResult] = bundle["micmac"]
    mactor_result: Optional[MACTORResult] = bundle["mactor_result"]
    components: list = bundle["components"]
    scenarios_list: list = bundle["scenarios"]
    actor_codes = bundle["actor_codes"]
    objective_codes = bundle["objective_codes"]
    postures_matrix = bundle["postures_matrix"]

    css = """
    @page { size: A4; margin: 18mm 16mm; }
    body { font-family: "DejaVu Sans", Helvetica, Arial, sans-serif; font-size: 10pt; color: #222; }
    h1 { color: #1e3a5f; font-size: 18pt; margin-top: 0; border-bottom: 2px solid #ff6b35; padding-bottom: 6px; }
    h2 { color: #1e3a5f; font-size: 12pt; margin-top: 16px; }
    .muted { color: #555; font-size: 9pt; }
    table.grid { border-collapse: collapse; width: 100%; margin: 8px 0 12px 0; }
    table.grid th, table.grid td { border: 1px solid #ccc; padding: 4px 6px; text-align: left; vertical-align: top; }
    table.grid th { background: #f3f6f9; font-weight: 600; }
    pre.json { white-space: pre-wrap; font-size: 8.5pt; background: #f8f9fa; padding: 8px; border-radius: 4px; }
    .cover-title { font-size: 26pt; color: #1e3a5f; margin-bottom: 4px; }
    .cover-sub { font-size: 14pt; color: #333; margin-bottom: 18px; }
    """

    parts: list[str] = []
    parts.append(f"<style>{css}</style>")
    parts.append('<div class="cover-title">Informe prospectiu · EINA</div>')
    parts.append(f"<div class='cover-sub'>{_escape(project.title)}</div>")
    parts.append(f"<p class='muted'>Projecte ID {project.id} · Generat {_escape(_utc_now_iso())}</p>")

    parts.append("<h1>Projecte</h1>")
    parts.append("<p><strong>Hipòtesi</strong></p>")
    parts.append(f"<p>{_escape(project.hypothesis)}</p>")
    parts.append("<p><strong>Context</strong></p>")
    parts.append(f"<p>{_escape(project.context)}</p>")

    _append_case_briefing_html(parts, bundle)
    _append_osint_sources_html(parts, bundle)
    _append_extraction_html(parts, bundle)
    _append_retrospective_html(parts, bundle)

    parts.append("<h1>Variables (MIC-MAC)</h1>")
    suggested_vars = bundle.get("suggested_variables") or []
    if suggested_vars:
        parts.append("<h2>Suggeriments des de l'extracció OSINT</h2>")
        parts.append('<table class="grid"><thead><tr><th>Codi</th><th>Nom</th><th>Tipus</th><th>Raonament</th></tr></thead><tbody>')
        for sv in suggested_vars[:20]:
            parts.append(
                f"<tr><td>{_escape(sv.get('code'))}</td><td>{_escape(sv.get('name'))}</td>"
                f"<td>{_escape(sv.get('type'))}</td><td>{_escape(sv.get('rationale') or sv.get('desc', ''))}</td></tr>"
            )
        parts.append("</tbody></table>")
    if vars_list:
        parts.append('<table class="grid"><thead><tr><th>Codi</th><th>Nom</th><th>Tipus</th><th>Descripció</th></tr></thead><tbody>')
        for v in vars_list:
            parts.append(
                f"<tr><td>{_escape(v.code)}</td><td>{_escape(v.name)}</td>"
                f"<td>{_escape(v.var_type)}</td><td>{_escape(v.description)}</td></tr>"
            )
        parts.append("</tbody></table>")
    else:
        parts.append("<p class='muted'>Sense variables registrades.</p>")

    parts.append("<h1>Resultats MIC-MAC</h1>")
    if micmac:
        vb = micmac.vb_index
        vr = micmac.vr_index
        meta = (
            f"<p class='muted'>Calculat: {_escape(micmac.calculated_at.isoformat()) if micmac.calculated_at else '—'}"
            f" · VB index: {_escape(str(vb) if vb is not None else '—')}"
            f" · VR index: {_escape(str(vr) if vr is not None else '—')} </p>"
        )
        parts.append(meta)
        sector_rows = _format_sectors_table(micmac.sectors)
        if sector_rows:
            parts.append("<h2>Classificació per sectors (Godet)</h2>")
            parts.append('<table class="grid"><thead><tr><th>Codi</th><th>Sector</th><th>Motricitat</th><th>Dependència</th></tr></thead><tbody>')
            for row in sector_rows:
                parts.append(f"<tr><td>{_escape(row[0])}</td><td>{_escape(row[1])}</td><td>{_escape(row[2])}</td><td>{_escape(row[3])}</td></tr>")
            parts.append("</tbody></table>")
        _append_micmac_reasoning_html(parts, bundle)
        for label, blob in (
            ("Sectors", micmac.sectors),
            ("Motricitat directa", micmac.motricite_direct),
            ("Dependència directa", micmac.dependence_direct),
            ("Matriu directa", micmac.matrix_direct),
            ("Matriu indirecta", micmac.matrix_indirect),
        ):
            if blob is not None:
                parts.append(f"<h2>{_escape(label)}</h2><pre class='json'>{_escape(_json_block(blob))}</pre>")
    else:
        parts.append("<p class='muted'>Encara sense càlcul MIC-MAC desat.</p>")

    parts.append("<h1>MACTOR · Actors i objectius</h1>")
    suggested_actors = bundle.get("suggested_actors") or []
    if suggested_actors:
        parts.append("<h2>Actors suggerits per l'extracció OSINT</h2>")
        parts.append('<table class="grid"><thead><tr><th>Codi</th><th>Nom</th><th>Força</th><th>Declaracions</th></tr></thead><tbody>')
        for sa in suggested_actors[:15]:
            parts.append(
                f"<tr><td>{_escape(sa.get('code'))}</td><td>{_escape(sa.get('name'))}</td>"
                f"<td>{_escape(str(sa.get('force')))}</td><td>{sa.get('statement_count', sa.get('n_statements', ''))}</td></tr>"
            )
        parts.append("</tbody></table>")
    if actors_list:
        parts.append('<table class="grid"><thead><tr><th>Codi</th><th>Nom</th><th>Força</th><th>Fins estratègics</th></tr></thead><tbody>')
        for a in actors_list:
            fins = ", ".join(a.strategic_goals or [])
            parts.append(
                f"<tr><td>{_escape(a.code)}</td><td>{_escape(a.name)}</td>"
                f"<td>{_escape(str(a.force_score))}</td><td>{_escape(fins)}</td></tr>"
            )
        parts.append("</tbody></table>")
    if objectives_list:
        parts.append("<h2>Objectius</h2>")
        parts.append('<table class="grid"><thead><tr><th>Codi</th><th>Nom</th></tr></thead><tbody>')
        for o in objectives_list:
            parts.append(f"<tr><td>{_escape(o.code)}</td><td>{_escape(o.name)}</td></tr>")
        parts.append("</tbody></table>")

    if actor_codes and objective_codes and postures_matrix:
        parts.append("<h2>Matriu de postures</h2>")
        parts.append('<table class="grid"><thead><tr><th>Actor \\ Objectiu</th>')
        parts.extend(f"<th>{_escape(oc)}</th>" for oc in objective_codes)
        parts.append("</tr></thead><tbody>")
        for i, ac in enumerate(actor_codes):
            parts.append(f"<tr><th>{_escape(ac)}</th>")
            row = postures_matrix[i] if i < len(postures_matrix) else []
            for j in range(len(objective_codes)):
                val = row[j] if j < len(row) else ""
                parts.append(f"<td>{_escape(str(val))}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    parts.append("<h2>Agregats MACTOR</h2>")
    if mactor_result:
        for label, blob in (
            ("Mobilització actors", mactor_result.mobilisation_actors),
            ("Mobilització objectius", mactor_result.mobilisation_objectives),
            ("Matriu de convergències", mactor_result.convergences_matrix),
        ):
            if blob is not None:
                parts.append(f"<h3>{_escape(label)}</h3><pre class='json'>{_escape(_json_block(blob))}</pre>")
    else:
        parts.append("<p class='muted'>Sense resultats MACTOR calculats.</p>")

    parts.append("<h1>Anàlisi morfològic</h1>")
    if components:
        for c in components:
            parts.append(f"<h2>{_escape(c.code)} · {_escape(c.name)}</h2>")
            confs = c.configurations or []
            if isinstance(confs, list) and confs:
                parts.append('<table class="grid"><thead><tr><th>Etiqueta</th><th>Descripció</th></tr></thead><tbody>')
                for cfg in confs:
                    if isinstance(cfg, dict):
                        parts.append(
                            f"<tr><td>{_escape(cfg.get('label', ''))}</td>"
                            f"<td>{_escape(cfg.get('desc', ''))}</td></tr>"
                        )
                    else:
                        parts.append(f"<tr><td colspan='2'>{_escape(str(cfg))}</td></tr>")
                parts.append("</tbody></table>")
            else:
                parts.append("<p class='muted'>Sense configuracions.</p>")
    else:
        parts.append("<p class='muted'>Sense components morfològics.</p>")

    incompat = bundle.get("incompatibilities") or []
    if incompat:
        parts.append("<h2>Incompatibilitats morfològiques</h2>")
        parts.append('<table class="grid"><thead><tr><th>Component A</th><th>Config A</th><th>Component B</th><th>Config B</th></tr></thead><tbody>')
        for row in incompat[:30]:
            parts.append(
                f"<tr><td>{_escape(row.get('component_a'))}</td><td>{_escape(row.get('config_a'))}</td>"
                f"<td>{_escape(row.get('component_b'))}</td><td>{_escape(row.get('config_b'))}</td></tr>"
            )
        parts.append("</tbody></table>")

    smic = bundle.get("smic") or {}
    if smic and smic.get("initial_probs"):
        parts.append("<h2>SMIC · Probabilitats d'escenari</h2>")
        parts.append(f"<pre class='json'>{_escape(_json_block(smic))}</pre>")

    parts.append("<h1>Escenaris</h1>")
    if scenarios_list:
        for s in scenarios_list:
            parts.append(f"<h2>{_escape(s.name)} ({_escape(s.scenario_type or '')})</h2>")
            parts.append(f"<p class='muted'>Probabilitat: {_escape(s.probability)}</p>")
            if s.morphological_config:
                parts.append(f"<p><strong>Configuració</strong> {_escape(s.morphological_config)}</p>")
            nar = _escape(s.narrative or "").replace("\n", "<br/>")
            parts.append(f"<div>{nar}</div>")
    else:
        parts.append("<p class='muted'>Sense narratives d'escenari generades.</p>")

    _append_qual_quant_html(parts, bundle)

    return "<html><meta charset='utf-8'><body>" + "".join(parts) + "</body></html>"


def _write_pdf_sync(path: Path, bundle: dict[str, Any]) -> None:
    html_str = _html_report(bundle)
    try:
        render_pdf_from_html(html_str, path, base_url=str(path.parent.resolve()))
    except ExportBackendError as exc:
        raise RuntimeError(str(exc)) from exc


def _add_doc_cover(doc: Any, project: ProspectiveProject) -> None:
    """
    DOCX cover: iterate (text, size, grey_rgb) tuples only — add paragraph per row.
    (Avoid unpacking a nonexistent `paragraph` tuple element from fixed triples.)
    """
    _, WD_ALIGN_PARAGRAPH, Pt, RGBColor, PRIMARY_RGB = _load_docx()
    subtitle_grey = RGBColor(0x33, 0x33, 0x33)
    meta_grey = RGBColor(0x66, 0x66, 0x66)
    accent_orange = RGBColor(0xFF, 0x6B, 0x35)

    cover_lines: list[tuple[str, Pt, RGBColor]] = [
        ("Informe prospectiu · EINA", Pt(26), PRIMARY_RGB),
        (project.title, Pt(22), subtitle_grey),
        ("MIC-MAC · MACTOR · Morfologia · Escenaris", Pt(13), subtitle_grey),
        (f"ID projecte {project.id}", Pt(11), meta_grey),
        (f"Generat: {_utc_now_iso()}", Pt(11), meta_grey),
        ("______________________________________________", Pt(9), accent_orange),
    ]

    for txt, sz, grey in cover_lines:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(txt)
        run.font.size = sz
        run.font.color.rgb = grey

    doc.add_page_break()


def _populate_doc_body(doc: Any, bundle: dict[str, Any]) -> None:
    project: ProspectiveProject = bundle["project"]
    vars_list: list = bundle["variables"]
    actors_list: list = bundle["actors"]
    objectives_list: list = bundle["objectives"]
    micmac: Optional[MICMACResult] = bundle["micmac"]
    mactor_result: Optional[MACTORResult] = bundle["mactor_result"]
    components: list = bundle["components"]
    scenarios_list: list = bundle["scenarios"]
    actor_codes = bundle["actor_codes"]
    objective_codes = bundle["objective_codes"]
    postures_matrix = bundle["postures_matrix"]

    _, _, _, _, PRIMARY_RGB = _load_docx()

    h = doc.add_heading("Projecte", level=1)
    h.runs[0].font.color.rgb = PRIMARY_RGB
    doc.add_paragraph(project.hypothesis or "")
    doc.add_heading("Context", level=2)
    doc.add_paragraph(project.context or "")

    _append_case_briefing_docx(doc, bundle)
    _append_osint_sources_docx(doc, bundle)
    _append_extraction_docx(doc, bundle)
    _append_retrospective_docx(doc, bundle)

    doc.add_heading("Variables (MIC-MAC)", level=1)
    suggested_vars = bundle.get("suggested_variables") or []
    if suggested_vars:
        doc.add_heading("Suggeriments des de l'extracció OSINT", level=2)
        _doc_table(
            doc,
            ["Codi", "Nom", "Tipus", "Raonament"],
            [
                [sv.get("code", ""), sv.get("name", ""), sv.get("type", ""), sv.get("rationale") or sv.get("desc", "")]
                for sv in suggested_vars[:20]
            ],
        )
    if vars_list:
        table = doc.add_table(rows=1, cols=4)
        hdr = table.rows[0].cells
        hdr[0].text = "Codi"
        hdr[1].text = "Nom"
        hdr[2].text = "Tipus"
        hdr[3].text = "Descripció"
        for v in vars_list:
            row = table.add_row().cells
            row[0].text = str(v.code)
            row[1].text = str(v.name)
            row[2].text = str(v.var_type or "")
            row[3].text = str(v.description or "")
    else:
        doc.add_paragraph("Sense variables.")

    doc.add_heading("Resultats MIC-MAC", level=1)
    if micmac:
        sector_rows = _format_sectors_table(micmac.sectors)
        if sector_rows:
            doc.add_heading("Classificació per sectors (Godet)", level=2)
            _doc_table(doc, ["Codi", "Sector", "Motricitat", "Dependència"], sector_rows)
        _append_micmac_reasoning_docx(doc, bundle)
        micmac_sections = (
            ("Sectors", micmac.sectors),
            ("Motricitat directa", micmac.motricite_direct),
            ("Dependència directa", micmac.dependence_direct),
            ("Matriu directa", micmac.matrix_direct),
            ("Matriu indirecta", micmac.matrix_indirect),
        )
        for title, blob in micmac_sections:
            if blob is not None:
                doc.add_heading(title, level=2)
                doc.add_paragraph(_json_block(blob))
    else:
        doc.add_paragraph("Sense MIC-MAC desat.")

    doc.add_heading("MACTOR", level=1)
    suggested_actors = bundle.get("suggested_actors") or []
    if suggested_actors:
        doc.add_heading("Actors suggerits per l'extracció OSINT", level=2)
        _doc_table(
            doc,
            ["Codi", "Nom", "Força", "Declaracions"],
            [[sa.get("code", ""), sa.get("name", ""), str(sa.get("force", "")), str(sa.get("statement_count", sa.get("n_statements", "")))] for sa in suggested_actors[:15]],
        )
    if actors_list:
        t = doc.add_table(rows=1, cols=4)
        hr = t.rows[0].cells
        hr[0].text = "Codi"
        hr[1].text = "Nom"
        hr[2].text = "Força"
        hr[3].text = "Fins"
        for a in actors_list:
            r = t.add_row().cells
            r[0].text = str(a.code)
            r[1].text = str(a.name)
            r[2].text = str(a.force_score)
            r[3].text = ", ".join(a.strategic_goals or [])
    if objectives_list:
        doc.add_heading("Objectius", level=2)
        ot = doc.add_table(rows=1, cols=2)
        ohr = ot.rows[0].cells
        ohr[0].text = "Codi"
        ohr[1].text = "Nom"
        for o in objectives_list:
            oc = ot.add_row().cells
            oc[0].text = str(o.code)
            oc[1].text = str(o.name)

    if actor_codes and objective_codes:
        doc.add_heading("Matriu de postures", level=2)
        cols = 1 + len(objective_codes)
        pt = doc.add_table(rows=1, cols=cols)
        head = pt.rows[0].cells
        head[0].text = "Actor \\ Objectiu"
        for j, oc in enumerate(objective_codes):
            head[j + 1].text = str(oc)
        for i, ac in enumerate(actor_codes):
            prow = pt.add_row().cells
            prow[0].text = str(ac)
            row_vals = postures_matrix[i] if i < len(postures_matrix) else []
            for j in range(len(objective_codes)):
                prow[j + 1].text = str(row_vals[j] if j < len(row_vals) else "")

    if mactor_result:
        doc.add_heading("Agregats MACTOR", level=2)
        for lbl, fld in (
            ("Mobilització actors", mactor_result.mobilisation_actors),
            ("Mobilització objectius", mactor_result.mobilisation_objectives),
            ("Convergències", mactor_result.convergences_matrix),
        ):
            if fld is not None:
                doc.add_paragraph(lbl + ":")
                doc.add_paragraph(_json_block(fld))

    doc.add_heading("Anàlisi morfològic", level=1)
    if components:
        for c in components:
            doc.add_heading(f"{c.code} — {c.name}", level=2)
            cfgs = c.configurations or []
            if isinstance(cfgs, list):
                ct = doc.add_table(rows=1, cols=2)
                chr_ = ct.rows[0].cells
                chr_[0].text = "Etiqueta"
                chr_[1].text = "Descripció"
                for cfg in cfgs:
                    if isinstance(cfg, dict):
                        cr = ct.add_row().cells
                        cr[0].text = str(cfg.get("label", ""))
                        cr[1].text = str(cfg.get("desc", ""))
                    else:
                        cr = ct.add_row().cells
                        cr[0].text = str(cfg)
                        cr[1].text = ""
    else:
        doc.add_paragraph("Sense components.")

    incompat = bundle.get("incompatibilities") or []
    if incompat:
        doc.add_heading("Incompatibilitats morfològiques", level=2)
        _doc_table(
            doc,
            ["Component A", "Config A", "Component B", "Config B"],
            [[row.get("component_a", ""), row.get("config_a", ""), row.get("component_b", ""), row.get("config_b", "")] for row in incompat[:30]],
        )
    smic = bundle.get("smic") or {}
    if smic and smic.get("initial_probs"):
        doc.add_heading("SMIC · Probabilitats d'escenari", level=2)
        doc.add_paragraph(_json_block(smic))

    doc.add_heading("Escenaris", level=1)
    if scenarios_list:
        for s in scenarios_list:
            doc.add_heading(s.name, level=2)
            doc.add_paragraph(f"Tipus: {s.scenario_type or '—'}  · Probabilitat: {s.probability or '—'}")
            if s.morphological_config:
                doc.add_paragraph(str(s.morphological_config))
            doc.add_paragraph(s.narrative or "")
    else:
        doc.add_paragraph("Sense escenaris generats.")

    _append_qual_quant_docx(doc, bundle)


def _write_html_sync(bundle: dict[str, Any]) -> str:
    return _html_report(bundle)


async def export_html(
    db: AsyncSession,
    project_id: int,
    *,
    output_dir: str | Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """Export full report as standalone HTML (print to PDF from browser on Windows)."""
    bundle = await _load_project_bundle(db, project_id)
    if not bundle:
        raise ValueError(f"Prospective project {project_id} not found")

    directory = _ensure_reports_dir(output_dir)
    fname = filename or f"prospective_project_{project_id}.html"
    path = directory / fname
    html_str = await asyncio.to_thread(_write_html_sync, bundle)
    await asyncio.to_thread(path.write_text, html_str, encoding="utf-8")
    logger.info("Wrote prospective HTML export to %s", path)
    return {
        "file_path": str(path.resolve()),
        "format": "html",
        "project_id": project_id,
    }


def _write_docx_sync(bundle: dict[str, Any]) -> bytes:
    Document, _, _, _, _ = _load_docx()
    doc = Document()
    project: ProspectiveProject = bundle["project"]
    _add_doc_cover(doc, project)
    _populate_doc_body(doc, bundle)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def export_pdf(
    db: AsyncSession,
    project_id: int,
    *,
    output_dir: str | Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Export prospective project bundle to PDF. Returns metadata including absolute file_path.
    """
    bundle = await _load_project_bundle(db, project_id)
    if not bundle:
        raise ValueError(f"Prospective project {project_id} not found")

    directory = _ensure_reports_dir(output_dir)
    fname = filename or f"prospective_project_{project_id}.pdf"
    path = directory / fname

    await asyncio.to_thread(_write_pdf_sync, path, bundle)
    logger.info("Wrote prospective PDF export to %s", path)

    return {
        "file_path": str(path.resolve()),
        "format": "pdf",
        "project_id": project_id,
    }


async def export_docx(
    db: AsyncSession,
    project_id: int,
    *,
    output_dir: str | Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Export prospective project bundle to DOCX. Returns metadata including absolute file_path.
    """
    bundle = await _load_project_bundle(db, project_id)
    if not bundle:
        raise ValueError(f"Prospective project {project_id} not found")

    directory = _ensure_reports_dir(output_dir)
    fname = filename or f"prospective_project_{project_id}.docx"
    path = directory / fname

    data = await asyncio.to_thread(_write_docx_sync, bundle)
    await asyncio.to_thread(path.write_bytes, data)
    logger.info("Wrote prospective DOCX export to %s", path)

    return {
        "file_path": str(path.resolve()),
        "format": "docx",
        "project_id": project_id,
    }
