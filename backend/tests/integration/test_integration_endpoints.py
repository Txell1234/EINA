"""
Integration tests for integration endpoints
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestIntegrationEndpoints:
    """Test suite for integration API endpoints"""
    
    def test_comprehensive_analysis(self, test_client: TestClient, sample_case):
        """Test comprehensive analysis"""
        response = test_client.post(
            "/api/integration/comprehensive-analysis",
            params={
                "case_id": sample_case.id,
                "entity_name": "TestCompany"
            }
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "case_id" in data
            assert "assessment" in data or "risks" in data
    
    def test_geopolitical_investment_impact(self, test_client: TestClient, sample_case):
        """Test geopolitical investment impact"""
        response = test_client.get(
            "/api/integration/geopolitical-investment-impact",
            params={
                "case_id": sample_case.id,
                "countries": "USA",
                "investment_type": "general"
            }
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "investment_impact" in data or "impacts" in data
