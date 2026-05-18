"""Minimal case model for prospective project FK."""
from sqlalchemy import Column, Integer, String

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=False, default="Cas")
