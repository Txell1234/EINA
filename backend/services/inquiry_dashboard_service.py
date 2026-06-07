"""Global prospective inquiry dashboard — cross-case listing and batch export."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.case import Case
from models.prospective_inquiry import ProspectiveInquiry
from services.inquiry_export_service import build_inquiry_report_html
from services.inquiry_orchestrator_service import InquiryOrchestratorService
from services.inquiry_report_meta_service import get_report_meta


def extract_probability_history(
    artifacts: dict[str, Any] | None,
    *,
    current_probability: float | int | None = None,
    max_points: int = 12,
) -> list[dict[str, Any]]:
    """Time series from audit trail synthesis_completed events."""
    trail = (artifacts or {}).get("audit_trail") or []
    points: list[dict[str, Any]] = []
    for entry in trail:
        if not isinstance(entry, dict) or entry.get("event") != "synthesis_completed":
            continue
        pct = entry.get("probability_pct")
        if pct is None:
            continue
        points.append(
            {
                "at": entry.get("at"),
                "run_number": entry.get("run_number"),
                "probability_pct": float(pct),
            }
        )
    if current_probability is not None:
        cur = float(current_probability)
        if not points or points[-1]["probability_pct"] != cur:
            points.append(
                {
                    "at": None,
                    "run_number": None,
                    "probability_pct": cur,
                }
            )
    return points[-max_points:]


def probability_delta(history: list[dict[str, Any]]) -> float | None:
    if len(history) < 2:
        return None
    return round(history[-1]["probability_pct"] - history[-2]["probability_pct"], 1)


def _parse_meta(parsed_trigger: dict[str, Any] | None) -> tuple[float | None, bool | None]:
    pt = parsed_trigger if isinstance(parsed_trigger, dict) else {}
    conf = pt.get("parse_confidence")
    llm = pt.get("llm_used")
    return (
        round(float(conf), 3) if conf is not None else None,
        bool(llm) if llm is not None else None,
    )


class InquiryDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_dashboard(
        self,
        *,
        status: str | None = None,
        case_id: int | None = None,
        search: str | None = None,
        mode: str | None = None,
        scheduled_only: bool = False,
        min_confidence: float | None = None,
        llm_only: bool = False,
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
        if mode in ("full", "lite"):
            q = q.where(ProspectiveInquiry.mode == mode)
        if search:
            term = search.strip()[:120]
            if term:
                q = q.where(func.lower(ProspectiveInquiry.question).contains(term.lower()))

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

            parsed = inquiry.parsed_trigger if isinstance(inquiry.parsed_trigger, dict) else {}
            parse_confidence, llm_used = _parse_meta(parsed)
            if min_confidence is not None:
                if parse_confidence is None or parse_confidence < min_confidence:
                    continue
            if llm_only and llm_used is not True:
                continue

            ans = inquiry.answer if isinstance(inquiry.answer, dict) else {}
            artifacts = inquiry.artifacts if isinstance(inquiry.artifacts, dict) else {}
            prob = ans.get("probability_pct")
            prob_history = extract_probability_history(artifacts, current_probability=prob)
            items.append(
                {
                    "id": inquiry.id,
                    "case_id": inquiry.case_id,
                    "case_name": case_name,
                    "question": (inquiry.question or "")[:120],
                    "mode": inquiry.mode,
                    "status": st,
                    "run_count": inquiry.run_count or 0,
                    "probability_pct": prob,
                    "probability_delta": probability_delta(prob_history),
                    "probability_history": prob_history,
                    "possibility": ans.get("possibility"),
                    "parse_confidence": parse_confidence,
                    "llm_used": llm_used,
                    "auto_rerun_enabled": scheduled,
                    "rerun_interval_hours": inquiry.rerun_interval_hours or 24,
                    "next_rerun_at": inquiry.next_rerun_at.isoformat() if inquiry.next_rerun_at else None,
                    "scheduled_due": due,
                    "wizard_project_id": artifacts.get("wizard_project_id"),
                    "report_meta": get_report_meta(inquiry),
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

    async def batch_schedule(
        self,
        inquiry_ids: list[int],
        *,
        enabled: bool,
        interval_hours: int = 24,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not inquiry_ids:
            raise ValueError("Calen IDs d'inquiry")
        if len(inquiry_ids) > limit:
            raise ValueError(f"Màxim {limit} inquiries per batch schedule")

        orchestrator = InquiryOrchestratorService(self.db)
        results: list[dict[str, Any]] = []
        for iid in inquiry_ids:
            try:
                summary = await orchestrator.set_schedule(
                    iid,
                    enabled=enabled,
                    interval_hours=interval_hours,
                )
                results.append({"inquiry_id": iid, **summary})
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
