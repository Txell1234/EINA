"""
Unit tests for ReportService export paths
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.export_backends import ExportBackendError
from services.report_service import ReportService

SAMPLE_DATA = {
    "case": {"id": 1, "name": "Test", "description": "Desc"},
    "osint_data": [],
    "ai_analyses": [],
    "qualitative_analyses": [],
    "predictions": [],
    "investment_recommendations": [],
    "premises": [],
    "bias_guidance": {"enabled": False, "premise_count": 0, "notes": []},
}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_excel_produces_xlsx(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = ReportService(MagicMock())
    meta = await service._generate_excel(1, SAMPLE_DATA)

    assert meta["status"] == "completed"
    assert meta["format"] == "excel"
    path = Path(meta["file_path"])
    assert path.suffix == ".xlsx"
    assert path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_excel_fallback_when_openpyxl_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = ReportService(MagicMock())

    with patch(
        "services.report_service.write_case_report_excel",
        side_effect=Exception("openpyxl broken"),
    ):
        meta = await service._generate_excel(99, SAMPLE_DATA)

    assert meta["status"] == "fallback_json"
    assert Path(meta["file_path"]).exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_pdf_fallback_when_weasyprint_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = ReportService(MagicMock())

    with patch(
        "services.report_service.render_pdf_from_html",
        side_effect=ExportBackendError("weasyprint", "native_libs missing"),
    ):
        meta = await service._generate_pdf(1, SAMPLE_DATA)

    assert meta["status"] == "fallback_json"
    assert Path(meta["file_path"]).suffix == ".json"
