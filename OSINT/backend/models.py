"""SQLAlchemy models for OSINT platform."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    case_type = Column(String(100), nullable=True)
    thematics = Column(JSON, nullable=True)  # ["geopolitical", "cyber", "brand", ...]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    osint_data = relationship("OSINTData", back_populates="case", cascade="all, delete-orphan")
    ai_analyses = relationship("AIAnalysis", back_populates="case", cascade="all, delete-orphan")
    risk_concepts = relationship("RiskConcept", back_populates="case", cascade="all, delete-orphan")
    risk_analyses = relationship("RiskAnalysis", back_populates="case", cascade="all, delete-orphan")
    kpis = relationship("KPI", back_populates="case", cascade="all, delete-orphan")
    qualitative_analyses = relationship("QualitativeAnalysis", back_populates="case", cascade="all, delete-orphan")
    unified_analyses = relationship("UnifiedAnalysis", back_populates="case", cascade="all, delete-orphan")
    investment_recommendations_rel = relationship("InvestmentRecommendation", back_populates="case", cascade="all, delete-orphan")


class OSINTData(Base):
    __tablename__ = "osint_data"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    source = Column(String(100), nullable=False)
    data_type = Column(String(100), nullable=False)
    query = Column(String(500), nullable=True)
    thematic = Column(String(100), nullable=True)
    raw_data = Column(JSON, nullable=True)
    metadata_info = Column(JSON, nullable=True)  # original_url, etc.
    collected_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="osint_data")


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    analysis_type = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="ai_analyses")


class RiskConcept(Base):
    __tablename__ = "risk_concepts"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    name = Column(String(255), nullable=False)
    weight = Column(Float, default=1.0)
    dimension = Column(String(100), nullable=True)
    keywords = Column(JSON, nullable=True)  # ["sancions", "sancions", ...]

    case = relationship("Case", back_populates="risk_concepts")


class RiskAnalysis(Base):
    __tablename__ = "risk_analyses"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    mode = Column(String(50), nullable=False)  # "rule_based" | "ai"
    parameters_snapshot = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="risk_analyses")


class KPI(Base):
    __tablename__ = "kpis"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    variable_type = Column(String(50), nullable=True)  # quantitative, qualitative
    value = Column(Float, nullable=True)
    qualitative_value = Column(String(500), nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="kpis")


class QualitativeAnalysis(Base):
    __tablename__ = "qualitative_analyses"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    premise = Column(Text, nullable=True)
    reasoning_framework = Column(String(100), nullable=True)
    kpi_ids = Column(JSON, nullable=True)  # [1, 2, 3]
    analysis_result = Column(JSON, nullable=True)
    conclusion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="qualitative_analyses")


class UnifiedAnalysis(Base):
    __tablename__ = "unified_analyses"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    country = Column(String(100), nullable=True)
    actor = Column(String(100), nullable=True)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="unified_analyses")


class InvestmentRecommendation(Base):
    __tablename__ = "investment_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="investment_recommendations_rel")
