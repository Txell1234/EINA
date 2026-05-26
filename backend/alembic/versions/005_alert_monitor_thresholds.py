"""Add optional threshold columns to alert_monitors.

Revision ID: 005_alert_monitor_thresholds
Revises: 004_extract_typology_columns
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_alert_monitor_thresholds"
down_revision: Union[str, None] = "004_extract_typology_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    cols = _columns("alert_monitors")
    if "lookback_days" not in cols:
        op.add_column("alert_monitors", sa.Column("lookback_days", sa.Integer(), nullable=True))
    if "horizon_label" not in cols:
        op.add_column("alert_monitors", sa.Column("horizon_label", sa.String(), nullable=True))
    if "min_match_score" not in cols:
        op.add_column("alert_monitors", sa.Column("min_match_score", sa.Float(), nullable=True))
    if "min_keywords_matched" not in cols:
        op.add_column(
            "alert_monitors",
            sa.Column("min_keywords_matched", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    pass
