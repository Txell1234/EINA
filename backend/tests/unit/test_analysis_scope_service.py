"""Regression tests for analysis scope profile and filtering."""
from datetime import datetime

import pytest

from schemas.analysis_scope import AnalysisScope
from services.analysis_scope_service import (
    filter_articles_by_scope,
    load_case_scope_profile,
    scope_to_time_range,
)
from services.case_topic_relevance import build_case_topic_profile


@pytest.mark.unit
class TestScopeToTimeRange:
    def test_custom_dates(self):
        scope = AnalysisScope(start_date="2025-01-01", end_date="2025-03-31")
        tr = scope_to_time_range(scope)
        assert tr == {"start": "2025-01-01", "end": "2025-03-31"}

    def test_period_days(self):
        scope = AnalysisScope(period_days=90)
        tr = scope_to_time_range(scope)
        assert tr is not None
        assert "start" in tr and "end" in tr

    def test_empty_scope(self):
        scope = AnalysisScope(period_days=None, start_date=None, end_date=None)
        assert scope_to_time_range(scope) is None


@pytest.mark.unit
class TestLoadCaseScopeProfile:
    async def test_japan_rearmament_case(self, db_session):
        from models.case import Case, CaseStatus, CaseType

        case = Case(
            name="Rearmament del Japó",
            description=(
                "FOCULAITZACIÓ EN REARMAMENT de japó: analisi geopolítica "
                "Trump Xi Indo-Pacific JSDF Article 9"
            ),
            case_type=CaseType.GEOPOLITICAL,
            status=CaseStatus.PENDING,
            created_at=datetime.now(),
        )
        db_session.add(case)
        await db_session.commit()
        await db_session.refresh(case)

        profile = await load_case_scope_profile(db_session, case.id)

        assert profile.case_id == case.id
        assert profile.suggested_query
        assert "Japan" in profile.suggested_query
        assert "rearmament" in profile.suggested_query.lower()
        assert profile.suggested_queries
        assert profile.suggested_queries[0] == profile.suggested_query
        assert profile.analytical_profile is not None
        assert "public_sector" in profile.analytical_profile.get("analysis_lenses", [])
        assert profile.default_scope.apply_topic_filter is True

    async def test_missing_case_returns_empty_profile(self, db_session):
        profile = await load_case_scope_profile(db_session, 99999)
        assert profile.case_id == 99999
        assert profile.suggested_query == ""
        assert profile.keywords == []


@pytest.mark.unit
class TestFilterArticlesByScope:
    def test_topic_filter_removes_irrelevant(self):
        case_profile = build_case_topic_profile(
            "Rearmament del Japó",
            "JSDF defense budget Article 9 Indo-Pacific",
        )
        scope = AnalysisScope(apply_topic_filter=True, min_relevance=0.28)
        articles = [
            {
                "title": "Japan rearmament accelerates",
                "summary": "Japan plans to double defense budget and expand JSDF in Indo-Pacific.",
                "url": "https://example.com/japan",
            },
            {
                "title": "Iran closes Hormuz",
                "summary": "Iran's IRGC warned it would set ships ablaze in the Strait of Hormuz.",
                "url": "https://example.com/iran",
            },
        ]
        kept, stats = filter_articles_by_scope(
            articles, case_profile=case_profile, scope=scope
        )
        assert len(kept) == 1
        assert "Japan" in kept[0]["title"]
        assert stats["removed_topic"] == 1


@pytest.mark.unit
class TestScopeProfileEndpoint:
    def test_scope_profile_api(self, test_client, db_session):
        from models.case import Case, CaseStatus, CaseType

        async def _seed():
            case = Case(
                name="Rearmament del Japó",
                description="FOCULAITZACIÓ EN REARMAMENT de japó i Indo-Pacific",
                case_type=CaseType.GEOPOLITICAL,
                status=CaseStatus.PENDING,
                created_at=datetime.now(),
            )
            db_session.add(case)
            await db_session.commit()
            await db_session.refresh(case)
            return case.id

        import asyncio

        case_id = asyncio.get_event_loop().run_until_complete(_seed())

        resp = test_client.get(f"/api/cases/{case_id}/scope-profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == case_id
        assert "Japan" in data["suggested_query"]
        assert "rearmament" in data["suggested_query"].lower()
        assert data.get("analytical_profile")
        assert "analysis_lenses" in data["analytical_profile"]
