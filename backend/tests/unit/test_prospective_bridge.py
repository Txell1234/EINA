"""Unit tests for retrospective and geopolitical prospective bridges."""
from services.prospective_geopolitical_service import (
    variable_matches_country,
    _relation_influence,
)
from services.retrospective_service import _keywords, _trend_label


class TestGeopoliticalBridge:
    def test_variable_matches_country(self):
        var = {"code": "A", "name": "Expansió BRI", "desc": "Xina belt and road"}
        assert variable_matches_country(var, "Xina")

    def test_relation_influence_deteriorating(self):
        class Rel:
            status = "deteriorating"
            relation_score = 30
            political_cooperation = 20
            economic_cooperation = 10
            security_cooperation = 15

        assert _relation_influence(Rel()) >= 2


class TestRetrospective:
    def test_keywords_from_variable(self):
        kws = _keywords({"name": "Cohesió QUAD", "desc": "grau de coordinació"})
        assert any("quad" in k or "cohesió" in k for k in kws)

    def test_trend_rising(self):
        assert _trend_label([1, 1, 2, 2, 5, 6, 8, 9]) == "pujant"
