"""OSINT query and result models for extraction pipeline."""
from sqlalchemy import Column, ForeignKey, Integer, JSON

from app.database import Base


class OSINTQuery(Base):
    __tablename__ = "osint_queries"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)


class OSINTResult(Base):
    __tablename__ = "osint_results"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("osint_queries.id"), nullable=False, index=True)
    data = Column(JSON, nullable=False, default=dict)
