"""
Unit tests for AIService analysis methods
"""
import pytest
from services.ai_service import AIService


@pytest.mark.unit
class TestAIService:
    """Test suite for AIService"""
    
    async def test_analyze_as_geopolitical_expert_no_client(self, db_session, sample_case):
        """Test geopolitical expert analysis when OpenAI is not configured"""
        service = AIService()
        service.client = None
        
        result = await service.analyze_as_geopolitical_expert(
            case_id=sample_case.id,
            osint_data=[],
            db=db_session
        )
        
        assert "error" in result
        assert result["error"] == "OpenAI not configured"
    
    async def test_analyze_as_investment_advisor_no_client(self, db_session, sample_case):
        """Test investment advisor analysis when OpenAI is not configured"""
        service = AIService()
        service.client = None
        
        result = await service.analyze_as_investment_advisor(
            case_id=sample_case.id,
            osint_data=[],
            db=db_session
        )
        
        assert "error" in result
        assert result["error"] == "OpenAI not configured"
    
    async def test_analyze_as_reputation_manager_no_client(self, db_session, sample_case):
        """Test reputation manager analysis when OpenAI is not configured"""
        service = AIService()
        service.client = None
        
        result = await service.analyze_as_reputation_manager(
            case_id=sample_case.id,
            osint_data=[],
            db=db_session
        )
        
        assert "error" in result
        assert result["error"] == "OpenAI not configured"
    
    async def test_analyze_as_public_affairs_consultant_no_client(self, db_session, sample_case):
        """Test public affairs consultant analysis when OpenAI is not configured"""
        service = AIService()
        service.client = None
        
        result = await service.analyze_as_public_affairs_consultant(
            case_id=sample_case.id,
            osint_data=[],
            db=db_session
        )
        
        assert "error" in result
        assert result["error"] == "OpenAI not configured"



