"""Tests for inquiry → Godet wizard bridge."""
import pytest

from services.inquiry_wizard_bridge_service import InquiryWizardBridgeService
from services.morph_bootstrap_service import MorphBootstrapService


@pytest.mark.unit
async def test_apply_morph_bootstrap_creates_project(db_session, sample_case):
    morph = MorphBootstrapService().bootstrap(
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        event_type="security_maritime",
    )
    result = await InquiryWizardBridgeService(db_session).apply_morph_bootstrap(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        morph_bootstrap=morph,
    )
    assert result["ok"] is True
    assert result["project_id"] > 0
    assert result["components_saved"] >= 3
    assert result["cca_rules_saved"] >= 0
