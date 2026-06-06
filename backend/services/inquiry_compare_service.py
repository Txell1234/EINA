"""Compare inquiry runs — delta between answers (deterministic)."""
from __future__ import annotations

from typing import Any


def compare_inquiry_answers(
    previous: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> dict[str, Any]:
    prev = previous or {}
    curr = current or {}

    prev_prob = prev.get("probability_pct")
    curr_prob = curr.get("probability_pct")
    prob_delta = None
    if isinstance(prev_prob, (int, float)) and isinstance(curr_prob, (int, float)):
        prob_delta = round(float(curr_prob) - float(prev_prob), 1)

    prev_poss = prev.get("possibility")
    curr_poss = curr.get("possibility")
    poss_changed = prev_poss != curr_poss if prev_poss and curr_poss else False

    prev_reasoning = {r.get("conclusion") for r in (prev.get("reasoning") or []) if r.get("conclusion")}
    curr_reasoning = {r.get("conclusion") for r in (curr.get("reasoning") or []) if r.get("conclusion")}

    return {
        "methodology": "deterministic_answer_diff",
        "probability_delta": prob_delta,
        "possibility_changed": poss_changed,
        "previous_possibility": prev_poss,
        "current_possibility": curr_poss,
        "new_conclusions": sorted(curr_reasoning - prev_reasoning),
        "removed_conclusions": sorted(prev_reasoning - curr_reasoning),
        "confidence_delta": (
            round(float(curr.get("confidence", 0)) - float(prev.get("confidence", 0)), 1)
            if curr.get("confidence") is not None and prev.get("confidence") is not None
            else None
        ),
    }


def build_case_inquiry_comparison(rows: list[Any]) -> dict[str, Any]:
    """Build chronological comparison table for inquiries on the same case."""
    sorted_rows = sorted(
        rows,
        key=lambda r: (r.created_at.isoformat() if getattr(r, "created_at", None) else ""),
    )
    items: list[dict[str, Any]] = []
    prev_answer: dict[str, Any] | None = None
    for row in sorted_rows:
        ans = row.answer if isinstance(getattr(row, "answer", None), dict) else {}
        artifacts = row.artifacts if isinstance(getattr(row, "artifacts", None), dict) else {}
        item = {
            "id": row.id,
            "question": (row.question or "")[:120],
            "mode": row.mode,
            "status": row.status,
            "run_count": getattr(row, "run_count", 0) or 0,
            "probability_pct": ans.get("probability_pct"),
            "possibility": ans.get("possibility"),
            "confidence": ans.get("confidence"),
            "financial_mode": ans.get("financial_mode"),
            "completed_at": row.completed_at.isoformat() if getattr(row, "completed_at", None) else None,
            "wizard_project_id": artifacts.get("wizard_project_id"),
            "diff_vs_previous": compare_inquiry_answers(prev_answer, ans) if prev_answer else None,
        }
        items.append(item)
        if ans:
            prev_answer = ans

    latest_id = sorted_rows[-1].id if sorted_rows else None
    prob_series = [
        {"id": i["id"], "probability_pct": i["probability_pct"]}
        for i in items
        if i.get("probability_pct") is not None
    ]
    return {
        "methodology": "deterministic_case_comparison",
        "count": len(items),
        "latest_id": latest_id,
        "probability_series": prob_series,
        "items": items,
    }
