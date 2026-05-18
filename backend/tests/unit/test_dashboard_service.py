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
        assert "total_mentions" in result
        assert "change_percent" in result
    
    async def test_get_sentiment_score(self, db_session):
        """Test getting sentiment score"""
        service = DashboardService(db_session)
        
        result = await service.get_sentiment_score(days=7)
        
        assert isinstance(result, dict)
        assert "sentiment_score" in result
    
    async def test_get_critical_alerts(self, db_session):
        """Test getting critical alerts"""
        service = DashboardService(db_session)
        
        result = await service.get_critical_alerts(days=7)
        
        assert isinstance(result, dict)
    
    async def test_get_all_metrics(self, db_session):
        """Test getting all metrics"""
        service = DashboardService(db_session)
        
        result = await service.get_all_metrics(days=7)
        
        assert isinstance(result, dict)
        assert "total_mentions" in result
        assert "sentiment_score" in result
        assert "critical_alerts" in result



