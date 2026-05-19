"""Unit tests for morphological space (Zwicky) and SMIC."""
import pytest

from services.morph_space import (
    build_cartesian,
    build_scenario_specs,
    compute_smic_bayesian,
    compute_smic_final,
    filter_valid_combinations,
    format_morph_config,
    is_combo_valid,
    morph_space_stats,
    select_scenario_combos,
)


COMPONENTS = [
    {
        "code": "C1",
        "name": "BRI",
        "configs": [{"label": "Expansio"}, {"label": "Estancament"}, {"label": "Retroces"}],
    },
    {
        "code": "C2",
        "name": "QUAD",
        "configs": [{"label": "Alta cohesio"}, {"label": "Divisio"}],
    },
]


class TestMorphSpace:
    def test_cartesian_product_size(self):
        combos = build_cartesian(COMPONENTS)
        assert len(combos) == 6

    def test_filter_incompatible_pair(self):
        incompat = [
            {
                "component_a": "C1",
                "config_a": "Expansio",
                "component_b": "C2",
                "config_b": "Alta cohesio",
            }
        ]
        valid = filter_valid_combinations(COMPONENTS, incompat)
        assert len(valid) == 5
        for combo in valid:
            assert is_combo_valid(combo, incompat)

    def test_morph_space_stats(self):
        stats = morph_space_stats(COMPONENTS, [])
        assert stats["total_combinations"] == 6
        assert stats["valid_combinations"] == 6

    def test_select_scenario_combos_extremes(self):
        combos = select_scenario_combos(COMPONENTS, [])
        infern = combos["infern"]
        cel = combos["cel"]
        assert format_morph_config(infern) != format_morph_config(cel)

    def test_build_scenario_specs_uses_real_configs(self):
        specs = build_scenario_specs(COMPONENTS, [])
        assert all(s["config"] for s in specs)
        assert "Expansio" in specs[0]["config"] or "Alta cohesio" in specs[0]["config"]


class TestSMIC:
    def test_compute_smic_normalizes(self):
        initial = [0.25, 0.25, 0.25, 0.25]
        cross = [[0.0] * 4 for _ in range(4)]
        final, labels = compute_smic_final(initial, cross)
        assert abs(sum(final) - 1.0) < 0.001
        assert len(labels) == 4

    def test_compute_smic_bayesian(self):
        prior = [0.65, 0.35, 0.35, 0.10]
        cross = [[0.0] * 4 for _ in range(4)]
        cross[0][1] = 0.8
        adjusted, labels = compute_smic_bayesian(prior, cross)
        assert len(adjusted) == 4
        assert len(labels) == 4
        assert abs(sum(adjusted) - 1.0) < 0.01
