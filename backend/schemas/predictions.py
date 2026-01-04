"""
Predictions schemas
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class PredictionRequest(BaseModel):
    case_id: int
    prediction_type: str  # trend, risk, market, event
    model_id: Optional[int] = None
    context_data: Optional[Dict[str, Any]] = None
    predicted_date: Optional[datetime] = None

class PredictionResponse(BaseModel):
    id: int
    case_id: int
    model_id: Optional[int]
    prediction_type: str
    prediction_text: str
    confidence_percentage: float
    predicted_date: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TrendPredictionResponse(BaseModel):
    id: int
    prediction_text: str
    confidence_percentage: float
    created_at: datetime
    
    class Config:
        from_attributes = True









