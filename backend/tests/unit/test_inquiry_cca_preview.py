"""Tests for CCA live preview."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.inquiry_cca_service import InquiryCcaService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_preview_cca_impact():
    mock_db = MagicMock()
    mock_comp = MagicMock()
    mock_comp.code = "C1"
    mock_comp.name = "Actor"
    mock_comp.configurations = ["A", "B"]
    mock_comp.order_index = 0

    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = [mock_comp]
    mock_db.execute = AsyncMock(return_value=exec_result)

    mock_ps = MagicMock()
    mock_ps.get_incompatibilities = AsyncMock(return_value=[])

    with patch("services.inquiry_cca_service.ProspectiveService", return_value=mock_ps):
        svc = InquiryCcaService(mock_db)
        result = await svc.preview_cca_impact(
            1,
            [
                {
                    "component_a": "C1",
                    "config_a": "A",
                    "component_b": "C1",
                    "config_b": "B",
                    "consistency": -1,
                    "selected": True,
                }
            ],
        )

    assert result["found"] is True
    assert result["after"]["valid_combinations"] <= result["before"]["valid_combinations"]
