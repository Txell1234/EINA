"""
Qualitative Analysis schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from models.qualitative import ReasoningFrameworkType, KPIType

class PremiseCreate(BaseModel):
    case_id: int
    premise_text: str
    framework_id: Optional[int] = None

class PremiseResponse(BaseModel):
    id: int
    case_id: int
    premise_text: str
    framework_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class KPICreate(BaseModel):
    name: str
    kpi_type: KPIType
    metric_type: Optional[str] = None  # sentiment, volume, count, trend, engagement, ratio, custom
    description: Optional[str] = None
    target_value: Optional[str] = None
    measurement_unit: Optional[str] = None
    case_type_filter: Optional[str] = None  # Comma-separated case types
    is_template: bool = False

class KPIResponse(BaseModel):
    id: int
    name: str
    kpi_type: KPIType
    metric_type: Optional[str]
    description: Optional[str]
    target_value: Optional[str]
    measurement_unit: Optional[str]
    case_type_filter: Optional[str]
    is_active: bool
    is_template: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CaseKPICreate(BaseModel):
    case_id: int
    kpi_id: int
    target_value: Optional[str] = None
    measurement_unit: Optional[str] = None
    is_tracked: bool = True
    metadata: Optional[dict] = None

class CaseKPIResponse(BaseModel):
    id: int
    case_id: int
    kpi_id: int
    value: Optional[str]
    target_value: Optional[str]
    measurement_unit: Optional[str]
    is_tracked: bool
    metadata: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    kpi: Optional[KPIResponse] = None  # Include KPI details
    
    model_config = ConfigDict(from_attributes=True)

class ReasoningFrameworkResponse(BaseModel):
    id: int
    name: str
    framework_type: ReasoningFrameworkType
    description: Optional[str]
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class QualitativeAnalysisRequest(BaseModel):
    case_id: int
    premise: str
    framework: str = "deductive"
    kpi_ids: Optional[List[int]] = None

class QualitativeAnalysisResponse(BaseModel):
    id: int
    case_id: int
    premise_id: int
    framework_id: Optional[int]
    conclusions: str
    evidence: List[dict]
    confidence_score: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


