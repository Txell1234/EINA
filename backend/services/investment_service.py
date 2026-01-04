"""
Investment Service - Generate investment recommendations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.investments import InvestmentRecommendation, RiskAnalysis, Opportunity, RecommendationType, RiskLevel
from services.ai_service import AIService
from integrations.alphavantage_api import AlphaVantageAPIService
from integrations.finnhub_api import FinnhubAPIService
from integrations.permutable_api import PermutableAPIService

class InvestmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.alphavantage = AlphaVantageAPIService()
        self.finnhub = FinnhubAPIService()
        self.permutable = PermutableAPIService()
    
    async def generate_recommendation(self, case_id: int) -> dict:
        """Generate investment recommendation with risk analysis"""
        # Get case data
        # TODO: Fetch case and related OSINT/AI data
        
        # Use AI to generate recommendation
        recommendation_data = await self.ai_service.generate_investment_recommendation(
            case_id=case_id
        )
        
        # Map recommendation type
        rec_type_str = recommendation_data.get("type", "hold").lower()
        rec_type_map = {
            "buy": RecommendationType.BUY,
            "sell": RecommendationType.SELL,
            "hold": RecommendationType.HOLD,
        }
        rec_type = rec_type_map.get(rec_type_str, RecommendationType.HOLD)
        
        # Create recommendation
        recommendation = InvestmentRecommendation(
            case_id=case_id,
            recommendation_type=rec_type,
            confidence_percentage=recommendation_data.get("confidence", 50.0),
            rationale=recommendation_data.get("rationale", "")
        )
        self.db.add(recommendation)
        await self.db.commit()
        await self.db.refresh(recommendation)
        
        # Create risk analyses
        risks = recommendation_data.get("risks", [])
        for risk_data in risks:
            risk = RiskAnalysis(
                recommendation_id=recommendation.id,
                risk_type=risk_data.get("type", "general"),
                risk_level=RiskLevel(risk_data.get("level", "medium")),
                risk_percentage=risk_data.get("percentage", 50.0),
                description=risk_data.get("description", ""),
                factors=risk_data.get("factors", [])
            )
            self.db.add(risk)
        
        # Create opportunities
        opportunities = recommendation_data.get("opportunities", [])
        for opp_data in opportunities:
            opportunity = Opportunity(
                recommendation_id=recommendation.id,
                title=opp_data.get("title", ""),
                description=opp_data.get("description", ""),
                confidence_percentage=opp_data.get("confidence", 50.0),
                impact_level=opp_data.get("impact", "medium"),
                metadata=opp_data.get("metadata", {})
            )
            self.db.add(opportunity)
        
        await self.db.commit()
        
        return {
            "recommendation_id": recommendation.id,
            "type": recommendation.recommendation_type,
            "confidence": recommendation.confidence_percentage
        }

