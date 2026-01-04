"""
Unit tests for PublicAffairsService
"""
import pytest
from services.public_affairs_service import PublicAffairsService


@pytest.mark.unit
class TestPublicAffairsService:
    """Test suite for PublicAffairsService"""
    
    async def test_analyze_policy_impact_creates_policy(self, db_session, sample_case):
        """Test that analyzing policy impact creates a policy analysis if it doesn't exist"""
        service = PublicAffairsService(db_session)
        
        result = await service.analyze_policy_impact(
            policy_topic="Climate Change",
            jurisdiction="global",
            case_id=sample_case.id,
            fetch_fresh_data=False
        )
        
        assert "error" not in result
        assert "policy_id" in result
        assert "impact_score" in result
        assert result["impact_score"] >= 0.0
        assert result["impact_score"] <= 100.0
    
    async def test_identify_stakeholders(self, db_session, sample_case):
        """Test stakeholder identification"""
        service = PublicAffairsService(db_session)
        
        result = await service.identify_stakeholders(
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "stakeholders" in result
        assert "total_identified" in result
        assert isinstance(result["stakeholders"], list)
    
    async def test_track_advocacy_opportunities(self, db_session, sample_case):
        """Test tracking advocacy opportunities"""
        service = PublicAffairsService(db_session)
        
        result = await service.track_advocacy_opportunities(
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "opportunities" in result
        assert "total" in result
        assert isinstance(result["opportunities"], list)
    
    async def test_measure_campaign_effectiveness_not_found(self, db_session):
        """Test measuring campaign effectiveness for non-existent campaign"""
        service = PublicAffairsService(db_session)
        
        result = await service.measure_campaign_effectiveness(campaign_id=99999)
        
        assert "error" in result
        assert result["error"] == "Campaign not found"



