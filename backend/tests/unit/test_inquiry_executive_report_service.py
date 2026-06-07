"""Tests for multi-inquiry executive report."""
import pytest

from services.inquiry_executive_report_service import (
    _cross_cutting_themes,
    _portfolio_stats,
    build_multi_inquiry_executive_html,
)


@pytest.mark.unit
def test_portfolio_stats():
    items = [
        {"status": "completed", "probability_pct": 30},
        {"status": "completed", "probability_pct": 50},
        {"status": "failed", "probability_pct": None},
    ]
    stats = _portfolio_stats(items)
    assert stats["count"] == 3
    assert stats["completed"] == 2
    assert stats["avg_probability"] == 40.0
    assert stats["min_probability"] == 30
    assert stats["max_probability"] == 50


@pytest.mark.unit
def test_cross_cutting_themes():
    details = [
        {
            "artifacts": {"monitor_suggestions": {"suggested_monitors": [{"indicator": "Hormuz traffic"}]}},
            "answer": {"conclusions": ["Risc elevat"]},
        },
        {
            "artifacts": {"monitor_suggestions": {"suggested_monitors": [{"indicator": "Hormuz traffic"}]}},
            "answer": {"conclusions": ["Risc elevat", "Altres"]},
        },
    ]
    themes = _cross_cutting_themes(details)
    assert "Hormuz traffic" in themes["monitors"]
    assert "Risc elevat" in themes["conclusions"]


@pytest.mark.unit
def test_build_multi_inquiry_executive_html():
    bundle = {
        "case_name": "Hormuz test",
        "scope_note": "Selecció",
        "comparison": {
            "items": [
                {
                    "id": 1,
                    "question": "Blockade lifted?",
                    "probability_pct": 35,
                    "possibility": "PLAUSIBLE",
                    "status": "completed",
                    "diff_vs_previous": None,
                },
                {
                    "id": 2,
                    "question": "Normalization by 2027?",
                    "probability_pct": 42,
                    "possibility": "POSSIBLE",
                    "status": "completed",
                    "diff_vs_previous": {"probability_delta": 7.0},
                },
            ],
            "probability_series": [
                {"id": 1, "probability_pct": 35},
                {"id": 2, "probability_pct": 42},
            ],
        },
        "stats": _portfolio_stats(
            [
                {"status": "completed", "probability_pct": 35},
                {"status": "completed", "probability_pct": 42},
            ]
        ),
        "details": [
            {
                "id": 1,
                "status": "completed",
                "question": "Blockade lifted?",
                "answer": {"probability_pct": 35, "possibility": "PLAUSIBLE", "conclusions": ["A"]},
            }
        ],
        "cross_cutting": {"monitors": [], "conclusions": []},
    }
    html = build_multi_inquiry_executive_html(bundle, lang="ca")
    assert "Informe executiu multi-inquiry" in html
    assert "Hormuz test" in html
    assert "Blockade lifted" in html
    assert "Síntesi comparativa" in html


@pytest.mark.unit
async def test_build_executive_report_bundle_by_case(db_session, sample_case):
    from models.prospective_inquiry import ProspectiveInquiry
    from services.inquiry_executive_report_service import build_executive_report_bundle

    db_session.add_all(
        [
            ProspectiveInquiry(
                case_id=sample_case.id,
                question="Trump announces US blockade of Hormuz lifted by December 2026?",
                mode="lite",
                status="completed",
                answer={"probability_pct": 35, "possibility": "PLAUSIBLE", "conclusions": ["X"]},
            ),
            ProspectiveInquiry(
                case_id=sample_case.id,
                question="Israel and Indonesia normalize relations by 2027?",
                mode="full",
                status="completed",
                answer={"probability_pct": 20, "possibility": "UNLIKELY", "conclusions": ["Y"]},
            ),
        ]
    )
    await db_session.commit()

    bundle = await build_executive_report_bundle(db_session, case_id=sample_case.id, lang="ca")
    assert bundle["case_id"] == sample_case.id
    assert len(bundle["details"]) == 2
    assert bundle["stats"]["count"] == 2
    assert bundle["stats"]["avg_probability"] == 27.5
