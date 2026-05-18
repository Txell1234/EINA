"""
AI Analysis schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class AIAnalysisRequest(BaseModel):
    case_id: int
    osint_results: Optional[List[Dict[str, Any]]] = None

class AIAnalysisResponse(BaseModel):
    id: int
    case_id: int
    analysis_type: str
    analysis_data: Dict[str, Any]
    confidence_score: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ConceptResponse(BaseModel):
    id: int
    analysis_id: int
    concept_name: str
    concept_type: Optional[str] = None
    confidence: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TrendResponse(BaseModel):
    id: int
    analysis_id: int
    trend_name: str
    trend_type: Optional[str]
    intensity: float
    confidence: float
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SentimentResponse(BaseModel):
    id: int
    analysis_id: int
    sentiment_type: str
    score: float
    confidence: float
    source_text: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

