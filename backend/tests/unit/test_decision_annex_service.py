"""Tests for decision annex and INTSUM digest."""
import pytest

from services.decision_annex_service import (
    build_case_intsum,
    build_decision_annex,
    decision_annex_html,
)


@pytest.mark.unit
def test_decision_annex_html_empty_when_no_content():
    assert decision_annex_html({"has_content": False}) == ""


@pytest.mark.unit
def test_decision_annex_html_renders_sections():
    html = decision_annex_html(
        {
            "has_content": True,
            "monitor_horizons": ["12m"],
            "points_of_no_return": [{"title": "Reforma irreversible", "trigger": "vot", "horizon": "12m"}],
            "key_actors": [
                {
                    "name": "Japó",
                    "actor_class": "state",
                    "statement_count": 5,
                    "avg_posture": 1.2,
                    "top_topics": ["defensa"],
                }
            ],
            "signal_breakdown": {"structural": 3, "episodic": 2, "unknown": 0},
        }
    )
    assert "Annex de decisió" in html
    assert "Japó" in html
    assert "Estructural" in html


@pytest.mark.unit
async def test_build_decision_annex_empty_case(db_session, sample_case):
    annex = await build_decision_annex(db_session, sample_case.id)
    assert annex["case_id"] == sample_case.id
    assert "has_content" in annex


@pytest.mark.unit
async def test_build_case_intsum_not_found(db_session):
    result = await build_case_intsum(db_session, 999_999, days=7)
    assert result["found"] is False


@pytest.mark.unit
async def test_build_case_intsum_with_case(db_session, sample_case):
    result = await build_case_intsum(db_session, sample_case.id, days=7)
    assert result["found"] is True
    assert result["days"] == 7
    assert "summary" in result
    assert "alerts" in result
    assert "statements" in result
    assert "has_activity" in result
    assert "alerts_fallback" in result["summary"]
    assert "statements_fallback" in result["summary"]


@pytest.mark.unit
async def test_build_case_intsum_statement_fallback(db_session, sample_case):
    from datetime import datetime, timedelta, timezone
    from models.extract import ExtractedStatement

    old = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.add(
        ExtractedStatement(
            case_id=sample_case.id,
            actor="Japó",
            actor_type="state",
            statement="Declaració de prova fora de la finestra de 7 dies",
            posture_value=1,
            cleanup_decision="KEEP",
            extracted_at=old.replace(tzinfo=None),
        )
    )
    await db_session.commit()

    result = await build_case_intsum(db_session, sample_case.id, days=7)
    assert result["summary"]["new_statements"] == 0
    assert result["summary"]["statements_fallback"] is True
    assert len(result["statements"]) >= 1
    assert result["has_activity"] is True
