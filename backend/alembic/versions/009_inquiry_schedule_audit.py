"""inquiry auto-rerun schedule columns

Revision ID: 009_inquiry_schedule
Revises: 008_prospective_inquiries
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "009_inquiry_schedule"
down_revision = "008_prospective_inquiries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "prospective_inquiries",
        sa.Column("auto_rerun_enabled", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "prospective_inquiries",
        sa.Column("rerun_interval_hours", sa.Integer(), nullable=True, server_default="24"),
    )
    op.add_column(
        "prospective_inquiries",
        sa.Column("next_rerun_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "prospective_inquiries",
        sa.Column("last_rerun_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "prospective_inquiries",
        sa.Column("run_count", sa.Integer(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("prospective_inquiries", "run_count")
    op.drop_column("prospective_inquiries", "last_rerun_at")
    op.drop_column("prospective_inquiries", "next_rerun_at")
    op.drop_column("prospective_inquiries", "rerun_interval_hours")
    op.drop_column("prospective_inquiries", "auto_rerun_enabled")
