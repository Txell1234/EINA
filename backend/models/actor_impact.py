"""
Actor impact assessments — actors affected per scenario with evidence trail.
"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON
from sqlalchemy.sql import func

from app.database import Base


class ActorImpactAssessment(Base):
    __tablename__ = "actor_impact_assessments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), nullable=True)
    assessment_data = Column(JSON, nullable=False, default=dict)
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
