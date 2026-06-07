from services.report_layout import (
    build_cover_page,
    build_godet_pipeline_html,
    build_morph_cards_html,
    svg_probability_ring,
)


def test_cover_page_contains_title():
    html = build_cover_page("eina", title="Test Informe", subtitle="Pregunta?", meta="meta")
    assert "Test Informe" in html
    assert "report-cover" in html


def test_godet_pipeline_renders_steps():
    html = build_godet_pipeline_html([{"step": "osint", "ok": True}], template="eina")
    assert "godet-pipeline" in html
    assert "OSINT" in html


def test_morph_cards():
    html = build_morph_cards_html(
        [{"name": "Escenari A", "config": "X+Y", "possibility": "PLAUSIBLE"}],
        template="graphics",
    )
    assert "Escenari A" in html
    assert "morph-card" in html


def test_svg_ring():
    assert "68%" in svg_probability_ring(68)
