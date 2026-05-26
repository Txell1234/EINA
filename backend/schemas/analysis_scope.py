"""Shared analysis/search scope parameters."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisScope(BaseModel):
    """Delimitations applied early in search, OSINT collection and analysis."""

    period_days: int | None = Field(None, ge=1, le=3650)
    start_date: str | None = Field(None, description="ISO date YYYY-MM-DD")
    end_date: str | None = Field(None, description="ISO date YYYY-MM-DD")
    apply_topic_filter: bool = True
    domains: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    min_relevance: float = Field(0.28, ge=0.0, le=1.0)


class CaseScopeProfile(BaseModel):
    case_id: int
    focus_label: str
    suggested_query: str
    suggested_queries: list[str] = Field(default_factory=list)
    keywords: list[str]
    primary_geos: list[str]
    themes: list[str]
    default_scope: AnalysisScope
    # Additive analytical framing (JPA-inspired: lenses, institutions, scenarios)
    case_type: str = "general"
    analytical_profile: dict | None = None
