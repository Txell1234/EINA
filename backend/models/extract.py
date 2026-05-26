"""
Extracted Statements - structured extraction from OSINT sources
Pattern: github.com/pranaykotas/china-us-rhetoric
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Float, DateTime
from sqlalchemy.sql import func

from app.database import Base


class ExtractedStatement(Base):
    __tablename__ = "extracted_statements"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), nullable=True)
    osint_result_id = Column(Integer, nullable=True)

    actor = Column(String, nullable=False, index=True)
    actor_type = Column(String, default="state")
    actor_importance = Column(Integer, default=3)

    context = Column(Text, default="")
    statement = Column(Text, nullable=False)
    topic = Column(String, default="", index=True)
    framing = Column(String, default="neutral")

    posture_toward = Column(String, default="", index=True)
    posture_value = Column(Integer, default=0)

    tone = Column(String, default="neutral")
    tone_intensity = Column(Integer, default=3)

    relevance_signals = Column(JSON, default=list)
    grounding_score = Column(Float, nullable=True)
    cleanup_decision = Column(String, default="PENDING", index=True)
    cleanup_reason = Column(Text, default="")

    source_url = Column(String, default="")
    source_date = Column(String, default="")
    source_text_excerpt = Column(Text, default="")

    # Optional additive metadata (nullable — legacy rows unchanged)
    institution_subtype = Column(String, nullable=True, index=True)
    signal_type = Column(String, nullable=True, index=True)

    extracted_at = Column(DateTime(timezone=True), server_default=func.now())
