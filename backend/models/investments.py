"""
Investment Recommendations models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class RecommendationType(str, enum.Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class InvestmentRecommendation(Base):
    __tablename__ = "investment_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    recommendation_type = Column(Enum(RecommendationType), nullable=False)
    confidence_percentage = Column(Float, nullable=False)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    risk_analyses = relationship("RiskAnalysis", back_populates="recommendation")
    opportunities = relationship("Opportunity", back_populates="recommendation")

class RiskAnalysis(Base):
    __tablename__ = "risk_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("investment_recommendations.id"), nullable=False)
    risk_type = Column(String, nullable=False)  # geopolitical, political, social
    risk_level = Column(Enum(RiskLevel), nullable=False)
    risk_percentage = Column(Float, nullable=False)  # 0-100
    description = Column(Text)
    factors = Column(JSON)  # List of risk factors
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    recommendation = relationship("InvestmentRecommendation", back_populates="risk_analyses")

class Opportunity(Base):
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("investment_recommendations.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    confidence_percentage = Column(Float, nullable=False)
    impact_level = Column(String)  # high, medium, low
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    recommendation = relationship("InvestmentRecommendation", back_populates="opportunities")

