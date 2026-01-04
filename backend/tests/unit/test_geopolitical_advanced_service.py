"""
Unit tests for GeopoliticalAdvancedService
"""
import pytest
from services.geopolitical_advanced_service import GeopoliticalAdvancedService


@pytest.mark.unit
class TestGeopoliticalAdvancedService:
    """Test suite for GeopoliticalAdvancedService"""
    
    async def test_analyze_supply_chain_risks(self, db_session, sample_case):
        """Test supply chain risk analysis"""
        service = GeopoliticalAdvancedService(db_session)
        
        result = await service.analyze_supply_chain_risks(
            country="China",
            industry="Electronics",
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "risk_id" in result
        assert "dependency_score" in result
        assert "vulnerability_factors" in result
        assert result["dependency_score"] >= 0.0
        assert result["dependency_score"] <= 100.0
    
    async def test_calculate_economic_interdependence(self, db_session, sample_case):
        """Test economic interdependence calculation"""
        service = GeopoliticalAdvancedService(db_session)
        
        result = await service.calculate_economic_interdependence(
            country1="USA",
            country2="China",
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "interdependence_id" in result
        assert "trade_volume" in result
        assert "dependency_ratio" in result
        assert "sectors" in result
    
    async def test_generate_scenario_analysis(self, db_session, sample_case):
        """Test scenario analysis generation"""
        service = GeopoliticalAdvancedService(db_session)
        
        result = await service.generate_scenario_analysis(
            case_id=sample_case.id,
            countries=["USA", "China"],
            time_horizon="12_months"
        )
        
        assert "error" not in result
        assert "scenarios" in result
        assert "countries" in result
        assert "time_horizon" in result
        assert "best_case" in result["scenarios"]
        assert "worst_case" in result["scenarios"]
        assert "base_case" in result["scenarios"]
    
    async def test_assess_regulatory_risk(self, db_session, sample_case):
        """Test regulatory risk assessment"""
        service = GeopoliticalAdvancedService(db_session)
        
        result = await service.assess_regulatory_risk(
            country="USA",
            industry="Technology",
            case_id=sample_case.id
        )
        
        assert "error" not in result
        assert "country" in result
        assert "regulatory_risk" in result



