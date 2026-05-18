"""
Prospective Analysis Models - MIC-MAC, MACTOR, Morphological, Scenarios
"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
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
    variables = relationship(
        "ProspectiveVariable", back_populates="project", cascade="all, delete-orphan"
    )
    actors = relationship(
        "ProspectiveActor", back_populates="project", cascade="all, delete-orphan"
    )
    objectives = relationship(
        "MACTORObjective", back_populates="project", cascade="all, delete-orphan"
    )
    components = relationship(
        "MorphComponent", back_populates="project", cascade="all, delete-orphan"
    )
    scenarios = relationship(
        "ProspectiveScenario", back_populates="project", cascade="all, delete-orphan"
    )
    micmac_result = relationship(
        "MICMACResult", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    mactor_result = relationship(
        "MACTORResult", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )


class ProspectiveVariable(Base):
    __tablename__ = "prospective_variables"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(8), nullable=False)
    name = Column(String, nullable=False)
    var_type = Column(String, default="I")
    description = Column(Text, default="")
    order_index = Column(Integer, default=0)
    project = relationship("ProspectiveProject", back_populates="variables")


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
    project = relationship("ProspectiveProject", back_populates="micmac_result")


class ProspectiveActor(Base):
    __tablename__ = "prospective_actors"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(8), nullable=False)
    name = Column(String, nullable=False)
    strategic_goals = Column(JSON, default=list)
    force_score = Column(Float, default=3.0)
    order_index = Column(Integer, default=0)
    project = relationship("ProspectiveProject", back_populates="actors")


class MACTORObjective(Base):
    __tablename__ = "mactor_objectives"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(8), nullable=False)
    name = Column(String, nullable=False)
    order_index = Column(Integer, default=0)
    project = relationship("ProspectiveProject", back_populates="objectives")


class MACTORPosture(Base):
    __tablename__ = "mactor_postures"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    actor_code = Column(String(8))
    objective_code = Column(String(8))
    posture_value = Column(Integer, default=0)


class MACTORResult(Base):
    __tablename__ = "mactor_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"), unique=True)
    mobilisation_actors = Column(JSON)
    mobilisation_objectives = Column(JSON)
    convergences_matrix = Column(JSON)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("ProspectiveProject", back_populates="mactor_result")


class MorphComponent(Base):
    __tablename__ = "morph_components"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("prospective_projects.id"))
    code = Column(String(8), nullable=False)
    name = Column(String, nullable=False)
    order_index = Column(Integer, default=0)
    configurations = Column(JSON, default=list)
    project = relationship("ProspectiveProject", back_populates="components")


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
    project = relationship("ProspectiveProject", back_populates="scenarios")
