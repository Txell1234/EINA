"""JSON array filters compatible with SQLite and MySQL/PostgreSQL."""
from __future__ import annotations

from sqlalchemy import String, cast, func
from sqlalchemy.sql.elements import ColumnElement

from app.config import settings


def json_array_contains(column, value: str) -> ColumnElement[bool]:
    """Filter rows where a JSON array column contains `value` (string match)."""
    quoted = f'"{value}"'
    if "sqlite" in settings.DATABASE_URL.lower():
        return cast(column, String).like(f"%{quoted}%")
    return func.json_contains(column, func.json_quote(value))


def json_array_contains_column(array_column, value_column) -> ColumnElement[bool]:
    """Join/filter when the sought value is another SQL column."""
    if "sqlite" in settings.DATABASE_URL.lower():
        return cast(array_column, String).like(func.concat('%"', value_column, '"%'))
    return func.json_contains(array_column, func.json_quote(value_column))
