"""Tests for actor network aggregation."""
from datetime import datetime

import pytest

from services.actor_network_service import ActorNetworkService


@pytest.mark.unit
async def test_actor_network_empty_case(db_session):
    svc = ActorNetworkService(db_session)
    result = await svc.build_network(99999)
    assert result["found"] is False


@pytest.mark.unit
async def test_actor_network_groups_by_typology(db_session):
    from models.case import Case, CaseStatus, CaseType
    from models.extract import ExtractedStatement

    case = Case(
        name="Rearmament del Japó",
        description="JSDF defense NATO Indo-Pacific",
        case_type=CaseType.GEOPOLITICAL,
        status=CaseStatus.PENDING,
        created_at=datetime.now(),
    )
    db_session.add(case)
    await db_session.flush()

    db_session.add(
        ExtractedStatement(
            case_id=case.id,
            actor="Japan",
            actor_type="state",
            institution_subtype="government",
            statement="Japan will increase defense spending for Indo-Pacific security.",
            topic="rearmament",
            posture_toward="China",
            posture_value=-1,
            cleanup_decision="KEEP",
        )
    )
    db_session.add(
        ExtractedStatement(
            case_id=case.id,
            actor="NATO",
            actor_type="alliance",
            institution_subtype="multilateral_org",
            statement="NATO welcomed Japan's defense cooperation in the region.",
            topic="alliance",
            posture_toward="Japan",
            posture_value=1,
            cleanup_decision="KEEP",
        )
    )
    await db_session.commit()

    result = await ActorNetworkService(db_session).build_network(case.id)
    assert result["found"] is True
    assert result["summary"]["actor_count"] >= 2
    assert "state" in result["summary"]["by_actor_class"]
    assert len(result["edges"]) >= 1
    assert result["analytical_profile"]["analysis_lenses"]
