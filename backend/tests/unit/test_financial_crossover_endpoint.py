"""Integration tests for financial report upload and crossover endpoints."""
import pytest


PRAAMS_SAMPLE = """
Return factors:
Growth: 6/7
Valuation: 5/7
Risk factors:
Geopolitical: 4/7
Recommendation: BUY
"""


@pytest.mark.unit
def test_financial_reports_flow(test_client, sample_case):
    case_id = sample_case.id

    listed = test_client.get(f"/api/cases/{case_id}/financial-reports")
    assert listed.status_code == 200
    assert listed.json() == []

    uploaded = test_client.post(
        f"/api/cases/{case_id}/financial-reports",
        json={"text": PRAAMS_SAMPLE, "source": "praams", "title": "Test"},
    )
    assert uploaded.status_code == 200
    report_id = uploaded.json()["report_id"]
    assert report_id > 0

    listed2 = test_client.get(f"/api/cases/{case_id}/financial-reports")
    assert len(listed2.json()) == 1

    crossover = test_client.post(
        f"/api/cases/{case_id}/financial-crossover",
        json={"report_id": report_id, "external_weight": 0.35},
    )
    assert crossover.status_code == 200
    body = crossover.json()
    assert body["found"] is True
    assert "crossover" in body
    assert body["crossover"]["final_numbers"]["external_return_index"] is not None
