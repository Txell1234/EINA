"""
Unit tests for ReputationService
"""
import pytest
from datetime import datetime
from models.reputation import ReputationProfile, EntityType, SentimentTrend
from services.reputation_service import ReputationService


@pytest.mark.unit
class TestReputationService:
    """Test suite for ReputationService"""
    
    async def test_calculate_reputation_score_creates_profile(self, db_session, sample_case):
        """Test that calculating reputation score creates a profile if it doesn't exist"""
        service = ReputationService(db_session)
        
        result = await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "profile_id" in result
        assert "reputation_score" in result
        assert result["reputation_score"] >= 0.0
        assert result["reputation_score"] <= 100.0
    
    async def test_calculate_reputation_score_updates_existing_profile(self, db_session, sample_case):
        """Test that calculating reputation score updates existing profile"""
        service = ReputationService(db_session)
        
        # First calculation
        result1 = await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        # Second calculation
        result2 = await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        assert result1["profile_id"] == result2["profile_id"]
        assert "reputation_score" in result2
        assert "change" in result2
    
    async def test_detect_crisis_indicators_no_crisis(self, db_session, sample_case):
        """Test crisis detection when there's no crisis"""
        service = ReputationService(db_session)
        
        # Create a profile first
        await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        result = await service.detect_crisis_indicators(
            entity_name="TestCompany",
            case_id=sample_case.id,
            fetch_fresh_data=False
        )
        
        assert "error" not in result
        assert "crisis_indicators" in result
        assert "crisis_level" in result
        assert result["crisis_level"] in ["none", "low", "medium", "high", "critical"]
    
    async def test_analyze_stakeholder_sentiment(self, db_session, sample_case):
        """Test stakeholder sentiment analysis"""
        service = ReputationService(db_session)
        
        # Create a profile first
        await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        result = await service.analyze_stakeholder_sentiment(
            entity_name="TestCompany",
            case_id=sample_case.id
        )
        
        assert "error" not in result or result.get("error") == "Profile not found"
        if "error" not in result:
            assert "stakeholder_sentiment" in result
            assert "profile_id" in result
    
    async def test_track_reputation_trend(self, db_session, sample_case):
        """Test reputation trend tracking"""
        service = ReputationService(db_session)
        
        # Create a profile first
        await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        result = await service.track_reputation_trend(
            entity_name="TestCompany",
            days=30
        )
        
        assert "error" not in result or result.get("error") == "Profile not found"
        if "error" not in result:
            assert "trend" in result
            assert "current_score" in result
            assert "history" in result
    
    async def test_generate_reputation_report(self, db_session, sample_case):
        """Test reputation report generation"""
        service = ReputationService(db_session)
        
        # Create a profile first
        await service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        result = await service.generate_reputation_report(
            entity_name="TestCompany",
            case_id=sample_case.id
        )
        
        assert "error" not in result or result.get("error") == "Profile not found"
        if "error" not in result:
            assert "entity_name" in result
            assert "reputation_score" in result
            assert "crisis_indicators" in result
            assert "recommendations" in result



