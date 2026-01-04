"""
Public Affairs models - Análisis de políticas, advocacy y stakeholders
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class PolicyImpactLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"

class CampaignStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PolicyAnalysis(Base):
    """Análisis de políticas y regulaciones"""
    __tablename__ = "policy_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    
    policy_topic = Column(String, nullable=False, index=True)
    jurisdiction = Column(String, nullable=False, index=True)  # País o región
    
    # Score de impacto (0-100, donde 100 es máximo impacto)
    impact_score = Column(Float, default=0.0, nullable=False)
    
    # Nivel de impacto
    impact_level = Column(Enum(PolicyImpactLevel), default=PolicyImpactLevel.MEDIUM)
    
    # Posiciones de stakeholders
    stakeholder_positions = Column(JSON)  # {"stakeholder_name": {"position": "support/oppose/neutral", "influence": 0.8}}
    
    # Oportunidades de advocacy
    advocacy_opportunities = Column(JSON)  # Lista de oportunidades identificadas
    
    # Detalles de la política
    policy_description = Column(Text)
    policy_status = Column(String)  # "proposed", "under_review", "approved", "rejected"
    effective_date = Column(DateTime(timezone=True), nullable=True)
    
    # Análisis de impacto detallado
    impact_analysis = Column(JSON)  # Análisis detallado del impacto
    
    # Metadata
    source_references = Column(JSON)  # OSINT results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AdvocacyCampaign(Base):
    """Campañas de advocacy"""
    __tablename__ = "advocacy_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    
    campaign_name = Column(String, nullable=False, index=True)
    
    # Estado de la campaña
    status = Column(Enum(CampaignStatus), default=CampaignStatus.PLANNING)
    
    # Stakeholders objetivo
    target_stakeholders = Column(JSON)  # Lista de stakeholders objetivo con sus roles
    
    # Estrategia de mensajes
    message_strategy = Column(JSON)  # Estrategia de mensajes por stakeholder
    
    # Métricas de éxito
    success_metrics = Column(JSON)  # Métricas a medir: {"awareness": 0, "support": 0, "engagement": 0}
    
    # Métricas actuales
    current_metrics = Column(JSON)  # Métricas actuales de la campaña
    
    # Fechas
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Descripción
    description = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())



