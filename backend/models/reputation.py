"""
Reputation Management models - Perfiles de reputación, histórico y análisis de stakeholders
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class EntityType(str, enum.Enum):
    COMPANY = "company"
    COUNTRY = "country"
    PERSON = "person"
    ORGANIZATION = "organization"

class SentimentTrend(str, enum.Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"
    CRISIS = "crisis"

class StakeholderType(str, enum.Enum):
    MEDIA = "media"
    INFLUENCER = "influencer"
    GOVERNMENT = "government"
    COMMUNITY = "community"
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    INVESTOR = "investor"
    NGO = "ngo"
    ACADEMIC = "academic"

class EngagementLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

class ReputationProfile(Base):
    """Perfil de reputación de entidad (empresa, país, persona, organización)"""
    __tablename__ = "reputation_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_name = Column(String, nullable=False, index=True)
    
    # Score de reputación (0-100, donde 100 es mejor reputación)
    reputation_score = Column(Float, default=50.0, nullable=False)
    
    # Tendencia de sentimiento
    sentiment_trend = Column(Enum(SentimentTrend), default=SentimentTrend.STABLE)
    
    # Indicadores de crisis
    crisis_indicators = Column(JSON)  # Lista de indicadores de crisis detectados
    
    # Sentimiento por tipo de stakeholder
    stakeholder_sentiment = Column(JSON)  # {"media": 0.7, "influencer": 0.5, ...}
    
    # Sentimiento por plataforma social
    platform_sentiment = Column(JSON)  # {"Instagram": 0.8, "Twitter": 0.6, ...}
    
    # Metadata adicional
    entity_metadata = Column(JSON)  # Información adicional sobre la entidad
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    history = relationship("ReputationHistory", back_populates="profile", cascade="all, delete-orphan")
    stakeholder_analyses = relationship("StakeholderAnalysis", back_populates="reputation_profile", cascade="all, delete-orphan")

class ReputationHistory(Base):
    """Histórico de cambios en reputación"""
    __tablename__ = "reputation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("reputation_profiles.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    score = Column(Float, nullable=False)  # Score en este momento
    
    # Razón del cambio
    change_reason = Column(Text, nullable=True)
    
    # Eventos que causaron el cambio
    events = Column(JSON)  # Lista de eventos OSINT o análisis que causaron el cambio
    
    # Cambio respecto al anterior
    score_change = Column(Float, default=0.0)  # Diferencia con el score anterior
    
    # Metadata
    source_references = Column(JSON)  # Referencias a OSINT results o análisis
    
    # Relationships
    profile = relationship("ReputationProfile", back_populates="history")

class StakeholderAnalysis(Base):
    """Análisis de stakeholders"""
    __tablename__ = "stakeholder_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    profile_id = Column(Integer, ForeignKey("reputation_profiles.id"), nullable=True)
    
    stakeholder_type = Column(Enum(StakeholderType), nullable=False)
    stakeholder_name = Column(String, nullable=False, index=True)
    
    # Score de influencia (0-100)
    influence_score = Column(Float, default=0.0, nullable=False)
    
    # Sentimiento (-1 a 1, donde 1 es muy positivo)
    sentiment = Column(Float, default=0.0)
    
    # Nivel de engagement
    engagement_level = Column(Enum(EngagementLevel), default=EngagementLevel.MEDIUM)
    
    # Métricas de engagement
    engagement_metrics = Column(JSON)  # {"mentions": 100, "shares": 50, "comments": 30}
    
    # Plataformas donde está activo
    active_platforms = Column(JSON)  # ["Twitter", "LinkedIn", "Instagram"]
    
    # Metadata
    stakeholder_metadata = Column(JSON)  # Información adicional del stakeholder
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_analyzed = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    reputation_profile = relationship("ReputationProfile", back_populates="stakeholder_analyses")

