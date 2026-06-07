"""CCA rule suggestions for wizard — from inquiry morph bootstrap or project hypothesis."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import MorphComponent, ProspectiveProject
from models.prospective_inquiry import ProspectiveInquiry
from services.morph_bootstrap_service import MorphBootstrapService
from services.prospective_service import ProspectiveService


def _rule_key(r: dict[str, Any]) -> tuple[str, str, str, str]:
    """Canonical undirected pair key for deduplication."""
    a = (str(r.get("component_a") or ""), str(r.get("config_a") or ""))
    b = (str(r.get("component_b") or ""), str(r.get("config_b") or ""))
    if a <= b:
        return (a[0], a[1], b[0], b[1])
    return (b[0], b[1], a[0], a[1])


def _normalize_rule(rule: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "id": str(rule.get("id") or f"rule_{idx}"),
        "component_a": str(rule.get("component_a") or rule.get("comp_a") or ""),
        "config_a": str(rule.get("config_a") or rule.get("cfg_a") or ""),
        "component_b": str(rule.get("component_b") or rule.get("comp_b") or ""),
        "config_b": str(rule.get("config_b") or rule.get("cfg_b") or ""),
        "consistency": rule.get("consistency", -1),
        "justification": rule.get("justification", ""),
        "source": rule.get("source", "domain_rule"),
        "selected": rule.get("selected", True),
    }


def merge_cca_rules(
    existing: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    *,
    remove_keys: set[tuple[str, str, str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Merge selected CCA rules into incompatibilities (bidirectional dedupe)."""
    remove_keys = remove_keys or set()
    merged: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    for r in existing:
        row = {
            "component_a": r["component_a"],
            "config_a": r["config_a"],
            "component_b": r["component_b"],
            "config_b": r["config_b"],
        }
        k = _rule_key(row)
        if k not in remove_keys:
            merged[k] = row

    for rule in selected:
        if rule.get("consistency", -1) != -1:
            continue
        if rule.get("selected") is False:
            k = _rule_key(rule)
            merged.pop(k, None)
            continue
        row = {
            "component_a": rule["component_a"],
            "config_a": rule["config_a"],
            "component_b": rule["component_b"],
            "config_b": rule["config_b"],
        }
        k = _rule_key(row)
        if k in remove_keys:
            merged.pop(k, None)
            continue
        if rule.get("justification"):
            row["justification"] = rule["justification"]
        if rule.get("source"):
            row["source"] = rule["source"]
        merged[k] = row

    return list(merged.values())


def classify_existing_rules(
    existing: list[dict[str, Any]],
    suggested_keys: set[tuple[str, str, str, str]],
) -> list[dict[str, Any]]:
    """Tag persisted incompatibilities as manual vs applied-from-suggestion."""
    out: list[dict[str, Any]] = []
    for i, r in enumerate(existing):
        k = _rule_key(r)
        out.append(
            {
                **r,
                "id": f"existing_{i}",
                "consistency": -1,
                "origin": "applied" if k in suggested_keys else "manual",
                "status": "applied" if k in suggested_keys else "manual",
                "selected": True,
                "already_applied": True,
            }
        )
    return out


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
        suggested_keys = {_rule_key(r) for r in rules}

        existing = await ProspectiveService(self.db).get_incompatibilities(project_id)
        existing_keys = {_rule_key(r) for r in existing}
        for rule in rules:
            k = _rule_key(rule)
            rule["already_applied"] = k in existing_keys
            rule["status"] = "applied" if rule["already_applied"] else "suggested"
            rule["origin"] = "suggested"

        existing_classified = classify_existing_rules(existing, suggested_keys)
        manual_only = [r for r in existing_classified if r["origin"] == "manual"]

        return {
            "found": True,
            "project_id": project_id,
            "inquiry_id": inquiry_id,
            "question": question,
            "suggested_components": morph_bootstrap.get("suggested_components") or [],
            "wizard_components": wizard_components,
            "rules": rules,
            "existing_incompatibilities": existing_classified,
            "manual_rules": manual_only,
            "cca_heatmap": morph_bootstrap.get("cca_heatmap"),
            "valid_combinations_count": morph_bootstrap.get("valid_combinations_count"),
            "methodology": morph_bootstrap.get("methodology", "rule_based_morph_bootstrap"),
            "counts": {
                "suggested": len(rules),
                "applied": sum(1 for r in rules if r.get("already_applied")),
                "manual": len(manual_only),
                "total_persisted": len(existing),
            },
        }

    async def apply_selected_rules(
        self,
        project_id: int,
        rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        existing = await ProspectiveService(self.db).get_incompatibilities(project_id)
        to_add = [r for r in rules if r.get("consistency", -1) == -1 and r.get("selected") is not False]
        to_remove = {_rule_key(r) for r in rules if r.get("selected") is False}
        merged = merge_cca_rules(existing, to_add, remove_keys=to_remove)
        stats = await ProspectiveService(self.db).save_incompatibilities(project_id, merged)
        return {
            "ok": True,
            "project_id": project_id,
            "rules_applied": len(to_add),
            "rules_removed": len(to_remove),
            "total_incompatibilities": len(merged),
            "incompatibilities": merged,
            "morph_stats": stats,
        }

    async def preview_cca_impact(
        self,
        project_id: int,
        rules: list[dict[str, Any]],
        *,
        include_existing: bool = True,
    ) -> dict[str, Any]:
        """Live preview: how proposed CCA rules change valid morph combinations."""
        from observability.metrics import (
            CCA_COMBINATIONS_TOTAL,
            CCA_PRUNED_TOTAL,
            MORPH_VALID_CONFIGS,
        )
        from observability.tracing import q2fs_span
        from services.morph_space import morph_space_stats

        with q2fs_span("cca_preview", "cca", {"project_id": project_id}):
            comp_r = await self.db.execute(
                select(MorphComponent)
                .where(MorphComponent.project_id == project_id)
                .order_by(MorphComponent.order_index.asc())
            )
            components = [
                {
                    "code": m.code,
                    "name": m.name,
                    "configurations": m.configurations or [],
                }
                for m in comp_r.scalars().all()
            ]
            if not components:
                return {"found": False, "error": "Cap component morfològic al projecte"}

            existing = (
                await ProspectiveService(self.db).get_incompatibilities(project_id)
                if include_existing
                else []
            )
            proposed = [
                {
                    "component_a": r["component_a"],
                    "config_a": r["config_a"],
                    "component_b": r["component_b"],
                    "config_b": r["config_b"],
                }
                for r in rules
                if r.get("selected", True) and r.get("consistency", -1) == -1
            ]
            before = morph_space_stats(components, existing)
            merged = merge_cca_rules(existing, proposed)
            after = morph_space_stats(components, merged)

            existing_keys = {_rule_key(r) for r in existing}
            proposed_keys = {_rule_key(r) for r in proposed}
            new_keys = proposed_keys - existing_keys
            removed_keys = existing_keys - proposed_keys if not include_existing else set()

            CCA_COMBINATIONS_TOTAL.inc(before["total_combinations"])
            pruned = after["filtered_out"] - before["filtered_out"]
            if pruned > 0:
                CCA_PRUNED_TOTAL.inc(pruned)
            MORPH_VALID_CONFIGS.set(after["valid_combinations"])

            return {
                "found": True,
                "project_id": project_id,
                "before": before,
                "after": after,
                "delta_valid_combinations": after["valid_combinations"] - before["valid_combinations"],
                "delta_filtered_out": after["filtered_out"] - before["filtered_out"],
                "proposed_rules_count": len(proposed),
                "survival_rate_pct": round(
                    100.0 * after["valid_combinations"] / max(before["total_combinations"], 1),
                    1,
                ),
                "diff": {
                    "new_rules": len(new_keys),
                    "unchanged_rules": len(existing_keys & proposed_keys),
                    "removed_if_replaced": len(removed_keys),
                },
            }
