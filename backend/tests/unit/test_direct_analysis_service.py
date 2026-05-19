"""
Unit tests for direct_analysis_service pure helpers.
"""
import json

import pytest

from services.direct_analysis_service import (
    DirectAnalysisService,
    _validate_result,
)


@pytest.mark.unit
def test_validate_result_fixes_variable_desc_without_grau_en():
    result = {
        "variables": [
            {"code": "A", "name": "Presència militar", "desc": "Augment de tropes"},
        ],
        "actors": [],
        "components": [],
        "confidence": 0.8,
    }
    fixed, warnings = _validate_result(result)
    assert fixed["variables"][0]["desc"].lower().startswith("grau en")
    assert any("Variable A" in w for w in warnings)


@pytest.mark.unit
def test_validate_result_normalizes_confidence_out_of_range():
    for bad in (-0.5, 1.5, "alta", None):
        result = {
            "variables": [{"code": "A", "name": "X", "desc": "Grau en què X evoluciona"}] * 4,
            "actors": [{"code": "A1", "name": "Actor", "force": 3}] * 2,
            "components": [],
            "confidence": bad,
        }
        fixed, _ = _validate_result(result)
        assert fixed["confidence"] == 0.5


@pytest.mark.unit
def test_validate_result_keeps_valid_confidence():
    result = {
        "variables": [{"code": "A", "name": "X", "desc": "Grau en què X evoluciona"}] * 4,
        "actors": [{"code": "A1", "name": "Actor", "force": 3}] * 2,
        "components": [],
        "confidence": 0.75,
    }
    fixed, _ = _validate_result(result)
    assert fixed["confidence"] == 0.75


@pytest.mark.unit
def test_recover_analysis_extracts_partial_json():
    svc = DirectAnalysisService()
    broken = (
        'Aquí tens l\'anàlisi:\n'
        '{"hypothesis": "Tensió entre A i B", '
        '"context": "Context estratègic", '
        '"confidence": 0.7, '
        '"variables": [{"code": "A", "name": "Var", "desc": "Grau en què evoluciona"}], '
        '"actors": []}\n'
        'Text extra que trenca el parseig global'
    )
    recovered = svc._recover_analysis(broken)
    assert recovered is not None
    assert recovered["hypothesis"] == "Tensió entre A i B"
    assert recovered["confidence"] == 0.7
    assert len(recovered["variables"]) == 1


@pytest.mark.unit
def test_recover_analysis_returns_none_without_json():
    svc = DirectAnalysisService()
    assert svc._recover_analysis("cap json aquí") is None


@pytest.mark.unit
def test_recover_analysis_handles_trailing_comma():
    svc = DirectAnalysisService()
    raw = '{"hypothesis": "H", "variables": [],}'
    recovered = svc._recover_analysis(raw)
    assert recovered is not None
    assert recovered["hypothesis"] == "H"
    assert json.loads(json.dumps(recovered))  # serializable
