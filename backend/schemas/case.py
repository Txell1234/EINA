"""
Case schemas
"""
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import datetime
from models.case import CaseStatus, CaseType
from utils.prompt_utils import normalize_prompt

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
    
    model_config = ConfigDict(from_attributes=True)

class CasePromptRequest(BaseModel):
    """Creació de cas: mode guiat (briefing + IA) o manual (usuari omple tot)."""
    prompt: str
    creation_mode: Literal["guided", "manual"] = "guided"
    name: Optional[str] = None
    case_type: Optional[str] = "general"

    @field_validator("prompt")
    @classmethod
    def normalize_multiline_prompt(cls, value: str) -> str:
        return normalize_prompt(value)

    @model_validator(mode="after")
    def validate_manual_fields(self) -> "CasePromptRequest":
        if self.creation_mode == "manual":
            manual_name = (self.name or "").strip()
            if not manual_name:
                raise ValueError("El nom del cas és obligatori en mode manual")
            self.name = manual_name
        return self

class CaseAutoCreateRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def normalize_multiline_prompt(cls, value: str) -> str:
        return normalize_prompt(value)
    case_type: Optional[str] = None
    auto_run: Optional[bool] = True
    selected_kpi_ids: Optional[List[int]] = None  # KPIs selected by user

class CasePromptResponse(BaseModel):
    id: int
    case_id: int
    prompt: str
    ai_analysis: dict
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class KPISuggestionResponse(BaseModel):
    """Response for KPI suggestions"""
    suggested_kpis: List[dict]
    case_type: str
    confidence: Optional[float] = None
    error: Optional[str] = None

