"""Prospective inquiry (Q2FS) — question-triggered full-stack analysis."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.sql import func

from app.database import Base


class ProspectiveInquiry(Base):
    __tablename__ = "prospective_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)

    question = Column(Text, nullable=False)
    mode = Column(String, default="full")  # full | lite
    status = Column(String, default="pending")
    # pending | parsing | osint | intelligence | awaiting_godet | synthesizing | completed | failed

    parsed_trigger = Column(JSON, default=dict)
    inquiry_scope = Column(JSON, default=dict)
    steps_log = Column(JSON, default=list)
    scope_audit = Column(JSON, default=dict)
    artifacts = Column(JSON, default=dict)
    answer = Column(JSON, default=dict)
    error_message = Column(Text, default="")

    include_financial = Column(Integer, default=0)
    financial_text = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
