"""Immutable audit trail for prospective inquiry runs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class InquiryAuditService:
    def __init__(self, artifacts: dict[str, Any] | None = None):
        self._artifacts = dict(artifacts or {})

    @property
    def artifacts(self) -> dict[str, Any]:
        return self._artifacts

    def run_number(self) -> int:
        return int(self._artifacts.get("run_number") or 0)

    def begin_run(self) -> int:
        n = self.run_number() + 1
        self._artifacts["run_number"] = n
        self._append(
            "run_started",
            {"run_number": n},
        )
        return n

    def log_step(self, step: str, *, ok: bool = True, detail: dict[str, Any] | None = None) -> None:
        self._append(
            "step_completed",
            {"step": step, "ok": ok, **(detail or {})},
        )

    def log_event(self, event: str, detail: dict[str, Any] | None = None) -> None:
        self._append(event, detail or {})

    def trail(self) -> list[dict[str, Any]]:
        return list(self._artifacts.get("audit_trail") or [])

    def _append(self, event: str, detail: dict[str, Any]) -> None:
        trail = list(self._artifacts.get("audit_trail") or [])
        trail.append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "run_number": self.run_number() or 1,
                **detail,
            }
        )
        self._artifacts["audit_trail"] = trail[-500:]
