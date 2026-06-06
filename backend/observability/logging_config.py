"""Structured JSON logging (Loki / Promtail compatible)."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from observability.correlation import correlation_log_extra


class StructuredJsonFormatter(logging.Formatter):
    """One JSON object per log line for Loki ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "eina-q2fs",
        }
        payload.update(correlation_log_extra())

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key in ("phase", "inquiry_id", "parse_confidence", "llm_used", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        return json.dumps(payload, ensure_ascii=False)


def setup_structured_logging(*, enabled: bool = True, level: int = logging.INFO) -> None:
    if not enabled:
        return

    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root.handlers = [handler]
    root.setLevel(level)
