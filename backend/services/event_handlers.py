"""
Event bus handlers — wire domain events to downstream services.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.database import AsyncSessionLocal
from services.event_bus_service import get_event_bus
from services.extract_service import ExtractService
from services.prospective_service import ProspectiveService

logger = logging.getLogger(__name__)


async def handle_extraction_completed(event: Dict[str, Any]) -> None:
    """Sync suggested variables/actors into the latest prospective project for the case."""
    case_id = event.get("detail", {}).get("case_id")
    if not case_id:
        return

    async with AsyncSessionLocal() as db:
        extract_svc = ExtractService(db)
        prospective_svc = ProspectiveService(db)

        variables = await extract_svc.get_suggested_variables(case_id)
        actors = await extract_svc.get_suggested_actors(case_id)
        if not variables and not actors:
            logger.info("Extraction completed for case %s: no suggestions to apply", case_id)
            return

        projects = await prospective_svc.list_projects(case_id=case_id)
        if not projects:
            logger.info(
                "Extraction completed for case %s: %d vars, %d actors — no prospective project",
                case_id,
                len(variables),
                len(actors),
            )
            return

        project = projects[0]
        result = await prospective_svc.apply_extraction(project.id, variables, actors)
        logger.info(
            "Applied extraction to project %s (case %s): %d variables, %d actors",
            project.id,
            case_id,
            len(result.get("variables", [])),
            len(result.get("actors", [])),
        )


def register_event_handlers() -> None:
    bus = get_event_bus()
    bus.register_rule(
        name="prospective-sync-on-extraction",
        handler=handle_extraction_completed,
        sources=["extract_service"],
        detail_types=["extraction.completed"],
    )
    logger.info("Event bus handlers registered")
