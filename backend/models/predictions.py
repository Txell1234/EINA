"""
Predictions models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class PredictionModel(Base):
    __tablename__ = "prediction_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    model_type = Column(String, nullable=False)  # trend, risk, market, etc.
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    predictions = relationship("Prediction", back_populates="model")

class Prediction(Base):
    __tablename__ = "predictions_standalone"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("prediction_models.id"), nullable=True)
    prediction_type = Column(String, nullable=False)
    prediction_text = Column(Text, nullable=False)
    confidence_percentage = Column(Float, nullable=False)
    predicted_date = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    model = relationship("PredictionModel", back_populates="predictions")
    confidence_scores = relationship("ConfidenceScore", back_populates="prediction")

class ConfidenceScore(Base):
    __tablename__ = "confidence_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions_standalone.id"), nullable=False)
    score_type = Column(String, nullable=False)  # overall, evidence, reasoning
    score_value = Column(Float, nullable=False)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    prediction = relationship("Prediction", back_populates="confidence_scores")

