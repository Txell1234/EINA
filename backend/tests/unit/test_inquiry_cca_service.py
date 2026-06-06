"""Tests for CCA suggestions service."""
import pytest

from services.inquiry_cca_service import InquiryCcaService, merge_cca_rules
from services.inquiry_wizard_bridge_service import InquiryWizardBridgeService
from services.morph_bootstrap_service import MorphBootstrapService


@pytest.mark.unit
def test_merge_cca_rules_dedupes():
    existing = [{"component_a": "C1", "config_a": "A", "component_b": "C2", "config_b": "B"}]
    selected = [{"component_a": "C1", "config_a": "X", "component_b": "C2", "config_b": "Y", "consistency": -1}]
    merged = merge_cca_rules(existing, selected)
    assert len(merged) == 2


@pytest.mark.unit
async def test_suggest_for_project_from_inquiry(db_session, sample_case):
    morph = MorphBootstrapService().bootstrap(
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        event_type="security_maritime",
    )
    bridge = await InquiryWizardBridgeService(db_session).apply_morph_bootstrap(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        morph_bootstrap=morph,
    )
    assert bridge["ok"] is True

    from models.prospective_inquiry import ProspectiveInquiry

    inquiry = ProspectiveInquiry(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="full",
        status="awaiting_godet",
        parsed_trigger={"event_type": "security_maritime", "actors": ["Trump"]},
        artifacts={"morph_bootstrap": morph, "wizard_project_id": bridge["project_id"]},
    )
    db_session.add(inquiry)
    await db_session.commit()
    await db_session.refresh(inquiry)

    result = await InquiryCcaService(db_session).suggest_for_project(
        bridge["project_id"],
        inquiry_id=inquiry.id,
    )
    assert result["found"] is True
    assert len(result["rules"]) >= 1
    assert result["cca_heatmap"] is not None


@pytest.mark.unit
async def test_apply_selected_rules(db_session, sample_case):
    morph = MorphBootstrapService().bootstrap(
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        event_type="security_maritime",
    )
    bridge = await InquiryWizardBridgeService(db_session).apply_morph_bootstrap(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        morph_bootstrap=morph,
    )
    rules = morph.get("suggested_cca_rules") or []
    assert rules

    applied = await InquiryCcaService(db_session).apply_selected_rules(
        bridge["project_id"],
        [{**rules[0], "selected": True}],
    )
    assert applied["ok"] is True
    assert applied["total_incompatibilities"] >= 1
