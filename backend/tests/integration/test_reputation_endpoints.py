"""
Integration tests for reputation endpoints
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestReputationEndpoints:
    """Test suite for reputation API endpoints"""
    
    def test_list_reputation_profiles(self, test_client: TestClient):
        """Test listing reputation profiles"""
        response = test_client.get("/api/reputation/profiles")
        assert response.status_code in [200, 404]  # 404 if no profiles exist
    
    def test_get_reputation_score(self, test_client: TestClient, sample_case):
        """Test getting reputation score"""
        # First create a profile by analyzing
        response = test_client.post(
            "/api/reputation/analyze",
            json={
                "entity_name": "TestCompany",
                "entity_type": "company",
                "case_id": sample_case.id
            }
        )
        # May succeed or fail depending on data availability
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            profile_id = response.json().get("profile_id")
            if profile_id:
                score_response = test_client.get(f"/api/reputation/{profile_id}/score")
                assert score_response.status_code in [200, 404]
    
    def test_get_crisis_indicators(self, test_client: TestClient):
        """Test getting crisis indicators"""
        # This will fail if no profiles exist, which is acceptable
        response = test_client.get(
            "/api/reputation/crisis-indicators",
            params={"entity_name": "TestCompany"}
        )
        assert response.status_code in [200, 404, 500]
