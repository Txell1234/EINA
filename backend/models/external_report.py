"""External financial / research reports uploaded for case crossover (additive)."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.sql import func

from app.database import Base


class CaseExternalReport(Base):
    __tablename__ = "case_external_reports"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)

    source = Column(String, default="custom")  # praams | bloomberg | custom | url
    title = Column(String, default="")
    source_url = Column(String, default="")
    filename = Column(String, default="")

    raw_text = Column(Text, default="")
    parsed_metrics = Column(JSON, default=dict)
    parse_status = Column(String, default="pending")  # pending | ok | partial | failed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
