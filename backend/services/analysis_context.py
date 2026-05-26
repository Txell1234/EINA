"""Build analysis prompts from user direction + case context."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case, CasePrompt


async def latest_case_prompt(db: AsyncSession, case_id: int) -> str | None:
    result = await db.execute(
        select(CasePrompt)
        .where(CasePrompt.case_id == case_id)
        .order_by(CasePrompt.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return (row.prompt or "").strip() if row else None


async def case_brief(db: AsyncSession, case_id: int) -> dict:
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        return {}
    prompt = await latest_case_prompt(db, case_id)
    return {
        "case_id": case.id,
        "name": case.name,
        "case_type": case.case_type.value if hasattr(case.case_type, "value") else str(case.case_type),
        "description": case.description or "",
        "latest_prompt": prompt or "",
    }


def format_user_analysis_block(
    user_direction: str,
    *,
    case_name: str = "",
    case_description: str = "",
    latest_prompt: str = "",
    focus_entity: str | None = None,
    focus_topic: str | None = None,
) -> str:
    parts = [
        "=== DIRECCIÓ ANALÍTICA DE L'USUARI (PRIORITÀRIA — NO IGNORAR) ===",
        user_direction.strip(),
    ]
    if focus_entity:
        parts.append(f"\nEntitat focus: {focus_entity.strip()}")
    if focus_topic:
        parts.append(f"\nTema focus: {focus_topic.strip()}")
    if latest_prompt:
        parts.append(f"\n=== BRIEFING ORIGINAL DEL CAS ===\n{latest_prompt[:3000]}")
    elif case_name or case_description:
        parts.append("\n=== CONTEXT DEL CAS ===")
        if case_name:
            parts.append(f"Nom: {case_name}")
        if case_description:
            parts.append(f"Descripció: {case_description[:2000]}")
    return "\n".join(parts)
