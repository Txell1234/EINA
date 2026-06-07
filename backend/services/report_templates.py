"""Report export visual templates — EINA, Intelligence Unit, Economist, Graphics."""
from __future__ import annotations

from typing import Any

DEFAULT_TEMPLATE = "eina"

REPORT_TEMPLATES: dict[str, dict[str, Any]] = {
    "eina": {
        "id": "eina",
        "label": "EINA Intelligence",
        "label_ca": "EINA Intelligence",
        "description": "Marca EINA: blau marí, accent taronja, capçalera institucional amb gràfics.",
        "badge": "EINA · OSINT Platform",
        "accent": "#ff6b35",
        "primary": "#1e3a5f",
    },
    "intelligence": {
        "id": "intelligence",
        "label": "Intelligence Unit Brief",
        "label_ca": "Unitat d'Intel·ligència",
        "description": "Briefing classificat: fons fosc, monospace, banda vermella, diagrama pipeline.",
        "badge": "INTEL BRIEF · RESTRICTED",
        "accent": "#f85149",
        "primary": "#58a6ff",
    },
    "economist": {
        "id": "economist",
        "label": "The Economist Style",
        "label_ca": "Estil The Economist",
        "description": "Revista editorial: serif, banda vermella, pull-quotes, layout columnes.",
        "badge": "Special Report",
        "accent": "#e3120b",
        "primary": "#1a1a1a",
    },
    "graphics": {
        "id": "graphics",
        "label": "Graphics & Data",
        "label_ca": "Gràfics i dades",
        "description": "Dashboard visual: KPIs, barres SVG, targetes d'escenaris, gradient header.",
        "badge": "Data Intelligence",
        "accent": "#6366f1",
        "primary": "#0ea5e9",
    },
}


def normalize_template(key: str | None) -> str:
    k = (key or DEFAULT_TEMPLATE).strip().lower()
    return k if k in REPORT_TEMPLATES else DEFAULT_TEMPLATE


def normalize_report_variant(key: str | None) -> str:
    """full = methodology + annexes; analytical = EIU-style outlook brief."""
    k = (key or "full").strip().lower()
    if k in ("analytical", "analitic", "analitico", "analysis", "brief", "outlook"):
        return "analytical"
    return "full"


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": meta["id"],
            "label": meta["label"],
            "label_ca": meta["label_ca"],
            "description": meta["description"],
            "accent": meta["accent"],
            "primary": meta["primary"],
        }
        for meta in REPORT_TEMPLATES.values()
    ]


def _base_css() -> str:
    return """
    @page { size: A4; margin: 14mm 12mm; }
    * { box-sizing: border-box; }
    body { margin: 0; line-height: 1.5; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    h1, h2, h3 { margin-top: 1.1em; margin-bottom: 0.5em; }
    h2 { page-break-after: avoid; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; }
    th, td { padding: 8px 10px; text-align: left; vertical-align: top; }
    .muted { opacity: 0.78; font-size: 0.88em; }
    .section-lead { font-size: 0.95em; margin: 8px 0; }

    /* Cover */
    .report-cover { page-break-after: always; padding: 28px 0 20px; min-height: 220px; }
    .cover-brand { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; }
    .cover-logo { flex-shrink: 0; }
    .cover-brand-text { flex: 1; min-width: 200px; }
    .cover-ring { flex-shrink: 0; }
    .cover-possibility { margin-top: 16px; font-size: 1.1em; letter-spacing: 0.04em; }
    .cover-meta { margin-top: 8px; }

    /* Sections */
    .report-section { margin: 20px 0; padding: 16px 18px; border-radius: 10px; page-break-inside: avoid; }
    .executive-summary { margin: 16px 0; padding: 18px 20px; border-radius: 10px; }

    /* KPI & charts */
    .kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 14px 0; }
    .kpi { flex: 1; min-width: 130px; padding: 14px 16px; border-radius: 10px; }
    .kpi strong { display: block; font-size: 1.55em; margin-top: 4px; }
    .prob-bar { height: 10px; border-radius: 5px; background: #e5e7eb; margin: 8px 0 16px; overflow: hidden; }
    .prob-fill { height: 100%; border-radius: 5px; transition: width 0.3s; }
    .prob-ring { display: block; }
    .dashboard-grid { display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0; }
    .dash-card { flex: 1; min-width: 90px; padding: 12px; border-radius: 8px; text-align: center; }
    .dash-card strong { display: block; font-size: 1.4em; }
    .dash-label { font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.8; }
    .mini-bar-chart { max-width: 320px; margin: 8px 0; }

    /* Godet pipeline */
    .godet-pipeline-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0; }
    .godet-step { padding: 8px 10px; border-radius: 8px; font-size: 0.85em; display: flex; gap: 6px; align-items: center; }
    .godet-step__mark { font-weight: 700; }
    .godet-wizard-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 8px; }
    .godet-wizard-step { padding: 6px 8px; border-radius: 6px; font-size: 0.78em; text-align: center; }

    /* Morph cards */
    .morph-card-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .morph-card { padding: 12px 14px; border-radius: 10px; page-break-inside: avoid; }
    .morph-card h3 { margin: 0 0 6px; font-size: 1em; }
    .morph-config { margin: 0 0 8px; font-size: 0.88em; opacity: 0.85; }
    .morph-possibility { font-size: 0.8em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Conclusions */
    .pullquote { margin: 16px 0; padding: 14px 18px; border-radius: 8px; font-size: 1.15em; font-style: italic; }
    .conclusion-list li { margin-bottom: 6px; }
    .reason-list { font-size: 0.92em; }

    /* Footer */
    .report-footer { margin-top: 32px; padding-top: 16px; border-top: 2px solid; text-align: center; }
    .footer-brand { font-weight: 700; letter-spacing: 0.06em; font-size: 0.9em; margin-bottom: 4px; }

    ul { padding-left: 1.25rem; }

    /* LLM narrative prose */
    .report-narrative { margin: 12px 0 18px; }
    .report-prose { margin: 0 0 10px; line-height: 1.62; }
    .report-prose strong { font-weight: 700; letter-spacing: 0.01em; }
    .report-list { margin: 8px 0 14px 1.4rem; padding-left: 0.5rem; }
    .report-list li { margin-bottom: 6px; line-height: 1.55; }
    .report-list--numbered { list-style-type: decimal; }

    /* EIU-style outlook (Godet analytical report) */
    .outlook-report { margin: 20px 0 28px 0; }
    .outlook-theme { font-size: 13pt; font-weight: 600; color: #334155; margin: 0 0 16px 0; line-height: 1.45; }
    .outlook-toc { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; }
    .outlook-toc ol { margin: 8px 0 0 1.2rem; }
    .outlook-block { margin: 24px 0; page-break-inside: avoid; }
    .outlook-block h2 { font-size: 14pt; margin-bottom: 10px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; border-left: none; padding-left: 0; }
    .outlook-block--watch h2 { border-color: #1e3a5f; }
    .outlook-block--risk h2 { border-color: #c62828; }
    .outlook-block--opp h2 { border-color: #2e7d32; }
    .outlook-block--scenarios h2 { border-color: #6366f1; }
    .outlook-bullets li { margin-bottom: 8px; line-height: 1.5; }
    .outlook-prose p { margin: 0 0 10px 0; line-height: 1.55; text-align: justify; }
    .outlook-scenario-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
    .outlook-scenario-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; background: #fff; page-break-inside: avoid; }
    .outlook-scenario-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
    .outlook-scenario-head h4 { margin: 0; font-size: 11pt; }
    .outlook-likelihood { font-weight: 700; color: #1e3a5f; white-space: nowrap; }
    .outlook-likelihood-bar { height: 6px; background: #e2e8f0; border-radius: 3px; margin: 8px 0; overflow: hidden; }
    .outlook-likelihood-bar span { display: block; height: 100%; background: linear-gradient(90deg, #1e3a5f, #6366f1); border-radius: 3px; }
    .outlook-source { font-size: 8.5pt; margin-top: 8px; }

    /* Case-driven actor map */
    .actor-map-section { margin: 28px 0; page-break-inside: avoid; }
    .actor-map-section h2 { font-size: 14pt; margin-bottom: 6px; border-left: none; padding-left: 0; border-bottom: 2px solid #1e3a5f; padding-bottom: 6px; }
    .actor-map-lead { color: #64748b; font-size: 10pt; margin: 0 0 8px 0; }
    .actor-map-focus { font-size: 10pt; color: #334155; margin: 0 0 16px 0; padding: 10px 12px; background: #f8fafc; border-left: 4px solid #ff6b35; border-radius: 0 6px 6px 0; }
    .actor-map-layout { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }
    .actor-map-visual { flex: 1 1 320px; min-width: 280px; max-width: 480px; }
    .actor-map-svg { display: block; width: 100%; height: auto; background: #f1f5f9; border-radius: 8px; border: 1px solid #e2e8f0; }
    .actor-map-region { stroke: #fff; stroke-width: 2; }
    .actor-map-actors { flex: 1 1 340px; display: flex; flex-direction: column; gap: 12px; }
    .actor-map-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 12px 14px; border-left: 5px solid var(--actor-accent, #1e3a5f);
      page-break-inside: avoid;
    }
    .actor-map-card h3 { margin: 0 0 4px 0; font-size: 11pt; color: #1e293b; }
    .actor-map-card .actor-meta { font-size: 8.5pt; color: #64748b; margin-bottom: 8px; }
    .actor-map-card ul { margin: 0; padding-left: 1.1rem; font-size: 9.5pt; line-height: 1.5; }
    .actor-map-card li { margin-bottom: 5px; }
    .actor-map-no-geo { font-size: 8.5pt; color: #94a3b8; font-style: italic; margin-top: 4px; }
    .actor-map-source { font-size: 8pt; color: #94a3b8; margin-top: 12px; width: 100%; }
    @media print { .actor-map-layout { flex-direction: column; } }
    """


_TEMPLATE_CSS: dict[str, str] = {
    "eina": """
    body { font-family: "Segoe UI", "DejaVu Sans", Helvetica, Arial, sans-serif; font-size: 10.5pt; color: #1a2332; max-width: 920px; margin: 0 auto; padding: 1.5rem; background: #fff; }
    .report-badge { color: #ff6b35; font-size: 9pt; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; display: block; margin-bottom: 6px; }
    .report-title { color: #1e3a5f; font-size: 24pt; margin: 0 0 8px; line-height: 1.2; font-weight: 700; }
    .report-sub { color: #4a5568; font-size: 12pt; margin: 0; }
    h2 { color: #1e3a5f; font-size: 13pt; border-left: 5px solid #ff6b35; padding-left: 12px; }
    .report-section { background: #f8fafc; border: 1px solid #e2e8f0; }
    .executive-summary { background: linear-gradient(135deg, #f8fafc 0%, #eef2f7 100%); border: 1px solid #cbd5e1; }
    .kpi { background: linear-gradient(135deg, #1e3a5f, #2d4a6f); color: #fff; }
    .kpi .muted { color: rgba(255,255,255,0.75); }
    .prob-fill { background: linear-gradient(90deg, #1e3a5f, #ff6b35); }
    th { background: #eef2f7; color: #1e3a5f; border: 1px solid #cbd5e1; font-weight: 600; }
    td { border: 1px solid #e2e8f0; }
    .godet-step { background: #fff; border: 1px solid #e2e8f0; }
    .godet-step--done { background: #ecfdf5; border-color: #6ee7b7; color: #065f46; }
    .godet-wizard-step { background: #1e3a5f; color: #fff; }
    .morph-card { background: #fff; border-left: 4px solid #ff6b35; box-shadow: 0 2px 8px rgba(30,58,95,0.08); }
    .morph-possibility { color: #ff6b35; }
    .dash-card { background: #1e3a5f; color: #fff; }
    .pullquote { background: #fff7ed; border-left: 4px solid #ff6b35; color: #1e3a5f; }
    .report-footer { border-color: #ff6b35; }
    .footer-brand { color: #1e3a5f; }
    """,
    "intelligence": """
    body { font-family: "Consolas", "Courier New", monospace; font-size: 10pt; color: #e8eaed; background: #0d1117; max-width: 900px; margin: 0 auto; padding: 1.5rem; }
    .report-badge { color: #f85149; font-size: 8pt; font-weight: 700; letter-spacing: 0.14em; display: block; }
    .report-title { color: #f0f6fc; font-size: 20pt; margin: 8px 0; font-family: "Segoe UI", sans-serif; }
    .report-sub { color: #8b949e; font-size: 10pt; }
    h2 { color: #58a6ff; font-size: 11pt; text-transform: uppercase; letter-spacing: 0.08em; border-bottom: 1px solid #30363d; padding-bottom: 6px; border-left: none; }
    .report-cover { border: 1px solid #30363d; border-left: 5px solid #f85149; padding: 20px; border-radius: 4px; background: #161b22; }
    .report-section { background: #161b22; border: 1px solid #30363d; }
    .executive-summary { background: #161b22; border: 1px solid #30363d; }
    .kpi { background: #21262d; border: 1px solid #30363d; color: #f0f6fc; }
    .prob-fill { background: #f85149; }
    th { background: #21262d; color: #58a6ff; border: 1px solid #30363d; }
    td { border: 1px solid #30363d; color: #c9d1d9; }
    .godet-step { background: #0d1117; border: 1px solid #30363d; }
    .godet-step--done { border-color: #238636; color: #3fb950; }
    .godet-wizard-step { background: #21262d; border: 1px solid #58a6ff; color: #58a6ff; }
    .morph-card { background: #0d1117; border: 1px solid #30363d; border-left: 3px solid #f85149; }
    .morph-possibility { color: #f85149; }
    .dash-card { background: #21262d; border: 1px solid #30363d; color: #f0f6fc; }
    .pullquote { background: #21262d; border-left: 3px solid #f85149; color: #f0f6fc; font-style: normal; }
    .report-footer { border-color: #f85149; }
    .footer-brand { color: #58a6ff; }
    .muted { color: #8b949e; }
    """,
    "economist": """
    body { font-family: Georgia, "Times New Roman", serif; font-size: 11pt; color: #1a1a1a; max-width: 800px; margin: 0 auto; padding: 1.5rem 1.8rem; background: #fff; }
    .report-cover { border-top: 8px solid #e3120b; padding-top: 20px; }
    .report-badge { color: #e3120b; font-size: 9pt; font-weight: 700; font-family: "Segoe UI", sans-serif; letter-spacing: 0.12em; text-transform: uppercase; display: block; }
    .report-title { font-size: 32pt; font-weight: 400; line-height: 1.12; margin: 12px 0; }
    .report-sub { font-style: italic; color: #555; font-size: 13pt; border-bottom: 1px solid #ccc; padding-bottom: 14px; }
    h2 { font-family: "Segoe UI", sans-serif; font-size: 12pt; color: #e3120b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; border-left: none; }
    .report-section { background: #faf9f7; border: none; border-top: 1px solid #e8e8e8; border-radius: 0; padding: 16px 0; }
    .executive-summary { background: #faf9f7; border-left: 4px solid #e3120b; font-size: 12pt; line-height: 1.6; }
    .kpi { background: #faf9f7; border: 1px solid #ddd; font-family: "Segoe UI", sans-serif; }
    .kpi strong { color: #e3120b; }
    .prob-fill { background: #e3120b; }
    th { background: #f5f5f5; border-bottom: 2px solid #e3120b; font-family: "Segoe UI", sans-serif; font-size: 9pt; text-transform: uppercase; }
    td { border-bottom: 1px solid #ddd; }
    .godet-step { background: #fff; border: 1px solid #e8e8e8; font-family: "Segoe UI", sans-serif; font-size: 0.8em; }
    .godet-step--done { border-color: #e3120b; }
    .godet-wizard-step { background: #1a1a1a; color: #fff; font-family: "Segoe UI", sans-serif; }
    .morph-card { background: #fff; border: 1px solid #e8e8e8; border-top: 3px solid #e3120b; }
    .morph-possibility { color: #e3120b; font-family: "Segoe UI", sans-serif; }
    .dash-card { background: #faf9f7; border: 1px solid #ddd; font-family: "Segoe UI", sans-serif; }
    .dash-card strong { color: #e3120b; }
    .pullquote { border-left: 4px solid #e3120b; padding-left: 20px; font-size: 1.25em; color: #333; background: transparent; }
    .report-footer { border-color: #e3120b; font-family: "Segoe UI", sans-serif; }
    """,
    "graphics": """
    body { font-family: "Segoe UI", system-ui, sans-serif; font-size: 10pt; color: #0f172a; max-width: 960px; margin: 0 auto; padding: 1rem; background: #e2e8f0; }
    .report-cover { background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 55%, #8b5cf6 100%); color: #fff; padding: 28px 32px; border-radius: 16px; margin-bottom: 20px; }
    .report-cover .report-badge, .report-cover .report-sub, .report-cover .muted { color: rgba(255,255,255,0.92); }
    .report-cover .report-title { color: #fff; font-size: 26pt; }
    .report-badge { font-size: 8pt; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.9; display: block; }
    .report-title { font-size: 22pt; font-weight: 800; margin: 8px 0; }
    h2 { color: #0f172a; font-size: 13pt; background: #fff; padding: 10px 14px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border-left: none; }
    .report-section { background: #fff; box-shadow: 0 4px 14px rgba(0,0,0,0.06); border: none; }
    .executive-summary { background: #fff; border-radius: 14px; box-shadow: 0 4px 14px rgba(0,0,0,0.06); }
    .kpi { background: linear-gradient(145deg, #fff, #f0f9ff); box-shadow: 0 3px 10px rgba(14,165,233,0.15); border: 1px solid #e0f2fe; }
    .kpi strong { color: #6366f1; font-size: 1.7em; }
    .prob-fill { background: linear-gradient(90deg, #0ea5e9, #6366f1, #8b5cf6); }
    th { background: linear-gradient(180deg, #e0f2fe, #bae6fd); color: #0369a1; border: none; font-weight: 700; }
    td { border-bottom: 1px solid #e2e8f0; background: #fff; }
    table { border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .godet-step { background: #f0f9ff; border: 1px solid #bae6fd; }
    .godet-step--done { background: #dcfce7; border-color: #86efac; color: #166534; }
    .godet-wizard-step { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; font-weight: 600; }
    .morph-card { background: #fff; border-radius: 12px; box-shadow: 0 3px 12px rgba(99,102,241,0.12); border-top: 4px solid #6366f1; }
    .morph-possibility { color: #6366f1; }
    .dash-card { background: linear-gradient(145deg, #0ea5e9, #0284c7); color: #fff; box-shadow: 0 3px 10px rgba(14,165,233,0.3); }
    .pullquote { background: linear-gradient(135deg, #f0f9ff, #ede9fe); border-radius: 12px; border: none; color: #4338ca; font-weight: 600; font-style: normal; }
    .report-footer { border-color: #6366f1; background: #fff; padding: 16px; border-radius: 10px; }
    .footer-brand { color: #6366f1; }
    """,
}


def get_report_css(template: str | None, *, report_type: str = "inquiry") -> str:
    _ = report_type
    key = normalize_template(template)
    return _base_css() + _TEMPLATE_CSS[key]


def report_header_html(
    template: str | None,
    *,
    title: str,
    subtitle: str = "",
    meta: str = "",
) -> str:
    """Legacy inline header — prefer build_cover_page from report_layout for exports."""
    key = normalize_template(template)
    badge = REPORT_TEMPLATES[key]["badge"]
    parts = [
        "<header class='report-header'>",
        f"<div class='report-badge'>{badge}</div>",
        f"<h1 class='report-title'>{title}</h1>",
    ]
    if subtitle:
        parts.append(f"<p class='report-sub'>{subtitle}</p>")
    if meta:
        parts.append(f"<p class='muted'>{meta}</p>")
    parts.append("</header>")
    return "\n".join(parts)


def probability_kpi_html(probability_pct: Any, possibility: str = "") -> str:
    try:
        pct = max(0, min(100, int(float(probability_pct or 0))))
    except (TypeError, ValueError):
        pct = 0
    return (
        "<div class='kpi-row'>"
        f"<div class='kpi'><span class='muted'>Probabilitat</span><strong>{pct}%</strong></div>"
        f"<div class='kpi'><span class='muted'>Possibilitat</span><strong>{possibility or '—'}</strong></div>"
        "</div>"
        f"<div class='prob-bar'><div class='prob-fill' style='width:{pct}%'></div></div>"
    )
