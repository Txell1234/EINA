"""
Qualitative Analysis models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class ReasoningFrameworkType(str, enum.Enum):
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    CAUSAL = "causal"
    CUSTOM = "custom"

class KPIType(str, enum.Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"

class KPIMetricType(str, enum.Enum):
    """Types of metrics that can be tracked"""
    SENTIMENT = "sentiment"  # Positive/negative sentiment scores
    VOLUME = "volume"  # Count of mentions, posts, articles
    COUNT = "count"  # Number of events, agreements, etc.
    TREND = "trend"  # Trend direction (increasing/decreasing)
    ENGAGEMENT = "engagement"  # Likes, shares, comments
    RATIO = "ratio"  # Percentages, ratios
    CUSTOM = "custom"  # Custom metric type

class Premise(Base):
    __tablename__ = "premises"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    premise_text = Column(Text, nullable=False)
    framework_id = Column(Integer, ForeignKey("reasoning_frameworks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    framework = relationship("ReasoningFramework", back_populates="premises")
    analyses = relationship("QualitativeAnalysis", back_populates="premise")

class ReasoningFramework(Base):
    __tablename__ = "reasoning_frameworks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    framework_type = Column(Enum(ReasoningFrameworkType), nullable=False)
    description = Column(Text)
    definition = Column(JSON)  # doctrine, methodology, steps, criteria, prompts…
    is_custom = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    premises = relationship("Premise", back_populates="framework")
    analyses = relationship("QualitativeAnalysis", back_populates="framework")

class KPI(Base):
    __tablename__ = "kpis"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    kpi_type = Column(Enum(KPIType), nullable=False)
    metric_type = Column(String, nullable=True)  # sentiment, volume, count, trend, engagement, ratio, custom
    description = Column(Text)
    target_value = Column(String, nullable=True)
    measurement_unit = Column(String, nullable=True)  # e.g., "count", "percentage", "USD", "posts/day"
    case_type_filter = Column(String, nullable=True)  # Which case types this KPI is relevant for (comma-separated)
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)  # If True, this is a template KPI that can be reused
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    case_kpis = relationship("CaseKPI", back_populates="kpi")
    quantitative_analyses = relationship("QuantitativeAnalysis", back_populates="kpi")

class QualitativeAnalysis(Base):
    __tablename__ = "qualitative_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    premise_id = Column(Integer, ForeignKey("premises.id"), nullable=False)
    framework_id = Column(Integer, ForeignKey("reasoning_frameworks.id"), nullable=True)
    conclusions = Column(Text, nullable=False)
    evidence = Column(JSON)  # List of evidence items
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    premise = relationship("Premise", back_populates="analyses")
    framework = relationship("ReasoningFramework", back_populates="analyses")

class QuantitativeAnalysis(Base):
    __tablename__ = "quantitative_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    kpi_id = Column(Integer, ForeignKey("kpis.id"), nullable=False)
    value = Column(String, nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    kpi = relationship("KPI", back_populates="quantitative_analyses")

