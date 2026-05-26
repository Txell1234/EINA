"""Add alert_monitors columns missing from older SQLite dev DBs.

Revision ID: 003_alert_monitor_columns
Revises: 002_alert_matches
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_alert_monitor_columns"
down_revision: Union[str, None] = "002_alert_matches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade() -> None:
    if not op.get_bind().dialect.name == "sqlite":
        return
    cols = _columns("alert_monitors")
    if "unread_count" not in cols:
        op.add_column(
            "alert_monitors",
            sa.Column("unread_count", sa.Integer(), server_default="0"),
        )
    if "case_id" not in cols:
        op.add_column("alert_monitors", sa.Column("case_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    pass
