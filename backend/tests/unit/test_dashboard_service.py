"""
Unit tests for DashboardService
"""
import pytest
from services.dashboard_service import DashboardService


@pytest.mark.unit
class TestDashboardService:
    """Test suite for DashboardService"""
    
    async def test_get_total_mentions(self, db_session):
        """Test getting total mentions"""
        service = DashboardService(db_session)
        
        result = await service.get_total_mentions(days=7)
        
        assert isinstance(result, dict)
        assert "total" in result
        assert "period_days" in result
    
    async def test_get_sentiment_score(self, db_session):
        """Test getting sentiment score"""
        service = DashboardService(db_session)
        
        result = await service.get_sentiment_score(days=7)
        
        assert isinstance(result, dict)
        assert "average" in result
        assert "period_days" in result
    
    async def test_get_advanced_metrics(self, db_session):
        """Test getting advanced metrics"""
        service = DashboardService(db_session)
        
        result = await service.get_advanced_metrics(days=7)
        
        assert isinstance(result, dict)
        # May contain reputation_risk_index, geopolitical_risk_index, etc.
    
    async def test_get_all_metrics(self, db_session):
        """Test getting all metrics"""
        service = DashboardService(db_session)
        
        result = await service.get_all_metrics(days=7)
        
        assert isinstance(result, dict)
        assert "total_mentions" in result
        assert "sentiment_score" in result
        assert "advanced_metrics" in result



