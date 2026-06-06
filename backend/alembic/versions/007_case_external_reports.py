"""case external financial reports table

Revision ID: 007_case_external_reports
Revises: 006_scenario_milestones
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "007_case_external_reports"
down_revision = "006_scenario_milestones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_external_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_metrics", sa.JSON(), nullable=True),
        sa.Column("parse_status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_external_reports_case_id", "case_external_reports", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_case_external_reports_case_id", table_name="case_external_reports")
    op.drop_table("case_external_reports")
