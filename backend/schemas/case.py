"""
Case schemas
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.case import CaseStatus, CaseType

class CaseCreate(BaseModel):
    name: str
    case_type: CaseType = CaseType.GENERAL
    description: Optional[str] = None

class CaseUpdate(BaseModel):
    name: Optional[str] = None
    case_type: Optional[CaseType] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None

class CaseResponse(BaseModel):
    id: int
    name: str
    case_type: CaseType
    description: Optional[str]
    status: CaseStatus
    user_id: Optional[int] = None  # Autenticació eliminada
    created_at: Optional[datetime] = None  # Can be None initially, will be set by DB
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CasePromptRequest(BaseModel):
    prompt: str

class CaseAutoCreateRequest(BaseModel):
    prompt: str
    case_type: Optional[str] = None
    auto_run: Optional[bool] = True
    selected_kpi_ids: Optional[List[int]] = None  # KPIs selected by user

class CasePromptResponse(BaseModel):
    id: int
    case_id: int
    prompt: str
    ai_analysis: dict
    created_at: datetime
    
    class Config:
        from_attributes = True

class KPISuggestionResponse(BaseModel):
    """Response for KPI suggestions"""
    suggested_kpis: List[dict]
    case_type: str
    confidence: Optional[float] = None
    error: Optional[str] = None

