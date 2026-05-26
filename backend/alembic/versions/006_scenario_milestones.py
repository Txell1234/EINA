"""Add scenario_milestones table.

Revision ID: 006_scenario_milestones
Revises: 005_alert_monitor_thresholds
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_scenario_milestones"
down_revision: Union[str, None] = "005_alert_monitor_thresholds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    bind = op.get_bind()
    tables = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }
    if "scenario_milestones" in tables:
        return
    op.create_table(
        "scenario_milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0"),
        sa.Column("time_label", sa.String(), server_default=""),
        sa.Column("horizon_months", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("trigger_indicator", sa.Text(), server_default=""),
        sa.Column("reversibility", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.ForeignKeyConstraint(["scenario_id"], ["prospective_scenarios.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_scenario_milestones_scenario_id",
        "scenario_milestones",
        ["scenario_id"],
    )


def downgrade() -> None:
    pass
