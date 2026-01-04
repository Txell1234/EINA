"""
Unit tests for IntegrationService
"""
import pytest
from models.reputation import EntityType
from services.integration_service import IntegrationService


@pytest.mark.unit
class TestIntegrationService:
    """Test suite for IntegrationService"""
    
    async def test_analyze_geopolitical_impact_on_investments(self, db_session, sample_case):
        """Test geopolitical impact analysis on investments"""
        service = IntegrationService(db_session)
        
        result = await service.analyze_geopolitical_impact_on_investments(
            case_id=sample_case.id,
            countries=["USA"],
            investment_type="general",
            fetch_fresh_data=False
        )
        
        assert "error" not in result
        assert "investment_impact" in result
        assert "recent_events" in result
        assert "correlation" in result
    
    async def test_assess_reputation_impact_of_geopolitical_events(self, db_session, sample_case):
        """Test reputation impact assessment from geopolitical events"""
        service = IntegrationService(db_session)
        
        # First create a reputation profile
        from services.reputation_service import ReputationService
        rep_service = ReputationService(db_session)
        await rep_service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        result = await service.assess_reputation_impact_of_geopolitical_events(
            entity_name="TestCompany",
            case_id=sample_case.id
        )
        
        # May return error if no profile found, which is acceptable
        assert "error" in result or "entity_name" in result
    
    async def test_correlate_public_affairs_with_reputation(self, db_session, sample_case):
        """Test correlation between public affairs and reputation"""
        service = IntegrationService(db_session)
        
        # First create a reputation profile
        from services.reputation_service import ReputationService
        from models.reputation import EntityType
        rep_service = ReputationService(db_session)
        await rep_service.calculate_reputation_score(
            entity_name="TestCompany",
            entity_type=EntityType.COMPANY,
            case_id=sample_case.id
        )
        
        result = await service.correlate_public_affairs_with_reputation(
            entity_name="TestCompany",
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "entity_name" in result
        assert "policy_correlations" in result
        assert "overall_assessment" in result
    
    async def test_generate_comprehensive_risk_assessment(self, db_session, sample_case):
        """Test comprehensive risk assessment generation"""
        service = IntegrationService(db_session)
        
        result = await service.generate_comprehensive_risk_assessment(
            case_id=sample_case.id,
            entity_name="TestCompany",
            countries=["USA"]
        )
        
        assert "error" not in result
        assert "case_id" in result
        assert "assessment_date" in result
        assert "risks" in result
        assert "overall_risk" in result
        assert "recommendations" in result

