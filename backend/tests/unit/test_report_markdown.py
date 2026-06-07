"""Tests for report_markdown formatting."""
from services.report_markdown import format_report_text_html


SAMPLE = """**Actors Impulsors:** Governs dels EUA (B) i Xina (C) com a principals impulsors.

**Indicadors d'Alerta:**
1. → Inici d'exercicis militars conjunts entre EUA, Japó i Corea del Sud.
2. → Declaracions conjuntes EUA-Xina sobre control d'armament.

**Possibilitat (viabilitat lògica Zwicky):** Condicional. L'espai morfològic permet aquest escenari.

**Probabilitat (likelihood SMIC/tendències):** Baixa. Actuals tendències indiquen transformacions radicals."""


def test_bold_converted_to_strong():
    html_out = format_report_text_html("**Actors Impulsors:** Text de prova.")
    assert "**" not in html_out
    assert "<strong>Actors Impulsors:</strong>" in html_out


def test_numbered_alert_list():
    html_out = format_report_text_html(SAMPLE)
    assert "<ol class=\"report-list" in html_out
    assert "<li>" in html_out
    assert "exercicis militars" in html_out
    assert "**" not in html_out


def test_header_before_numbered_list():
    block = "**Indicadors d'Alerta:**\n1. → Primer indicador.\n2. → Segon indicador."
    html_out = format_report_text_html(block)
    assert "<strong>Indicadors d" in html_out and "Alerta:</strong>" in html_out
    assert "<ol class=\"report-list" in html_out
    assert "**" not in html_out


def test_multiple_sections():
    html_out = format_report_text_html(SAMPLE)
    assert html_out.count("<p class=\"report-prose\">") >= 2
    assert "<strong>Possibilitat" in html_out
    assert "<strong>Probabilitat" in html_out
