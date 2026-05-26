"""
SQLite schema patches for dev DBs created before model changes.
create_all() does not add columns to existing tables.
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)

ALERT_MONITOR_COLUMNS: dict[str, str] = {
    "unread_count": "INTEGER DEFAULT 0",
    "case_id": "INTEGER",
}

PROSPECTIVE_SCENARIO_COLUMNS: dict[str, str] = {
    "possibility": "VARCHAR DEFAULT 'PLAUSIBLE'",
    "possibility_rationale": "TEXT DEFAULT ''",
}

REASONING_FRAMEWORK_COLUMNS: dict[str, str] = {
    "definition": "TEXT",
    "is_custom": "INTEGER DEFAULT 0",
    "user_id": "INTEGER",
    "updated_at": "DATETIME",
}


def _sqlite_columns(conn: Connection, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def apply_sqlite_schema_patches(conn: Connection) -> list[str]:
    """Add missing alert_monitors columns. Returns list of applied patches."""
    applied: list[str] = []
    inspector = inspect(conn)
    if not inspector.has_table("alert_monitors"):
        return applied

    existing = _sqlite_columns(conn, "alert_monitors")
    for col, ddl in ALERT_MONITOR_COLUMNS.items():
        if col in existing:
            continue
        conn.execute(text(f"ALTER TABLE alert_monitors ADD COLUMN {col} {ddl}"))
        applied.append(f"alert_monitors.{col}")
        logger.info("Schema patch: added alert_monitors.%s", col)

    return applied


def apply_prospective_scenario_patches(conn: Connection) -> list[str]:
    """Add possibility columns to prospective_scenarios."""
    applied: list[str] = []
    inspector = inspect(conn)
    if not inspector.has_table("prospective_scenarios"):
        return applied

    existing = _sqlite_columns(conn, "prospective_scenarios")
    for col, ddl in PROSPECTIVE_SCENARIO_COLUMNS.items():
        if col in existing:
            continue
        conn.execute(text(f"ALTER TABLE prospective_scenarios ADD COLUMN {col} {ddl}"))
        applied.append(f"prospective_scenarios.{col}")
        logger.info("Schema patch: added prospective_scenarios.%s", col)

    return applied


def apply_reasoning_framework_patches(conn: Connection) -> list[str]:
    """Add extended columns to reasoning_frameworks."""
    applied: list[str] = []
    inspector = inspect(conn)
    if not inspector.has_table("reasoning_frameworks"):
        return applied

    existing = _sqlite_columns(conn, "reasoning_frameworks")
    for col, ddl in REASONING_FRAMEWORK_COLUMNS.items():
        if col in existing:
            continue
        conn.execute(text(f"ALTER TABLE reasoning_frameworks ADD COLUMN {col} {ddl}"))
        applied.append(f"reasoning_frameworks.{col}")
        logger.info("Schema patch: added reasoning_frameworks.%s", col)

    return applied


def run_schema_patches_sync(conn: Connection) -> None:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        conn.execute(text("PRAGMA busy_timeout=30000"))
        patches = apply_sqlite_schema_patches(conn)
        patches.extend(apply_prospective_scenario_patches(conn))
        patches.extend(apply_reasoning_framework_patches(conn))
        if patches:
            logger.info("Schema patches applied: %s", ", ".join(patches))
