"""Unit tests for retrospective and geopolitical prospective bridges."""
from datetime import datetime

from services.prospective_geopolitical_service import (
    variable_matches_country,
    _relation_influence,
)
from services.retrospective_service import _parse_date, _quarter_label, _quarter_sort_key


class TestGeopoliticalBridge:
    def test_variable_matches_country(self):
        var = {"code": "A", "name": "Expansió BRI", "desc": "Xina belt and road"}
        assert variable_matches_country(var, "Xina")
        assert variable_matches_country(var, "China")

    def test_variable_matches_japan_english_label(self):
        var = {"code": "V1", "name": "Rearmament japonès", "desc": "defensa regional"}
        assert variable_matches_country(var, "Japan")
        assert variable_matches_country(var, "Govern del Japó")

    def test_event_importance_enum(self):
        from models.geopolitical import EventImportance
        from services.prospective_geopolitical_service import _enum_value

        assert _enum_value(EventImportance.HIGH) == "high"
        assert _enum_value(EventImportance.MEDIUM) == "medium"

    def test_relation_influence_deteriorating(self):
        class Rel:
            status = "deteriorating"
            relation_score = 30
            political_cooperation = 20
            economic_cooperation = 10
            security_cooperation = 15

        assert _relation_influence(Rel()) >= 2


class TestRetrospective:
    def test_parse_gdelt_date(self):
        dt = _parse_date("20241115T120000Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 11

    def test_parse_iso_date(self):
        dt = _parse_date("2024-06-15T10:30:00Z")
        assert dt is not None
        assert dt.day == 15

    def test_quarter_label(self):
        assert _quarter_label(datetime(2024, 5, 1)) == "Q2 2024"

    def test_quarter_sort_key(self):
        labels = ["Q3 2023", "Q1 2024", "Q2 2023"]
        assert sorted(labels, key=_quarter_sort_key) == ["Q2 2023", "Q3 2023", "Q1 2024"]
