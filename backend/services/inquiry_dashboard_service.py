"""Global prospective inquiry dashboard — cross-case listing and batch export."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case
from models.prospective_inquiry import ProspectiveInquiry
from services.inquiry_export_service import build_inquiry_report_html
from services.inquiry_orchestrator_service import InquiryOrchestratorService


class InquiryDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_dashboard(
        self,
        *,
        status: str | None = None,
        case_id: int | None = None,
        scheduled_only: bool = False,
        limit: int = 100,
    ) -> dict[str, Any]:
        q = (
            select(ProspectiveInquiry, Case.name)
            .join(Case, Case.id == ProspectiveInquiry.case_id)
            .order_by(ProspectiveInquiry.created_at.desc())
            .limit(min(limit, 200))
        )
        if status:
            q = q.where(ProspectiveInquiry.status == status)
        if case_id:
            q = q.where(ProspectiveInquiry.case_id == case_id)

        rows = list((await self.db.execute(q)).all())
        now = datetime.now(timezone.utc)
        items: list[dict[str, Any]] = []
        stats = {
            "total": 0,
            "completed": 0,
            "awaiting_godet": 0,
            "failed": 0,
            "scheduled_active": 0,
            "scheduled_due": 0,
        }

        for inquiry, case_name in rows:
            st = inquiry.status or "pending"
            stats["total"] += 1
            if st == "completed":
                stats["completed"] += 1
            elif st == "awaiting_godet":
                stats["awaiting_godet"] += 1
            elif st == "failed":
                stats["failed"] += 1

            scheduled = bool(inquiry.auto_rerun_enabled)
            due = False
            if scheduled:
                stats["scheduled_active"] += 1
                if inquiry.next_rerun_at:
                    nra = inquiry.next_rerun_at
                    if nra.tzinfo is None:
                        nra = nra.replace(tzinfo=timezone.utc)
                    due = nra <= now
                    if due:
                        stats["scheduled_due"] += 1

            if scheduled_only and not scheduled:
                continue

            ans = inquiry.answer if isinstance(inquiry.answer, dict) else {}
            artifacts = inquiry.artifacts if isinstance(inquiry.artifacts, dict) else {}
            items.append(
                {
                    "id": inquiry.id,
                    "case_id": inquiry.case_id,
                    "case_name": case_name,
                    "question": (inquiry.question or "")[:120],
                    "mode": inquiry.mode,
                    "status": st,
                    "run_count": inquiry.run_count or 0,
                    "probability_pct": ans.get("probability_pct"),
                    "possibility": ans.get("possibility"),
                    "auto_rerun_enabled": scheduled,
                    "next_rerun_at": inquiry.next_rerun_at.isoformat() if inquiry.next_rerun_at else None,
                    "scheduled_due": due,
                    "wizard_project_id": artifacts.get("wizard_project_id"),
                    "created_at": inquiry.created_at.isoformat() if inquiry.created_at else None,
                    "completed_at": inquiry.completed_at.isoformat() if inquiry.completed_at else None,
                }
            )

        return {"found": True, "stats": stats, "count": len(items), "items": items}

    async def export_batch_zip(self, inquiry_ids: list[int]) -> bytes:
        if not inquiry_ids:
            raise ValueError("Calen IDs d'inquiry")
        if len(inquiry_ids) > 50:
            raise ValueError("Màxim 50 inquiries per export batch")

        orchestrator = InquiryOrchestratorService(self.db)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for iid in inquiry_ids:
                detail = await orchestrator.get_detail(iid)
                if not detail.get("found"):
                    continue
                html = build_inquiry_report_html(detail)
                zf.writestr(f"inquiry_{iid}.html", html.encode("utf-8"))
            zf.writestr(
                "manifest.txt",
                "\n".join(f"inquiry_{iid}.html" for iid in inquiry_ids).encode("utf-8"),
            )
        return buf.getvalue()

    async def rerun_batch(
        self,
        inquiry_ids: list[int],
        *,
        force_refresh: bool = True,
        limit: int = 10,
    ) -> dict[str, Any]:
        if not inquiry_ids:
            raise ValueError("Calen IDs d'inquiry")
        if len(inquiry_ids) > limit:
            raise ValueError(f"Màxim {limit} inquiries per batch re-run")

        orchestrator = InquiryOrchestratorService(self.db)
        results: list[dict[str, Any]] = []
        for iid in inquiry_ids:
            try:
                summary = await orchestrator.run_batch(iid, force_refresh=force_refresh)
                results.append({"inquiry_id": iid, "ok": True, **summary})
            except Exception as exc:
                results.append({"inquiry_id": iid, "ok": False, "error": str(exc)[:200]})

        ok_count = sum(1 for r in results if r.get("ok"))
        return {
            "found": True,
            "processed": len(results),
            "ok_count": ok_count,
            "failed_count": len(results) - ok_count,
            "results": results,
        }
