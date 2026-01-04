"""
Reports models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class ReportStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.GENERATING)
    format = Column(Enum(ReportFormat), default=ReportFormat.PDF)
    content = Column(JSON)  # Report content structure
    file_path = Column(String, nullable=True)  # Path to generated file
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)









