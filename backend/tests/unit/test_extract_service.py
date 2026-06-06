"""
Unit tests for extract_service pure functions.
Tests _recover_partial_json, grounding_score, and _clean_json
without any external API calls or database access.
"""
import pytest

from services.extract_service import _clean_json, _recover_partial_json
from services.extract_validation import grounding_score


class TestRecoverPartialJson:
    def test_valid_complete_json(self):
        text = '[{"actor": "Xina", "posture_value": 2}]'
        result = _recover_partial_json(text)
        assert len(result) == 1
        assert result[0]["actor"] == "Xina"

    def test_truncated_after_first_object(self):
        text = '[{"actor": "A", "value": 1}, {"actor": "B", "val'
        result = _recover_partial_json(text)
        assert len(result) == 1
        assert result[0]["actor"] == "A"

    def test_empty_array(self):
        result = _recover_partial_json("[]")
        assert result == []

    def test_not_starting_with_bracket(self):
        result = _recover_partial_json('{"actor": "A"}')
        assert result == []

    def test_completely_truncated(self):
        result = _recover_partial_json('[{"actor": "incomplete')
        assert result == []

    def test_multiple_objects_one_truncated(self):
        text = (
            '[{"actor": "A", "v": 1}, '
            '{"actor": "B", "v": 2}, '
            '{"actor": "C", "v'
        )
        result = _recover_partial_json(text)
        assert len(result) == 2
        assert result[0]["actor"] == "A"
        assert result[1]["actor"] == "B"

    def test_trailing_comma_cleaned(self):
        text = '[{"actor": "A", "v": 1},]'
        result = _recover_partial_json(text)
        assert len(result) == 1

    def test_nested_string_with_braces(self):
        text = '[{"statement": "China {expands} BRI", "value": 1}]'
        result = _recover_partial_json(text)
        assert len(result) == 1
        assert "expands" in result[0]["statement"]

    def test_escaped_quotes_in_string(self):
        text = '[{"statement": "He said \\"hello\\"", "v": 1}]'
        result = _recover_partial_json(text)
        assert len(result) == 1


class TestGroundingScore:
    def test_identical_texts(self):
        text = "China expands BRI into Central Asia"
        score = grounding_score(text, text)
        assert score == 1.0

    def test_no_overlap(self):
        statement = "alpha beta gamma delta"
        source = "uno dos tres cuatro"
        score = grounding_score(statement, source)
        assert score == 0.0

    def test_partial_overlap(self):
        statement = "China expands military presence"
        source = "China military operations in Pacific"
        score = grounding_score(statement, source)
        assert 0.0 < score <= 1.0

    def test_empty_statement(self):
        score = grounding_score("", "some source text here")
        assert score == 1.0

    def test_empty_source(self):
        score = grounding_score("statement words", "")
        assert score == 0.0

    def test_threshold_hallucination(self):
        statement = "Minister Zhang declared war on France yesterday"
        source = "The annual report covers economic performance indicators"
        score = grounding_score(statement, source)
        assert score < 0.08

    def test_well_grounded(self):
        source = "China announced new BRI agreements with Pakistan and Sri Lanka"
        statement = "China announced BRI agreements"
        score = grounding_score(statement, source)
        assert score > 0.5

    def test_case_insensitive(self):
        score1 = grounding_score("CHINA EXPANDS BRI", "china expands bri")
        score2 = grounding_score("china expands bri", "china expands bri")
        assert score1 == score2 == 1.0


class TestCleanJson:
    def test_strips_json_fences(self):
        text = "```json\n[{\"a\": 1}]\n```"
        result = _clean_json(text)
        assert "```" not in result
        assert result.strip() == '[{"a": 1}]'

    def test_strips_plain_fences(self):
        text = "```\n[{\"a\": 1}]\n```"
        result = _clean_json(text)
        assert "```" not in result

    def test_no_fences_unchanged(self):
        text = '[{"a": 1}]'
        assert _clean_json(text) == '[{"a": 1}]'

    def test_trailing_comma_removed(self):
        text = '[{"a": 1,}]'
        result = _clean_json(text)
        assert ",}" not in result
