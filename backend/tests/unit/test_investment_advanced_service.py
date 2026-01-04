"""
Unit tests for InvestmentAdvancedService
"""
import pytest
from services.investment_advanced_service import InvestmentAdvancedService


@pytest.mark.unit
class TestInvestmentAdvancedService:
    """Test suite for InvestmentAdvancedService"""
    
    async def test_analyze_esg_factors(self, db_session, sample_case):
        """Test ESG factors analysis"""
        service = InvestmentAdvancedService(db_session)
        
        result = await service.analyze_esg_factors(
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "esg_score" in result
        assert "environmental_score" in result
        assert "social_score" in result
        assert "governance_score" in result
        assert result["esg_score"] >= 0.0
        assert result["esg_score"] <= 100.0
    
    async def test_assess_regulatory_risk(self, db_session, sample_case):
        """Test regulatory risk assessment"""
        service = InvestmentAdvancedService(db_session)
        
        result = await service.assess_regulatory_risk(
            case_id=sample_case.id,
            country="USA"
        )
        
        assert "error" not in result
        assert "regulatory_risk" in result
        assert "recommendation" in result
    
    async def test_compare_market_opportunities(self, db_session, sample_case):
        """Test market opportunities comparison"""
        service = InvestmentAdvancedService(db_session)
        
        result = await service.compare_market_opportunities(
            case_id=sample_case.id,
            countries=["USA", "China"]
        )
        
        assert "error" not in result
        assert "opportunities" in result
        assert "comparison_date" in result
        assert isinstance(result["opportunities"], list)
    
    async def test_calculate_geopolitical_impact_on_investments(self, db_session, sample_case):
        """Test geopolitical impact calculation on investments"""
        service = InvestmentAdvancedService(db_session)
        
        result = await service.calculate_geopolitical_impact_on_investments(
            case_id=sample_case.id,
            countries=["USA"],
            investment_type="general",
            fetch_fresh_data=False
        )
        
        assert "error" not in result
        assert "impacts" in result
        assert "overall_assessment" in result
        assert "investment_type" in result



