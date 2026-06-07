from services.actor_impact_utils import coerce_evidence_text, evidence_is_cited, filter_cited_evidence


def test_coerce_evidence_text_from_dict_ref():
    assert coerce_evidence_text({"url": "https://example.com/a"}) == "https://example.com/a"
    assert coerce_evidence_text({"osint_result_id": 9}) == ""


def test_evidence_is_cited_accepts_dict_url():
    assert evidence_is_cited(
        {"source_url": {"url": "https://news.test/item"}, "excerpt": "x" * 60}
    )


def test_filter_cited_evidence_skips_invalid_refs():
    out = filter_cited_evidence(
        [
            {"source_url": {"osint_result_id": 1}, "excerpt": "short"},
            {
                "source_url": "https://valid.test",
                "excerpt": "Evidence with enough text to qualify as cited material here.",
            },
        ]
    )
    assert len(out) == 1
    assert out[0]["source_url"] == "https://valid.test"
