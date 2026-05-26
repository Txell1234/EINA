"""Tests for optional alert monitor thresholds."""
import pytest

from services import alert_monitor_service as ams


@pytest.mark.unit
def test_monitor_gdelt_days_default():
    class M:
        lookback_days = None
        horizon_label = None

    assert ams._monitor_gdelt_days(M()) == 7


@pytest.mark.unit
def test_monitor_gdelt_days_custom():
    class M:
        lookback_days = 30
        horizon_label = None

    assert ams._monitor_gdelt_days(M()) == 30


@pytest.mark.unit
def test_monitor_gdelt_days_from_horizon():
    class M:
        lookback_days = None
        horizon_label = "6m"

    assert ams._monitor_gdelt_days(M()) == 180


@pytest.mark.unit
def test_passes_monitor_thresholds_legacy():
    class M:
        min_match_score = None
        min_keywords_matched = None

    assert ams._passes_monitor_thresholds(M(), ["a"], 0.2) is True


@pytest.mark.unit
def test_passes_monitor_thresholds_min_score():
    class M:
        min_match_score = 0.5
        min_keywords_matched = None

    assert ams._passes_monitor_thresholds(M(), ["a", "b"], 0.6) is True
    assert ams._passes_monitor_thresholds(M(), ["a"], 0.3) is False


@pytest.mark.unit
def test_passes_monitor_thresholds_min_keywords():
    class M:
        min_match_score = None
        min_keywords_matched = 2

    assert ams._passes_monitor_thresholds(M(), ["a", "b"], 0.5) is True
    assert ams._passes_monitor_thresholds(M(), ["a"], 0.9) is False
