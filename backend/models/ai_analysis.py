"""
AI Analysis models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    analysis_type = Column(String, nullable=False)  # taranis, osintgpt, ominis
    analysis_data = Column(JSON)  # Full analysis results
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    concepts = relationship("Concept", back_populates="analysis")
    trends = relationship("Trend", back_populates="analysis")
    sentiments = relationship("Sentiment", back_populates="analysis")
    predictions = relationship("AIPrediction", back_populates="analysis")

class Concept(Base):
    __tablename__ = "concepts"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("ai_analyses.id"), nullable=False)
    concept_name = Column(String, nullable=False, index=True)
    concept_type = Column(String)  # entity, topic, relationship, etc.
    confidence = Column(Float, default=0.0)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis = relationship("AIAnalysis", back_populates="concepts")

class Trend(Base):
    __tablename__ = "trends"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("ai_analyses.id"), nullable=False)
    trend_name = Column(String, nullable=False)
    trend_type = Column(String)  # emerging, declining, stable
    intensity = Column(Float)  # 0-100
    confidence = Column(Float, default=0.0)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis = relationship("AIAnalysis", back_populates="trends")

class Sentiment(Base):
    __tablename__ = "sentiments"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("ai_analyses.id"), nullable=False)
    sentiment_type = Column(String, nullable=False)  # positive, negative, neutral
    score = Column(Float)  # -1 to 1
    confidence = Column(Float, default=0.0)
    source_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis = relationship("AIAnalysis", back_populates="sentiments")

class AIPrediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("ai_analyses.id"), nullable=False)
    prediction_type = Column(String, nullable=False)  # trend, risk, market, event
    prediction_text = Column(Text, nullable=False)
    confidence_percentage = Column(Float, nullable=False)  # 0-100
    predicted_date = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    analysis = relationship("AIAnalysis", back_populates="predictions")

