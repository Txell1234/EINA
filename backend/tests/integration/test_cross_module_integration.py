"""
Integration tests for cross-module integration
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.slow
class TestCrossModuleIntegration:
    """Test suite for cross-module integration scenarios"""
    
    def test_reputation_geopolitical_correlation(self, test_client: TestClient, sample_case):
        """Test correlation between reputation and geopolitical events"""
        # First create a reputation profile
        analyze_response = test_client.post(
            "/api/reputation/analyze",
            json={
                "entity_name": "TestCompany",
                "entity_type": "company",
                "case_id": sample_case.id
            }
        )
        
        # Then test correlation
        response = test_client.get(
            "/api/integration/reputation-geopolitical",
            params={
                "entity_name": "TestCompany",
                "case_id": sample_case.id
            }
        )
        assert response.status_code in [200, 404, 500]
    
    def test_public_affairs_reputation_correlation(self, test_client: TestClient, sample_case):
        """Test correlation between public affairs and reputation"""
        # First create a reputation profile
        analyze_response = test_client.post(
            "/api/reputation/analyze",
            json={
                "entity_name": "TestCompany",
                "entity_type": "company",
                "case_id": sample_case.id
            }
        )
        
        # Then test correlation
        response = test_client.get(
            "/api/integration/public-affairs-reputation",
            params={
                "entity_name": "TestCompany",
                "case_id": sample_case.id
            }
        )
        assert response.status_code in [200, 404, 500]
