"""
Integration tests for integration status endpoint
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import time


@pytest.mark.integration
class TestIntegrationStatus:
    """Test suite for integration status API endpoint"""
    
    def test_get_integration_status(self, test_client: TestClient):
        """Test getting integration status"""
        response = test_client.get("/api/integration/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check structure
        assert "ai" in data
        assert "osint_apis" in data
        assert "financial_apis" in data
        assert "geopolitical_apis" in data
        assert "external_tools" in data
        assert "summary" in data
        assert "cache_info" in data
        
        # Check AI section
        assert "llm" in data["ai"]
        assert "provider" in data["ai"]["llm"]
        assert "openai" in data["ai"]
        assert "configured" in data["ai"]["openai"]
        assert "status" in data["ai"]["openai"]
        assert "model" in data["ai"]["openai"]
        
        # Check summary
        assert "total_apis" in data["summary"]
        assert "configured_apis" in data["summary"]
        assert "not_configured_apis" in data["summary"]
        assert "critical_apis" in data["summary"]
        assert "alerts" in data["summary"]
        assert isinstance(data["summary"]["alerts"], list)
        
        # Check cache info
        assert "cached" in data["cache_info"]
        assert "cache_ttl_seconds" in data["cache_info"]
        assert data["cache_info"]["cache_ttl_seconds"] == 60
    
    def test_integration_status_structure(self, test_client: TestClient):
        """Test that integration status has correct structure"""
        response = test_client.get("/api/integration/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check OSINT APIs structure
        osint_apis = data["osint_apis"]
        expected_osint_apis = ["news_api", "github", "shodan", "ensembledata", "ipstack"]
        for api_name in expected_osint_apis:
            assert api_name in osint_apis
            assert "configured" in osint_apis[api_name]
            assert "status" in osint_apis[api_name]
        
        # Check Financial APIs structure
        financial_apis = data["financial_apis"]
        expected_financial_apis = ["alphavantage", "finnhub", "financial_modeling_prep"]
        for api_name in expected_financial_apis:
            assert api_name in financial_apis
            assert "configured" in financial_apis[api_name]
            assert "status" in financial_apis[api_name]
        
        # Check Geopolitical APIs structure
        geopolitical_apis = data["geopolitical_apis"]
        assert "permutable" in geopolitical_apis
        assert "configured" in geopolitical_apis["permutable"]
        assert "status" in geopolitical_apis["permutable"]
        
        # Check External Tools structure
        external_tools = data["external_tools"]
        expected_tools = ["sherlock", "recon-ng", "theharvester"]
        for tool_name in expected_tools:
            assert tool_name in external_tools
            assert "configured" in external_tools[tool_name]
            assert "status" in external_tools[tool_name]
    
    def test_integration_status_cache(self, test_client: TestClient):
        """Test that integration status is cached"""
        # First request
        response1 = test_client.get("/api/integration/status")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second request immediately (should use cache)
        response2 = test_client.get("/api/integration/status")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Cache info should indicate caching
        assert data2["cache_info"]["cached"] is True
        assert data2["cache_info"]["cache_age_seconds"] is not None
        assert data2["cache_info"]["cache_age_seconds"] < 1  # Should be very recent
    
    def test_refresh_integration_status(self, test_client: TestClient):
        """Test refreshing integration status cache"""
        # Get initial status
        response1 = test_client.get("/api/integration/status")
        assert response1.status_code == 200
        
        # Refresh cache
        refresh_response = test_client.post("/api/integration/status/refresh")
        assert refresh_response.status_code == 200
        
        refresh_data = refresh_response.json()
        assert "message" in refresh_data
        assert refresh_data["message"] == "Cache refreshed"
        assert "status" in refresh_data
        
        # Get status again (should be fresh)
        response2 = test_client.get("/api/integration/status")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cache_info"]["cache_age_seconds"] is not None
        assert data2["cache_info"]["cache_age_seconds"] < 1
    
    def test_critical_api_alerts(self, test_client: TestClient):
        """Test that critical API alerts are generated"""
        response = test_client.get("/api/integration/status")
        assert response.status_code == 200
        
        data = response.json()
        alerts = data["summary"]["alerts"]
        
        # Check alerts structure
        assert isinstance(alerts, list)
        
        # If LLM is not configured, there should be a critical alert
        if not data["summary"]["critical_apis"].get("llm"):
            llm_alert = next((a for a in alerts if a["api"] == "llm"), None)
            assert llm_alert is not None
            assert llm_alert["level"] == "critical"
            assert "message" in llm_alert
            assert "impact" in llm_alert

        # If OpenAI is not configured, there should be a warning (embeddings/classification)
        if not data["ai"]["openai"]["configured"]:
            openai_alert = next((a for a in alerts if a["api"] == "openai"), None)
            if openai_alert is not None:
                assert openai_alert["level"] == "warning"
                assert "message" in openai_alert
                assert "impact" in openai_alert
    
    def test_summary_counts(self, test_client: TestClient):
        """Test that summary counts are correct"""
        response = test_client.get("/api/integration/status")
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        
        # Count APIs manually
        all_apis = []
        for category in ["osint_apis", "financial_apis", "geopolitical_apis"]:
            for api_name, api_info in data[category].items():
                all_apis.append(api_info)
        
        # Verify counts match
        assert summary["total_apis"] == len(all_apis)
        assert summary["configured_apis"] == sum(1 for api in all_apis if api.get("configured", False))
        assert summary["not_configured_apis"] == summary["total_apis"] - summary["configured_apis"]
