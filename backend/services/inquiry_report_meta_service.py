"""Saved report metadata for prospective inquiries (stored in artifacts.report_meta)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case
from models.prospective_inquiry import ProspectiveInquiry
from services.report_templates import DEFAULT_TEMPLATE, normalize_template


def _artifacts_dict(inquiry: ProspectiveInquiry) -> dict[str, Any]:
    return dict(inquiry.artifacts) if isinstance(inquiry.artifacts, dict) else {}


def get_report_meta(inquiry: ProspectiveInquiry) -> dict[str, Any]:
    artifacts = _artifacts_dict(inquiry)
    meta = artifacts.get("report_meta")
    if not isinstance(meta, dict):
        meta = {}
    return {
        "is_saved": bool(meta.get("is_saved")),
        "keep_forever": bool(meta.get("keep_forever")),
        "archived": bool(meta.get("archived")),
        "report_title": meta.get("report_title") or "",
        "export_template": normalize_template(meta.get("export_template")),
        "saved_at": meta.get("saved_at"),
        "notes": meta.get("notes") or "",
    }


async def update_report_meta(
    db: AsyncSession,
    inquiry_id: int,
    *,
    is_saved: bool | None = None,
    keep_forever: bool | None = None,
    archived: bool | None = None,
    report_title: str | None = None,
    export_template: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    r = await db.execute(select(ProspectiveInquiry).where(ProspectiveInquiry.id == inquiry_id))
    inquiry = r.scalar_one_or_none()
    if not inquiry:
        return {"found": False, "error": "Inquiry no trobada"}

    artifacts = _artifacts_dict(inquiry)
    meta = dict(artifacts.get("report_meta") or {})

    if is_saved is not None:
        meta["is_saved"] = is_saved
        if is_saved and not meta.get("saved_at"):
            meta["saved_at"] = datetime.now(timezone.utc).isoformat()
    if keep_forever is not None:
        meta["keep_forever"] = keep_forever
        if keep_forever:
            meta["is_saved"] = True
    if archived is not None:
        meta["archived"] = archived
    if report_title is not None:
        meta["report_title"] = report_title.strip()[:200]
    if export_template is not None:
        meta["export_template"] = normalize_template(export_template)
    if notes is not None:
        meta["notes"] = notes.strip()[:500]

    artifacts["report_meta"] = meta
    inquiry.artifacts = artifacts
    await db.commit()
    await db.refresh(inquiry)

    return {"found": True, "inquiry_id": inquiry_id, "report_meta": get_report_meta(inquiry)}


async def list_report_library(
    db: AsyncSession,
    *,
    case_id: int | None = None,
    saved_only: bool = True,
    include_archived: bool = False,
    limit: int = 100,
) -> dict[str, Any]:
    q = (
        select(ProspectiveInquiry, Case.name)
        .join(Case, Case.id == ProspectiveInquiry.case_id)
        .order_by(ProspectiveInquiry.updated_at.desc())
        .limit(min(limit, 200))
    )
    if case_id:
        q = q.where(ProspectiveInquiry.case_id == case_id)

    items: list[dict[str, Any]] = []
    for inquiry, case_name in (await db.execute(q)).all():
        meta = get_report_meta(inquiry)
        if saved_only and not meta["is_saved"]:
            continue
        if not include_archived and meta["archived"]:
            continue
        ans = inquiry.answer if isinstance(inquiry.answer, dict) else {}
        items.append(
            {
                "id": inquiry.id,
                "case_id": inquiry.case_id,
                "case_name": case_name,
                "question": inquiry.question,
                "status": inquiry.status,
                "mode": inquiry.mode,
                "probability_pct": ans.get("probability_pct"),
                "possibility": ans.get("possibility"),
                "completed_at": inquiry.completed_at.isoformat() if inquiry.completed_at else None,
                "run_count": inquiry.run_count or 0,
                "report_meta": meta,
            }
        )

    return {"found": True, "count": len(items), "items": items}
