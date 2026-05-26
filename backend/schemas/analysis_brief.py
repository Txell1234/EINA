"""User-directed analysis brief — required for complementary tools."""
from typing import Optional

from pydantic import BaseModel, Field


class UserAnalysisBrief(BaseModel):
    """Direcció i pensament de l'usuari abans de qualsevol anàlisi complementari."""

    user_direction: str = Field(
        ...,
        min_length=30,
        max_length=8000,
        description="Pregunta analítica, hipòtesi o angle que vol explorar l'usuari",
    )
    focus_entity: Optional[str] = Field(None, max_length=200)
    focus_topic: Optional[str] = Field(None, max_length=300)


class ExpertAnalysisRequest(UserAnalysisBrief):
    """Cos comú per anàlisis expertes (reputació, PA, inversió)."""

    policy_topic: Optional[str] = Field(None, max_length=300)
    entity_name: Optional[str] = Field(None, max_length=200)
