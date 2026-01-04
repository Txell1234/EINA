"""
OSINT models
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class QueryStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class OSINTQuery(Base):
    __tablename__ = "osint_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_type = Column(String, nullable=False)  # sherlock, recon-ng, google_news, etc.
    query_params = Column(JSON)  # Parameters for the query
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    status = Column(Enum(QueryStatus), default=QueryStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    results = relationship("OSINTResult", back_populates="query")

class OSINTResult(Base):
    __tablename__ = "osint_results"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("osint_queries.id"), nullable=False)
    data = Column(JSON)  # Result data
    status = Column(String, default="completed")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    query = relationship("OSINTQuery", back_populates="results")

class OSINTSource(Base):
    __tablename__ = "osint_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)  # social, news, code, etc.
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

