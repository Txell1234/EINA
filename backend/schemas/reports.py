"""
Reports schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from models.reports import ReportStatus, ReportFormat

class ReportRequest(BaseModel):
    case_id: int
    title: Optional[str] = None
    format: Optional[ReportFormat] = ReportFormat.PDF

class ReportResponse(BaseModel):
    id: int
    case_id: int
    title: str
    status: ReportStatus
    format: ReportFormat
    file_path: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)









