from services.report_templates import (
    get_report_css,
    list_templates,
    normalize_template,
    probability_kpi_html,
)


def test_normalize_template_fallback():
    assert normalize_template("unknown") == "eina"
    assert normalize_template("economist") == "economist"


def test_list_templates_has_four_styles():
    ids = {t["id"] for t in list_templates()}
    assert ids == {"eina", "intelligence", "economist", "graphics"}


def test_get_report_css_includes_template_marker():
    css = get_report_css("intelligence")
    assert "Consolas" in css or "monospace" in css


def test_probability_kpi_html_renders_bar():
    html = probability_kpi_html(42, "PLAUSIBLE")
    assert "42%" in html
    assert "width:42%" in html
