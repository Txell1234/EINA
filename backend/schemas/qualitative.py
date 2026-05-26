"""
Qualitative Analysis schemas
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
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
    definition: Optional[dict[str, Any]] = None
    is_custom: bool = False
    user_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class FrameworkDefinition(BaseModel):
    doctrine: Optional[str] = ""
    epistemology: Optional[str] = ""
    ontology: Optional[str] = ""
    methodology: Optional[str] = ""
    analysis_steps: Optional[List[dict[str, Any]]] = None
    evidence_criteria: Optional[List[str]] = None
    bias_checks: Optional[List[str]] = None
    limitations: Optional[str] = ""
    output_sections: Optional[List[dict[str, Any]]] = None
    system_prompt_override: Optional[str] = ""
    application_notes: Optional[str] = ""
    tags: Optional[List[str]] = None
    auto_apply: bool = True


class ReasoningFrameworkCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    framework_type: ReasoningFrameworkType = ReasoningFrameworkType.CUSTOM
    description: Optional[str] = Field(None, max_length=2000)
    definition: Optional[FrameworkDefinition] = None


class ReasoningFrameworkUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    framework_type: Optional[ReasoningFrameworkType] = None
    description: Optional[str] = Field(None, max_length=2000)
    definition: Optional[FrameworkDefinition] = None
    is_active: Optional[bool] = None


class FrameworkGenerateRequest(BaseModel):
    brief: str = Field(..., min_length=20, max_length=4000)
    framework_type: ReasoningFrameworkType = ReasoningFrameworkType.CUSTOM
    language: str = Field(default="ca", max_length=10)


class FrameworkPreviewRequest(BaseModel):
    premise: str = Field(..., min_length=20, max_length=8000)
    case_context: Optional[str] = Field(None, max_length=4000)

class QualitativeAnalysisRequest(BaseModel):
    case_id: int
    premise: str = Field(..., min_length=30, max_length=8000)
    framework: Optional[str] = None
    framework_id: Optional[int] = None
    kpi_ids: Optional[List[int]] = None
    focus_entity: Optional[str] = Field(None, max_length=200)
    focus_topic: Optional[str] = Field(None, max_length=300)

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


