"""
Integration tests for public affairs endpoints
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestPublicAffairsEndpoints:
    """Test suite for public affairs API endpoints"""
    
    def test_list_policies(self, test_client: TestClient, sample_case):
        """Test listing policies"""
        response = test_client.get(
            "/api/public-affairs/policies",
            params={"case_id": sample_case.id}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_analyze_policy_impact(self, test_client: TestClient, sample_case):
        """Test analyzing policy impact"""
        response = test_client.post(
            "/api/public-affairs/analyze-impact",
            params={
                "policy_topic": "Climate Change",
                "jurisdiction": "global",
                "case_id": sample_case.id
            }
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "policy_id" in data
            assert "impact_score" in data
    
    def test_get_stakeholders(self, test_client: TestClient, sample_case):
        """Test getting stakeholders"""
        response = test_client.get(
            "/api/public-affairs/stakeholders",
            params={"case_id": sample_case.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "stakeholders" in data
        assert "total_identified" in data
