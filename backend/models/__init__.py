"""ORM models — import side effects register metadata."""
from models.case import Case  # noqa: F401
from models.extract import ExtractedStatement  # noqa: F401
from models.osint import OSINTQuery, OSINTResult  # noqa: F401
from models.prospective import (  # noqa: F401
    MACTORObjective,
    MACTORPosture,
    MACTORResult,
    MICMACResult,
    MorphComponent,
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
    ProspectiveVariable,
)
