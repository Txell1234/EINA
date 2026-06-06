"""Bridge inquiry morph bootstrap into the manual Godet wizard (additive seed)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.prospective_service import ProspectiveService


class InquiryWizardBridgeService:
    """Seed prospective project with morph components + CCA from inquiry — user completes MIC-MAC/MACTOR manually."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.prospective = ProspectiveService(db)

    async def apply_morph_bootstrap(
        self,
        *,
        case_id: int,
        question: str,
        morph_bootstrap: dict[str, Any],
        project_id: int | None = None,
    ) -> dict[str, Any]:
        components_raw = morph_bootstrap.get("suggested_components") or []
        cca_rules = morph_bootstrap.get("suggested_cca_rules") or []

        components = []
        for c in components_raw:
            configs = []
            for cfg in c.get("configurations") or []:
                if isinstance(cfg, dict):
                    configs.append({"label": cfg.get("label", ""), "desc": cfg.get("desc", "")})
                else:
                    configs.append({"label": str(cfg), "desc": ""})
            components.append(
                {
                    "code": c.get("code", ""),
                    "name": c.get("name", ""),
                    "configs": configs,
                }
            )

        if project_id:
            project = await self.prospective.get_project(project_id)
            if not project or project.case_id != case_id:
                return {"ok": False, "error": "Projecte no trobat per aquest cas"}
        else:
            title = question[:80] + ("…" if len(question) > 80 else "")
            project = await self.prospective.create_project(
                title=f"Inquiry: {title}",
                hypothesis=question,
                context="Generat des de Prospective Inquiry Q2FS — completa MIC-MAC i MACTOR manualment.",
                case_id=case_id,
            )
            project_id = project.id

        await self.prospective.save_components(project_id, components)
        stats = await self.prospective.save_incompatibilities(project_id, cca_rules)

        return {
            "ok": True,
            "project_id": project_id,
            "components_saved": len(components),
            "cca_rules_saved": len(cca_rules),
            "morph_stats": stats,
            "note": (
                "Components morfològics i regles CCA suggerides aplicats. "
                "Continua MIC-MAC i MACTOR al wizard d'Anàlisi Prospectiva."
            ),
        }
