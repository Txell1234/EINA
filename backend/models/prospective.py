"""
Prospective Analysis Models - MIC-MAC, MACTOR, Morphological, Scenarios
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Float, DateTime
from sqlalchemy.sql import func

from app.database import Base


class ProspectiveProject(Base):
    __tablename__ = "prospective_projects"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    title = Column(String, nullable=False)
    hypothesis = Column(Text, default="")
    context = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProspectiveVariable(Base):
    __tablename__ = "prospective_variables"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(4), nullable=False)
    name = Column(String, nullable=False)
    var_type = Column(String, default="I")
    description = Column(Text, default="")
    order_index = Column(Integer, default=0)


class MICMACResult(Base):
    __tablename__ = "micmac_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), unique=True)
    matrix_direct = Column(JSON)
    matrix_indirect = Column(JSON)
    motricite_direct = Column(JSON)
    dependence_direct = Column(JSON)
    sectors = Column(JSON)
    vb_index = Column(Integer, nullable=True)
    vr_index = Column(Integer, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class ProspectiveActor(Base):
    __tablename__ = "prospective_actors"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(4), nullable=False)
    name = Column(String, nullable=False)
    strategic_goals = Column(JSON, default=list)
    force_score = Column(Float, default=3.0)
    order_index = Column(Integer, default=0)


class MACTORObjective(Base):
    __tablename__ = "mactor_objectives"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(4), nullable=False)
    name = Column(String, nullable=False)
    order_index = Column(Integer, default=0)


class MACTORPosture(Base):
    __tablename__ = "mactor_postures"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    actor_code = Column(String(4))
    objective_code = Column(String(4))
    posture_value = Column(Integer, default=0)


class MACTORResult(Base):
    __tablename__ = "mactor_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), unique=True)
    mobilisation_actors = Column(JSON)
    mobilisation_objectives = Column(JSON)
    convergences_matrix = Column(JSON)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class MorphComponent(Base):
    __tablename__ = "morph_components"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(4), nullable=False)
    name = Column(String, nullable=False)
    configurations = Column(JSON, default=list)
    order_index = Column(Integer, default=0)


class MorphIncompatibility(Base):
    """Zwicky: incompatible configuration pairs across morphological components."""

    __tablename__ = "morph_incompatibilities"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), index=True)
    component_a = Column(String(8), nullable=False)
    config_a = Column(String(256), nullable=False)
    component_b = Column(String(8), nullable=False)
    config_b = Column(String(256), nullable=False)


class SMICResult(Base):
    """SMIC cross-impact matrix and computed scenario probabilities."""

    __tablename__ = "smic_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), unique=True)
    initial_probs = Column(JSON, default=list)
    cross_matrix = Column(JSON, default=list)
    final_probs = Column(JSON, default=list)
    final_labels = Column(JSON, default=list)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())


class ProspectiveScenario(Base):
    __tablename__ = "prospective_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    name = Column(String, nullable=False)
    scenario_type = Column(String)
    morphological_config = Column(Text, default="")
    probability = Column(String, default="MITJA")
    narrative = Column(Text, default="")
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


class MICMACExpertVote(Base):
    """Individual expert vote for one MIC-MAC matrix cell (Delphi panel mode)."""
    __tablename__ = "micmac_expert_votes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), index=True)
    expert_id = Column(String(64), nullable=False, index=True)
    expert_name = Column(String(128), default="Anònim")
    row_index = Column(Integer, nullable=False)
    col_index = Column(Integer, nullable=False)
    vote_value = Column(Integer, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())


class AlertMonitor(Base):
    """OSINT monitor created from a scenario early warning indicator."""
    __tablename__ = "alert_monitors"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), index=True)
    scenario_id = Column(Integer, ForeignKey("prospective_scenarios.id"), nullable=True)
    indicator = Column(Text, nullable=False)
    keywords = Column(JSON, default=list)
    osint_sources = Column(JSON, default=list)
    is_active = Column(Integer, default=1)
    last_checked = Column(DateTime(timezone=True), nullable=True)
    last_match = Column(DateTime(timezone=True), nullable=True)
    match_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
