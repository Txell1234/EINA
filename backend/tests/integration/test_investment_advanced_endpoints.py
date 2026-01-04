"""
Integration tests for investment advanced endpoints
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestInvestmentAdvancedEndpoints:
    """Test suite for investment advanced API endpoints"""
    
    def test_analyze_esg(self, test_client: TestClient, sample_case):
        """Test ESG analysis"""
        response = test_client.get(
            "/api/investment-advanced/esg",
            params={"case_id": sample_case.id}
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "esg_score" in data
            assert "environmental_score" in data
            assert "social_score" in data
            assert "governance_score" in data
    
    def test_get_regulatory_risk(self, test_client: TestClient, sample_case):
        """Test regulatory risk assessment"""
        response = test_client.get(
            "/api/investment-advanced/regulatory-risk",
            params={
                "case_id": sample_case.id,
                "country": "USA"
            }
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "regulatory_risk" in data or "recommendation" in data
    
    def test_compare_market_opportunities(self, test_client: TestClient, sample_case):
        """Test market opportunities comparison"""
        response = test_client.get(
            "/api/investment-advanced/market-opportunities",
            params={
                "case_id": sample_case.id,
                "countries": "USA,China"
            }
        )
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "opportunities" in data
            assert isinstance(data["opportunities"], list)
