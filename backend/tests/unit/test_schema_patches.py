"""SQLite schema patches for legacy dev databases."""
import pytest
from sqlalchemy import create_engine, text

from app.schema_patches import run_schema_patches_sync


@pytest.mark.unit
def test_schema_patches_add_extracted_statement_columns():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE extracted_statements (
                    id INTEGER PRIMARY KEY,
                    case_id INTEGER,
                    actor VARCHAR
                )
                """
            )
        )
        run_schema_patches_sync(conn)
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(extracted_statements)"))}
    assert "institution_subtype" in cols
    assert "signal_type" in cols


@pytest.mark.unit
def test_schema_patches_add_alert_monitor_threshold_columns():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE alert_monitors (
                    id INTEGER PRIMARY KEY,
                    indicator TEXT
                )
                """
            )
        )
        run_schema_patches_sync(conn)
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(alert_monitors)"))}
    assert "lookback_days" in cols
    assert "min_match_score" in cols
