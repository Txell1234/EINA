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

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.export_backends import ExportBackendError, render_pdf_from_html

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

PRIMARY_RGB = RGBColor(0x1E, 0x3A, 0x5F)


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

    return {
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
    }


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

    parts.append("<h1>Variables (MIC-MAC)</h1>")
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

    return "<html><meta charset='utf-8'><body>" + "".join(parts) + "</body></html>"


def _write_pdf_sync(path: Path, bundle: dict[str, Any]) -> None:
    html_str = _html_report(bundle)
    try:
        render_pdf_from_html(html_str, path, base_url=str(path.parent.resolve()))
    except ExportBackendError as exc:
        raise RuntimeError(str(exc)) from exc


def _add_doc_cover(doc: Document, project: ProspectiveProject) -> None:
    """
    DOCX cover: iterate (text, size, grey_rgb) tuples only — add paragraph per row.
    (Avoid unpacking a nonexistent `paragraph` tuple element from fixed triples.)
    """
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


def _populate_doc_body(doc: Document, bundle: dict[str, Any]) -> None:
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

    h = doc.add_heading("Projecte", level=1)
    h.runs[0].font.color.rgb = PRIMARY_RGB
    doc.add_paragraph(project.hypothesis or "")
    doc.add_heading("Context", level=2)
    doc.add_paragraph(project.context or "")

    doc.add_heading("Variables (MIC-MAC)", level=1)
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
        p = doc.add_paragraph()
        p.add_run("Sectors i matrius MIC-MAC (JSON):")
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


def _write_docx_sync(bundle: dict[str, Any]) -> bytes:
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
