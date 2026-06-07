"""Tests for case-driven actor map sections."""
import pytest

from services.report_actor_map import build_actor_map_sections, _resolve_region
from services.report_layout import build_actor_map_html
from services.report_i18n import get_report_strings


class _FakeProject:
    hypothesis = "Fragmentació comercial US-Xina i resiliència domèstica a l'Indo-Pacífic"
    title = "Cas BRI"
    context = ""


class _FakeActor:
    def __init__(self, name: str, code: str, force: float, goals: list[str], order: int = 0):
        self.name = name
        self.code = code
        self.force_score = force
        self.strategic_goals = goals
        self.order_index = order


@pytest.mark.unit
def test_resolve_region_aliases():
    assert _resolve_region("Xina") == "china"
    assert _resolve_region("Índia") == "south_asia"
    assert _resolve_region("QUAD") is None
    assert _resolve_region("Unió Europea") == "europe"


@pytest.mark.unit
def test_all_godet_actors_appear_not_deduped_by_region():
    bundle = {
        "lang": "ca",
        "project": _FakeProject(),
        "actors": [
            _FakeActor("Xina", "CH", 5.0, ["Consolidar BRI", "Lideratge regional"], 0),
            _FakeActor("Índia", "IN", 4.0, ["Corredors alternatius"], 1),
            _FakeActor("QUAD", "QD", 4.0, ["Contenció BRI"], 2),
        ],
        "actor_impact": {"actors": [], "claims": [], "impact_matrix": []},
    }
    out = build_actor_map_sections(bundle)
    names = [c["actor_name"] for c in out["callouts"]]
    assert names == ["Xina", "Índia", "QUAD"]
    assert out["case_focus"]


@pytest.mark.unit
def test_bullets_from_case_data_not_generic_template():
    bundle = {
        "lang": "ca",
        "project": _FakeProject(),
        "actors": [_FakeActor("Xina", "CH", 5.0, ["Consolidar BRI"], 0)],
        "actor_impact": {
            "actors": [
                {
                    "name": "Xina",
                    "statement_count": 8,
                    "motivation": "Prioritza estabilitat domèstica segons OSINT del cas.",
                    "posture_trend": "deteriorating",
                }
            ],
            "claims": [
                {
                    "claim": "Xina mantindrà pressió comercial sobre aliats del QUAD.",
                    "actors": ["Xina"],
                }
            ],
            "impact_matrix": [
                {
                    "actor": "Xina",
                    "scenario_name": "Tensió alta",
                    "impact_label": "exposat",
                    "impact_score": -1.2,
                    "mechanism": "postura hostil + risc geo",
                    "confidence": 70,
                }
            ],
        },
    }
    out = build_actor_map_sections(bundle)
    ch = out["callouts"][0]
    assert ch["actor_name"] == "Xina"
    text = " ".join(ch["bullets"]).lower()
    assert "bri" in text
    assert "osint" in text or "pressió" in text
    assert "tensió alta" in text


@pytest.mark.unit
def test_build_actor_map_html_uses_actor_names():
    bundle = {
        "lang": "en",
        "project": _FakeProject(),
        "actors": [_FakeActor("Japan", "JP", 4.0, ["Adapt supply chains"], 0)],
        "actor_impact": {"actors": [], "claims": [], "impact_matrix": []},
    }
    actor_map = build_actor_map_sections(bundle)
    html = build_actor_map_html(actor_map, template="eina", strings=get_report_strings("en"))
    assert "Japan" in html
    assert "Adapt supply chains" in html
    assert "actor-map-card" in html
