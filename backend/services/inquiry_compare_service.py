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
