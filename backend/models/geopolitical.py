"""
Geopolitical models - Relacions bilaterals, tractats, esdeveniments diplomàtics i riscos
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Float, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class RelationType(str, enum.Enum):
    BILATERAL = "bilateral"
    MULTILATERAL = "multilateral"
    ALLIANCE = "alliance"
    TRADE = "trade"
    DIPLOMATIC = "diplomatic"

class RelationStatus(str, enum.Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DETERIORATING = "deteriorating"
    CRITICAL = "critical"

class EventType(str, enum.Enum):
    SUMMIT = "summit"
    TREATY_SIGNING = "treaty_signing"
    SANCTION = "sanction"
    DIPLOMATIC_VISIT = "diplomatic_visit"
    TRADE_AGREEMENT = "trade_agreement"
    ALLIANCE_CHANGE = "alliance_change"
    CONFLICT = "conflict"
    OTHER = "other"

class EventImportance(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class BilateralRelation(Base):
    """Relació bilateral entre dos països amb històric temporal"""
    __tablename__ = "bilateral_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    country1 = Column(String, nullable=False, index=True)
    country2 = Column(String, nullable=False, index=True)
    relation_type = Column(Enum(RelationType), default=RelationType.BILATERAL)
    status = Column(Enum(RelationStatus), default=RelationStatus.STABLE)
    
    # Scoring de relació (0-100, on 100 és millor relació)
    relation_score = Column(Float, default=50.0)
    
    # Factors de relació
    political_cooperation = Column(Float, default=0.0)  # 0-100
    economic_cooperation = Column(Float, default=0.0)  # 0-100
    security_cooperation = Column(Float, default=0.0)  # 0-100
    cultural_exchange = Column(Float, default=0.0)  # 0-100
    
    # Dades temporals
    first_detected = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Metadata
    relation_metadata = Column(JSON)  # Informació addicional (tractats, visites, etc.)
    source_references = Column(JSON)  # Referències a OSINT results que van detectar la relació
    
    # Relationships
    treaties = relationship("Treaty", back_populates="relation", cascade="all, delete-orphan")
    events = relationship("DiplomaticEvent", back_populates="relation", cascade="all, delete-orphan")

class Treaty(Base):
    """Tractat o acord entre països"""
    __tablename__ = "treaties"
    
    id = Column(Integer, primary_key=True, index=True)
    relation_id = Column(Integer, ForeignKey("bilateral_relations.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    
    name = Column(String, nullable=False)
    treaty_type = Column(String)  # trade, defense, cultural, etc.
    signing_date = Column(DateTime(timezone=True))
    effective_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="active")  # active, expired, terminated
    
    # Països involucrats (pot ser més de 2 per tractats multilaterals)
    countries = Column(JSON)  # Lista de països
    
    # Detalls
    description = Column(Text)
    key_provisions = Column(JSON)  # Provisions clau del tractat
    impact_score = Column(Float, default=0.0)  # Impacte estimat (0-100)
    
    # Metadata
    source_references = Column(JSON)  # OSINT results que van detectar el tractat
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    relation = relationship("BilateralRelation", back_populates="treaties")

class DiplomaticEvent(Base):
    """Esdeveniment diplomàtic o polític"""
    __tablename__ = "diplomatic_events"
    
    id = Column(Integer, primary_key=True, index=True)
    relation_id = Column(Integer, ForeignKey("bilateral_relations.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    
    event_type = Column(Enum(EventType), nullable=False)
    importance = Column(Enum(EventImportance), default=EventImportance.MEDIUM)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    event_date = Column(DateTime(timezone=True), nullable=False)
    
    # Països/entitats involucrades
    countries = Column(JSON)  # Lista de països involucrats
    entities = Column(JSON)  # Organitzacions, persones clau, etc.
    
    # Impacte
    impact_score = Column(Float, default=0.0)  # Impacte estimat (0-100)
    sentiment_score = Column(Float, nullable=True)  # Sentiment associat (-1 a 1)
    
    # Location
    location = Column(String, nullable=True)
    location_coordinates = Column(JSON)  # {lat, lng}
    
    # Metadata
    source_references = Column(JSON)  # OSINT results
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    verified = Column(Boolean, default=False)  # Si l'esdeveniment ha estat verificat
    
    # Relationships
    relation = relationship("BilateralRelation", back_populates="events")

class GeopoliticalRisk(Base):
    """Scoring de risc geopolític per país/regió"""
    __tablename__ = "geopolitical_risks"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    
    country = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True, index=True)
    
    # Scoring general (0-100, on 100 és màxim risc)
    overall_risk_score = Column(Float, nullable=False)
    
    # Factors de risc (0-100 cadascun)
    political_stability_risk = Column(Float, default=0.0)  # Risc per inestabilitat política
    conflict_risk = Column(Float, default=0.0)  # Risc de conflicte
    economic_risk = Column(Float, default=0.0)  # Risc econòmic (sanccions, etc.)
    security_risk = Column(Float, default=0.0)  # Risc de seguretat (atacs, amenaces)
    
    # Factors addicionals
    regulatory_risk = Column(Float, default=0.0)  # Risc regulatori
    social_unrest_risk = Column(Float, default=0.0)  # Risc de malestar social
    
    # Prediccions
    risk_3_months = Column(Float, nullable=True)  # Predicció a 3 mesos
    risk_6_months = Column(Float, nullable=True)  # Predicció a 6 mesos
    risk_12_months = Column(Float, nullable=True)  # Predicció a 12 mesos
    
    # Canvi percentual (comparació amb període anterior)
    risk_change_7d = Column(Float, default=0.0)  # Canvi en 7 dies
    risk_change_30d = Column(Float, default=0.0)  # Canvi en 30 dies
    
    # Alertes
    alert_triggered = Column(Boolean, default=False)  # Si s'ha disparat una alerta (>15% canvi)
    alert_reason = Column(Text, nullable=True)  # Raó de l'alerta
    
    # Metadata
    factors_detail = Column(JSON)  # Detall dels factors que contribueixen al risc
    source_references = Column(JSON)  # OSINT results que van contribuir al càlcul
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SupplyChainRisk(Base):
    """Riesgos en cadenas de suministro"""
    __tablename__ = "supply_chain_risks"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    
    country = Column(String, nullable=False, index=True)
    industry = Column(String, nullable=False, index=True)  # manufacturing, technology, energy, etc.
    
    # Score de dependencia (0-100, donde 100 es máxima dependencia)
    dependency_score = Column(Float, default=0.0, nullable=False)
    
    # Factores de vulnerabilidad
    vulnerability_factors = Column(JSON)  # Lista de factores: ["political_instability", "trade_restrictions", etc.]
    
    # Análisis detallado
    risk_assessment = Column(JSON)  # Análisis detallado de riesgos
    mitigation_strategies = Column(JSON)  # Estrategias de mitigación sugeridas
    
    # Metadata
    source_references = Column(JSON)  # OSINT results que contribuyeron al análisis
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class EconomicInterdependence(Base):
    """Interdependencias económicas entre países"""
    __tablename__ = "economic_interdependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    
    country1 = Column(String, nullable=False, index=True)
    country2 = Column(String, nullable=False, index=True)
    
    # Volumen de comercio (en millones USD)
    trade_volume = Column(Float, default=0.0)
    
    # Ratio de dependencia (0-1, donde 1 es máxima dependencia)
    dependency_ratio = Column(Float, default=0.0)
    
    # Sectores involucrados
    sectors = Column(JSON)  # Lista de sectores: ["technology", "energy", "manufacturing"]
    
    # Análisis por sector
    sector_analysis = Column(JSON)  # Análisis detallado por sector
    
    # Dirección de la dependencia
    dependency_direction = Column(String)  # "mutual", "country1_to_country2", "country2_to_country1"
    
    # Metadata
    source_references = Column(JSON)  # OSINT results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())