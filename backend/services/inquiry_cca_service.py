"""CCA rule suggestions for wizard — from inquiry morph bootstrap or project hypothesis."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import MorphComponent, ProspectiveProject
from models.prospective_inquiry import ProspectiveInquiry
from services.morph_bootstrap_service import MorphBootstrapService
from services.prospective_service import ProspectiveService


def _normalize_rule(rule: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "id": f"rule_{idx}",
        "component_a": str(rule.get("component_a") or rule.get("comp_a") or ""),
        "config_a": str(rule.get("config_a") or rule.get("cfg_a") or ""),
        "component_b": str(rule.get("component_b") or rule.get("comp_b") or ""),
        "config_b": str(rule.get("config_b") or rule.get("cfg_b") or ""),
        "consistency": rule.get("consistency", -1),
        "justification": rule.get("justification", ""),
        "source": rule.get("source", "domain_rule"),
        "selected": True,
    }


def merge_cca_rules(
    existing: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge selected CCA rules into incompatibilities list (dedupe by pair)."""

    def key(r: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            r.get("component_a", ""),
            r.get("config_a", ""),
            r.get("component_b", ""),
            r.get("config_b", ""),
        )

    merged = {key(r): r for r in existing}
    for rule in selected:
        if rule.get("consistency", -1) != -1:
            continue
        row = {
            "component_a": rule["component_a"],
            "config_a": rule["config_a"],
            "component_b": rule["component_b"],
            "config_b": rule["config_b"],
        }
        merged[key(row)] = row
    return list(merged.values())


class InquiryCcaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def suggest_for_project(
        self,
        project_id: int,
        *,
        inquiry_id: int | None = None,
    ) -> dict[str, Any]:
        project = await ProspectiveService(self.db).get_project(project_id)
        if not project:
            return {"found": False, "error": "Projecte no trobat"}

        morph_bootstrap: dict[str, Any] | None = None
        question = project.hypothesis or project.title or ""
        event_type = "geopolitical"
        actors: list[str] | None = None

        if inquiry_id:
            r = await self.db.execute(
                select(ProspectiveInquiry).where(ProspectiveInquiry.id == inquiry_id)
            )
            inquiry = r.scalar_one_or_none()
            if inquiry:
                question = inquiry.question or question
                parsed = inquiry.parsed_trigger if isinstance(inquiry.parsed_trigger, dict) else {}
                event_type = parsed.get("event_type", event_type)
                actors = parsed.get("actors")
                artifacts = inquiry.artifacts if isinstance(inquiry.artifacts, dict) else {}
                morph_bootstrap = artifacts.get("morph_bootstrap")

        if not morph_bootstrap:
            morph_bootstrap = MorphBootstrapService().bootstrap(
                question=question,
                event_type=event_type,
                actors=actors,
            )

        comp_r = await self.db.execute(
            select(MorphComponent)
            .where(MorphComponent.project_id == project_id)
            .order_by(MorphComponent.order_index.asc())
        )
        wizard_components = [
            {
                "code": m.code,
                "name": m.name,
                "configurations": m.configurations or [],
            }
            for m in comp_r.scalars().all()
        ]

        raw_rules = morph_bootstrap.get("suggested_cca_rules") or []
        rules = [_normalize_rule(r, i) for i, r in enumerate(raw_rules)]

        existing = await ProspectiveService(self.db).get_incompatibilities(project_id)
        existing_keys = {
            (
                r["component_a"],
                r["config_a"],
                r["component_b"],
                r["config_b"],
            )
            for r in existing
        }
        for rule in rules:
            pair = (rule["component_a"], rule["config_a"], rule["component_b"], rule["config_b"])
            rev = (rule["component_b"], rule["config_b"], rule["component_a"], rule["config_a"])
            rule["already_applied"] = pair in existing_keys or rev in existing_keys

        return {
            "found": True,
            "project_id": project_id,
            "inquiry_id": inquiry_id,
            "question": question,
            "suggested_components": morph_bootstrap.get("suggested_components") or [],
            "wizard_components": wizard_components,
            "rules": rules,
            "cca_heatmap": morph_bootstrap.get("cca_heatmap"),
            "valid_combinations_count": morph_bootstrap.get("valid_combinations_count"),
            "methodology": morph_bootstrap.get("methodology", "rule_based_morph_bootstrap"),
        }

    async def apply_selected_rules(
        self,
        project_id: int,
        rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        existing = await ProspectiveService(self.db).get_incompatibilities(project_id)
        selected = [r for r in rules if r.get("selected", True) and r.get("consistency", -1) == -1]
        merged = merge_cca_rules(existing, selected)
        stats = await ProspectiveService(self.db).save_incompatibilities(project_id, merged)
        return {
            "ok": True,
            "project_id": project_id,
            "rules_applied": len(selected),
            "total_incompatibilities": len(merged),
            "morph_stats": stats,
        }
