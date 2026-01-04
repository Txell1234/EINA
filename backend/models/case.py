"""
Case models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class CaseStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"

class CaseType(str, enum.Enum):
    GENERAL = "general"
    BUSINESS = "business"
    POLITICAL = "political"
    GEOPOLITICAL = "geopolitical"
    SOCIAL = "social"
    INVESTIGATION = "investigation"

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    case_type = Column(Enum(CaseType), default=CaseType.GENERAL)
    description = Column(Text)
    status = Column(Enum(CaseStatus), default=CaseStatus.PENDING)
    user_id = Column(Integer, nullable=True)  # Autenticació eliminada - ja no és foreign key
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    prompts = relationship("CasePrompt", back_populates="case")
    analyses = relationship("CaseAnalysis", back_populates="case")
    kpis = relationship("CaseKPI", back_populates="case")

class CasePrompt(Base):
    __tablename__ = "case_prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    ai_analysis = Column(JSON)  # Plan generado por IA
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="prompts")

class CaseAnalysis(Base):
    __tablename__ = "case_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    analysis_type = Column(String, nullable=False)  # osint, ai, qualitative, etc.
    analysis_id = Column(Integer)  # ID del análisis específico
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="analyses")

class CaseKPI(Base):
    __tablename__ = "case_kpis"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    kpi_id = Column(Integer, ForeignKey("kpis.id"), nullable=False)
    value = Column(String)  # Current value
    target_value = Column(String, nullable=True)  # Target value for this specific case
    measurement_unit = Column(String, nullable=True)  # Override unit if different from KPI template
    is_tracked = Column(Boolean, default=True)  # Whether this KPI is actively tracked for this case
    extra_metadata = Column(JSON, nullable=True)  # Additional metadata (e.g., social_network, date_range)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    case = relationship("Case", back_populates="kpis")
    kpi = relationship("KPI", back_populates="case_kpis")

