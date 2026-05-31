"""Integration tests for case INTSUM digest endpoint."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestIntsumEndpoint:
    def test_intsum_returns_digest(self, test_client: TestClient, sample_case):
        r = test_client.get(f"/api/cases/{sample_case.id}/intsum?days=7")
        assert r.status_code == 200
        data = r.json()
        assert data["found"] is True
        assert data["case_id"] == sample_case.id
        assert "summary" in data
        assert "alerts" in data
        assert "statements" in data
        assert "has_activity" in data
        assert data["days"] == 7

    def test_intsum_not_found(self, test_client: TestClient):
        r = test_client.get("/api/cases/999999/intsum")
        assert r.status_code == 404

    def test_intsum_days_bounds(self, test_client: TestClient, sample_case):
        r = test_client.get(f"/api/cases/{sample_case.id}/intsum?days=0")
        assert r.status_code == 422
        r2 = test_client.get(f"/api/cases/{sample_case.id}/intsum?days=30")
        assert r2.status_code == 200
        assert r2.json()["days"] == 30
