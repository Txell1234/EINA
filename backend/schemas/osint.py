"""
OSINT schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from models.osint import QueryStatus

class OSINTQueryRequest(BaseModel):
    query_type: str
    query_params: Dict[str, Any] = {}
    case_id: Optional[int] = None

class OSINTQueryResponse(BaseModel):
    id: int
    query_type: str
    query_params: Dict[str, Any]
    case_id: Optional[int]
    status: QueryStatus
    created_at: datetime
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class OSINTResultResponse(BaseModel):
    query_id: Optional[int] = None
    result_id: Optional[int] = None
    data: Dict[str, Any]
    status: str
    error: Optional[str] = None
    coverage: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)

