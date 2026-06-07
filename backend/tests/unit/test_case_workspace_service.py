"""Tests for case workspace aggregation."""
import pytest

from services.case_workspace_service import load_case_workspace


@pytest.mark.asyncio
async def test_load_case_workspace(db_session, sample_case):
    ws = await load_case_workspace(db_session, sample_case.id)
    assert ws["found"] is True
    assert ws["case"]["id"] == sample_case.id
    assert "pipeline" in ws
    assert "projects" in ws
    assert "inquiries" in ws
    assert "financial_reports" in ws
    assert "company_registry" in ws
    assert "summary" in ws["company_registry"]


@pytest.mark.asyncio
async def test_load_case_workspace_not_found(db_session):
    ws = await load_case_workspace(db_session, 999999)
    assert ws["found"] is False
