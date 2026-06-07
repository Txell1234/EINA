"""Rich HTML layout blocks for styled report exports (SVG charts, covers, Godet pipeline)."""
from __future__ import annotations

import html
import math
from typing import Any

from services.report_markdown import format_report_line_html
from services.report_templates import REPORT_TEMPLATES, normalize_template

GODET_STEPS = [
    ("parse", "Parse pregunta"),
    ("osint", "OSINT"),
    ("intelligence", "Intel·ligència"),
    ("policy", "Policy-Industry"),
    ("financial", "Financer"),
    ("morph_bootstrap", "Morph/Zwicky"),
    ("monitors", "Monitors"),
    ("synthesis", "Síntesi"),
]


def _esc(s: Any) -> str:
    return html.escape(str(s) if s is not None else "")


def svg_probability_ring(pct: int, *, accent: str = "#ff6b35", track: str = "#e2e8f0") -> str:
    pct = max(0, min(100, pct))
    r = 42
    c = 2 * math.pi * r
    dash = c * pct / 100
    return f"""
    <svg class="prob-ring" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
      <circle cx="60" cy="60" r="{r}" fill="none" stroke="{track}" stroke-width="10"/>
      <circle cx="60" cy="60" r="{r}" fill="none" stroke="{accent}" stroke-width="10"
        stroke-dasharray="{dash} {c}" stroke-linecap="round"
        transform="rotate(-90 60 60)"/>
      <text x="60" y="56" text-anchor="middle" font-size="22" font-weight="700" fill="currentColor">{pct}%</text>
      <text x="60" y="74" text-anchor="middle" font-size="9" fill="currentColor" opacity="0.7">PROB.</text>
    </svg>
    """


def svg_mini_bar_chart(values: list[tuple[str, float]], *, color: str = "#1e3a5f") -> str:
    if not values:
        return ""
    max_v = max(v for _, v in values) or 1
    bars = []
    for i, (label, val) in enumerate(values[:6]):
        h = max(4, int(60 * val / max_v))
        x = 10 + i * 48
        bars.append(
            f'<rect x="{x}" y="{70 - h}" width="32" height="{h}" rx="4" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + 16}" y="88" text-anchor="middle" font-size="7" fill="currentColor">{_esc(label[:8])}</text>'
            f'<text x="{x + 16}" y="{65 - h}" text-anchor="middle" font-size="8" font-weight="600" fill="currentColor">{int(val)}</text>'
        )
    return (
        '<svg class="mini-bar-chart" viewBox="0 0 300 95" width="100%" height="95" aria-hidden="true">'
        + "".join(bars)
        + "</svg>"
    )


def build_godet_pipeline_html(steps_log: list[dict[str, Any]], *, template: str) -> str:
    tpl = normalize_template(template)
    done_steps = {str(s.get("step")) for s in steps_log if s.get("ok")}
    cells = []
    for key, label in GODET_STEPS:
        ok = key in done_steps
        cls = "godet-step godet-step--done" if ok else "godet-step"
        mark = "✓" if ok else "○"
        cells.append(f'<div class="{cls}"><span class="godet-step__mark">{mark}</span><span>{_esc(label)}</span></div>')
    wizard_steps = [
        ("Projecte", "project"),
        ("Variables", "variables"),
        ("MIC-MAC", "micmac"),
        ("Actors", "actors"),
        ("MACTOR", "mactor"),
        ("Morph", "morph"),
        ("SMIC", "smic"),
        ("Escenaris", "scenarios"),
    ]
    wizard_cells = "".join(
        f'<div class="godet-wizard-step"><span>{_esc(lbl)}</span></div>' for lbl, _ in wizard_steps
    )
    return f"""
    <section class="report-section godet-pipeline-section">
      <h2>Pipeline Q2FS · Godet</h2>
      <div class="godet-pipeline-grid">{"".join(cells)}</div>
      <p class="section-lead">Wizard prospectiu (completa per síntesi full):</p>
      <div class="godet-wizard-grid">{wizard_cells}</div>
      <p class="muted tpl-{tpl}">Mode full: la síntesi final requereix MIC-MAC, MACTOR, Morph i escenaris Godet.</p>
    </section>
    """


def build_cover_page(
    template: str | None,
    *,
    title: str,
    subtitle: str = "",
    meta: str = "",
    probability_pct: int | None = None,
    possibility: str = "",
) -> str:
    tpl = normalize_template(template)
    meta_info = REPORT_TEMPLATES[tpl]
    accent = {
        "eina": "#ff6b35",
        "intelligence": "#f85149",
        "economist": "#e3120b",
        "graphics": "#6366f1",
    }.get(tpl, "#ff6b35")
    ring = ""
    if probability_pct is not None:
        ring = f'<div class="cover-ring">{svg_probability_ring(probability_pct, accent=accent)}</div>'
    return f"""
    <section class="report-cover tpl-{tpl}">
      <div class="cover-brand">
        <div class="cover-logo" aria-hidden="true">
          <svg viewBox="0 0 64 64" width="56" height="56">
            <rect x="4" y="4" width="56" height="56" rx="12" fill="{accent}" opacity="0.15"/>
            <path d="M18 44 L32 16 L46 44 Z" fill="none" stroke="{accent}" stroke-width="3"/>
            <circle cx="32" cy="38" r="4" fill="{accent}"/>
          </svg>
        </div>
        <div class="cover-brand-text">
          <span class="report-badge">{_esc(meta_info["badge"])}</span>
          <h1 class="report-title">{title}</h1>
          {f'<p class="report-sub">{subtitle}</p>' if subtitle else ''}
          {f'<p class="muted cover-meta">{meta}</p>' if meta else ''}
        </div>
        {ring}
      </div>
      {f'<div class="cover-possibility"><strong>{_esc(possibility)}</strong></div>' if possibility else ''}
    </section>
    """


def build_scope_dashboard(scope_audit: dict[str, Any], *, template: str) -> str:
    if not scope_audit:
        return ""
    kept = int(scope_audit.get("kept") or 0)
    removed = int(scope_audit.get("removed_topic") or 0) + int(scope_audit.get("removed_must_match") or 0)
    queries = int(scope_audit.get("queries_run") or 0)
    chart = svg_mini_bar_chart(
        [("Queries", float(queries)), ("OK", float(kept)), ("Out", float(removed))],
        color={"eina": "#1e3a5f", "intelligence": "#58a6ff", "economist": "#e3120b", "graphics": "#0ea5e9"}.get(
            normalize_template(template), "#1e3a5f"
        ),
    )
    return f"""
    <section class="report-section scope-dashboard">
      <h2>OSINT &amp; Scope</h2>
      <div class="dashboard-grid">
        <div class="dash-card"><span class="dash-label">Consultes</span><strong>{queries}</strong></div>
        <div class="dash-card"><span class="dash-label">Conservats</span><strong>{kept}</strong></div>
        <div class="dash-card"><span class="dash-label">Filtrats</span><strong>{removed}</strong></div>
      </div>
      {chart}
    </section>
    """


def build_morph_cards_html(rows: list[dict[str, Any]], *, template: str) -> str:
    if not rows:
        return ""
    cards = []
    for row in rows[:8]:
        cards.append(
            f"""<article class="morph-card">
              <h3>{_esc(row.get('name'))}</h3>
              <p class="morph-config">{_esc(row.get('config'))}</p>
              <span class="morph-possibility">{_esc(row.get('possibility'))}</span>
            </article>"""
        )
    return f"""
    <section class="report-section morph-section">
      <h2>Escenaris morfològics (Zwicky)</h2>
      <div class="morph-card-grid">{"".join(cards)}</div>
    </section>
    """


def build_conclusions_block(conclusions: list[str], reasoning: list[dict[str, Any]], *, template: str) -> str:
    tpl = normalize_template(template)
    pullquote = ""
    if conclusions:
        pullquote = f'<blockquote class="pullquote tpl-{tpl}">{format_report_line_html(conclusions[0])}</blockquote>'
    items = "".join(f"<li>{format_report_line_html(c)}</li>" for c in conclusions)
    reason_items = ""
    for r in reasoning[:5]:
        if isinstance(r, dict):
            reason_items += (
                f"<li><strong>{_esc(r.get('conclusion'))}</strong> — "
                f"{format_report_line_html(str(r.get('because') or ''))}</li>"
            )
    return f"""
    <section class="report-section conclusions-section">
      <h2>Conclusions &amp; raonament</h2>
      {pullquote}
      <ul class="conclusion-list">{items}</ul>
      {f'<h3>Traçabilitat</h3><ul class="reason-list">{reason_items}</ul>' if reason_items else ''}
    </section>
    """


def build_report_footer(template: str | None, *, generated_note: str) -> str:
    tpl = normalize_template(template)
    return f"""
    <footer class="report-footer tpl-{tpl}">
      <div class="footer-brand">EINA · Open Source Intelligence Platform</div>
      <p class="muted">{_esc(generated_note)} · Plantilla: {_esc(REPORT_TEMPLATES[tpl]['label'])}</p>
    </footer>
    """


def build_eiu_outlook_html(
    outlook: dict[str, Any],
    *,
    template: str,
    strings: Any,
) -> str:
    """EIU-style outlook body: TOC, what to watch, risks, opportunities, scenarios."""
    tpl = normalize_template(template)
    toc_items = "".join(
        f'<li><a href="#{_esc(item["id"])}">{_esc(item["label"])}</a></li>'
        for item in (outlook.get("toc") or [])
    )
    watch_items = "".join(f"<li>{format_report_line_html(b)}</li>" for b in outlook.get("what_to_watch") or [])
    risk_paras = "".join(f"<p>{format_report_line_html(p)}</p>" for p in outlook.get("key_risks") or [])
    opp_paras = "".join(f"<p>{format_report_line_html(p)}</p>" for p in outlook.get("key_opportunities") or [])

    scenario_cards = []
    for sc in outlook.get("scenarios") or []:
        pct = sc.get("likelihood_pct")
        bar_w = pct if isinstance(pct, int) else 0
        scenario_cards.append(
            f"""<article class="outlook-scenario-card">
              <div class="outlook-scenario-head">
                <h4>{_esc(sc.get('name'))}</h4>
                <span class="outlook-likelihood">{_esc(sc.get('likelihood_label', '—'))}</span>
              </div>
              <div class="outlook-likelihood-bar"><span style="width:{bar_w}%"></span></div>
              <p class="muted">{_esc(sc.get('type'))} · {_esc(sc.get('possibility'))}</p>
              {f'<p>{format_report_line_html(sc.get("excerpt", ""))}</p>' if sc.get("excerpt") else ''}
            </article>"""
        )

    theme = outlook.get("theme_subtitle") or ""
    return f"""
    <section class="outlook-report tpl-{tpl}">
      <p class="outlook-theme">{_esc(theme)}</p>
      <nav class="outlook-toc" aria-label="{_esc(strings.toc)}">
        <h2>{_esc(strings.toc)}</h2>
        <ol>{toc_items}</ol>
      </nav>
      <section class="outlook-block outlook-block--watch" id="what-to-watch">
        <h2>{_esc(strings.outlook_what_to_watch)}</h2>
        <ul class="outlook-bullets">{watch_items}</ul>
        <p class="outlook-source muted">{_esc(strings.outlook_source_note)}</p>
      </section>
      <section class="outlook-block outlook-block--risk" id="key-risks">
        <h2>{_esc(strings.outlook_key_risks)}</h2>
        <div class="outlook-prose">{risk_paras}</div>
      </section>
      <section class="outlook-block outlook-block--opp" id="key-opportunities">
        <h2>{_esc(strings.outlook_key_opportunities)}</h2>
        <div class="outlook-prose">{opp_paras}</div>
      </section>
      {f'<section class="outlook-block outlook-block--scenarios" id="scenarios-outlook"><h2>{_esc(strings.outlook_scenarios)}</h2><div class="outlook-scenario-grid">{"".join(scenario_cards)}</div></section>' if scenario_cards else ''}
    </section>
    """


def build_actor_map_html(
    actor_map: dict[str, Any],
    *,
    template: str,
    strings: Any,
) -> str:
    """Case-driven map: highlights only regions present in this project + actor cards."""
    if not actor_map.get("has_data"):
        return ""
    tpl = normalize_template(template)
    viewbox = actor_map.get("viewbox") or "0 0 900 650"
    paths_svg = []
    for region in actor_map.get("regions") or []:
        for d in region.get("paths") or []:
            paths_svg.append(
                f'<path class="actor-map-region" d="{d}" fill="{region["color"]}" '
                f'opacity="0.9" data-region="{_esc(region["id"])}"/>'
            )

    cards_html = []
    for co in actor_map.get("callouts") or []:
        bullets = "".join(f"<li>{format_report_line_html(b)}</li>" for b in co.get("bullets") or [])
        meta = co.get("meta") or ""
        meta_line = f'<p class="actor-meta">{_esc(meta)}</p>' if meta else ""
        no_geo = ""
        if not co.get("region_id"):
            no_geo = f'<p class="actor-map-no-geo">{_esc(strings.actor_map_no_geo)}</p>'
        cards_html.append(
            f"""<article class="actor-map-card" style="--actor-accent:{co.get('color', '#1e3a5f')}">
              <h3>{_esc(co.get('actor_name') or '—')}</h3>
              {meta_line}
              <ul>{bullets}</ul>
              {no_geo}
            </article>"""
        )

    focus = actor_map.get("case_focus") or ""
    focus_html = ""
    if focus:
        focus_html = (
            f'<p class="actor-map-focus"><strong>{_esc(strings.actor_map_case_focus)}:</strong> '
            f'{format_report_line_html(focus)}</p>'
        )

    map_col = ""
    if paths_svg:
        vb_parts = viewbox.split()
        if len(vb_parts) == 4:
            vx, vy, vw, vh = vb_parts
            bg_rect = f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="#eef2f7"/>'
        else:
            bg_rect = '<rect width="900" height="650" fill="#eef2f7"/>'
        map_col = f"""
        <div class="actor-map-visual">
          <svg class="actor-map-svg" viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{_esc(strings.actor_map_title)}">
            {bg_rect}
            {"".join(paths_svg)}
          </svg>
        </div>"""

    return f"""
    <section class="actor-map-section tpl-{tpl}" id="actor-map">
      <h2>{_esc(strings.actor_map_title)}</h2>
      <p class="actor-map-lead">{_esc(strings.actor_map_lead)}</p>
      {focus_html}
      <div class="actor-map-layout">
        {map_col}
        <div class="actor-map-actors">{"".join(cards_html)}</div>
      </div>
      <p class="actor-map-source muted">{_esc(strings.actor_map_source_note)}</p>
    </section>
    """

