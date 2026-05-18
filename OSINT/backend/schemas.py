"""Pydantic schemas for API."""
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class CaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    country: Optional[str] = None
    case_type: Optional[str] = None
    thematics: Optional[List[str]] = None


class CaseCreate(CaseBase):
    pass


class CaseResponse(CaseBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OSINTCollectRequest(BaseModel):
    case_id: int
    query: str
    source_type: str
    thematic: Optional[str] = None


class OSINTDataResponse(BaseModel):
    id: int
    case_id: int
    source: str
    data_type: str
    query: Optional[str] = None
    thematic: Optional[str] = None
    raw_data: Optional[dict] = None
    metadata_info: Optional[dict] = None
    collected_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RiskConceptBase(BaseModel):
    name: str
    weight: Optional[float] = 1.0
    dimension: Optional[str] = None
    keywords: Optional[List[str]] = None


class RiskConceptCreate(RiskConceptBase):
    pass


class RiskConceptResponse(RiskConceptBase):
    id: int
    case_id: int

    class Config:
        from_attributes = True


class RiskAnalyzeRequest(BaseModel):
    rule_config: Optional[dict] = None


class RiskAnalyzeResponse(BaseModel):
    concepts: List[dict]
    dimensions: Optional[dict] = None
    overall_score: Optional[float] = None
