"""Aggregate case workspace payload for Intelligence Hub."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case
from models.prospective import ProspectiveProject
from models.prospective_inquiry import ProspectiveInquiry
from services.company_registry_service import load_company_registry
from services.financial_crossover_service import FinancialCrossoverService
from services.godet_checklist_service import project_godet_checklist
from services.intelligence_service import IntelligenceService


async def load_case_workspace(
    db: AsyncSession,
    case_id: int,
    *,
    project_id: int | None = None,
) -> dict[str, Any]:
    case_r = await db.execute(select(Case).where(Case.id == case_id))
    case = case_r.scalar_one_or_none()
    if not case:
        return {"found": False}

    intel = await IntelligenceService(db).get_status(case_id)
    pipeline = {
        "ready_steps": intel.get("ready_steps", 0),
        "total_steps": intel.get("total_steps", 6),
        "pipeline_ready": intel.get("pipeline_ready", False),
        "blocker": intel.get("blocker"),
        "steps": intel.get("steps") or {},
    }

    proj_r = await db.execute(
        select(ProspectiveProject)
        .where(ProspectiveProject.case_id == case_id)
        .order_by(ProspectiveProject.created_at.desc())
        .limit(20)
    )
    projects: list[dict[str, Any]] = []
    for p in proj_r.scalars().all():
        checklist_meta = await project_godet_checklist(db, p.id)
        projects.append(
            {
                "id": p.id,
                "title": p.title,
                "case_id": p.case_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "godet_checklist": checklist_meta.get("checklist") or {},
                "missing_steps": checklist_meta.get("missing_steps") or [],
                "suggested_next_step": checklist_meta.get("suggested_next_step"),
                "suggested_route": checklist_meta.get("suggested_route"),
                "scenario_count": checklist_meta.get("scenario_count", 0),
            }
        )

    inq_r = await db.execute(
        select(ProspectiveInquiry)
        .where(ProspectiveInquiry.case_id == case_id)
        .order_by(ProspectiveInquiry.created_at.desc())
        .limit(15)
    )
    inquiries = []
    for row in inq_r.scalars().all():
        answer = row.answer if isinstance(row.answer, dict) else {}
        artifacts = row.artifacts if isinstance(row.artifacts, dict) else {}
        inquiries.append(
            {
                "id": row.id,
                "question": (row.question or "")[:160],
                "mode": row.mode,
                "status": row.status,
                "run_count": row.run_count or 0,
                "wizard_project_id": artifacts.get("wizard_project_id"),
                "probability_pct": answer.get("probability_pct"),
                "possibility": answer.get("possibility"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    financial_reports = await FinancialCrossoverService(db).list_reports(case_id)

    briefing = (case.description or "").strip()
    briefing_excerpt = briefing[:280] + ("…" if len(briefing) > 280 else "")

    suggested_project_id = projects[0]["id"] if projects else None
    suggested_next_step = projects[0].get("suggested_next_step") if projects else None
    active_project_id = project_id if project_id else suggested_project_id
    company_registry = await load_company_registry(db, case_id, project_id=active_project_id)

    return {
        "found": True,
        "case": {
            "id": case.id,
            "name": case.name,
            "case_type": case.case_type,
            "briefing_excerpt": briefing_excerpt,
            "briefing_word_count": len(briefing.split()) if briefing else 0,
        },
        "pipeline": pipeline,
        "projects": projects,
        "inquiries": inquiries,
        "financial_reports": financial_reports[:20],
        "company_registry": company_registry,
        "suggested_project_id": suggested_project_id,
        "active_project_id": active_project_id,
        "suggested_next_step": suggested_next_step,
    }
