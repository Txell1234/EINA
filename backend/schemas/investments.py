"""
Investment Recommendations schemas
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from models.investments import RecommendationType, RiskLevel

class InvestmentRecommendationRequest(BaseModel):
    case_id: int
    user_direction: str = Field(..., min_length=30, max_length=8000)
    focus_entity: Optional[str] = Field(None, max_length=200)
    focus_topic: Optional[str] = Field(None, max_length=300)

class InvestmentRecommendationResponse(BaseModel):
    id: int
    case_id: int
    recommendation_type: RecommendationType
    confidence_percentage: float
    rationale: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class RiskAnalysisResponse(BaseModel):
    id: int
    recommendation_id: int
    risk_type: str
    risk_level: RiskLevel
    risk_percentage: float
    description: Optional[str]
    factors: List[dict]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OpportunityResponse(BaseModel):
    id: int
    recommendation_id: int
    title: str
    description: str
    confidence_percentage: float
    impact_level: Optional[str]
    metadata: Optional[dict]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)









