"""prospective inquiries Q2FS table

Revision ID: 008_prospective_inquiries
Revises: 007_case_external_reports
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "008_prospective_inquiries"
down_revision = "007_case_external_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prospective_inquiries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("parsed_trigger", sa.JSON(), nullable=True),
        sa.Column("inquiry_scope", sa.JSON(), nullable=True),
        sa.Column("steps_log", sa.JSON(), nullable=True),
        sa.Column("scope_audit", sa.JSON(), nullable=True),
        sa.Column("artifacts", sa.JSON(), nullable=True),
        sa.Column("answer", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("include_financial", sa.Integer(), nullable=True),
        sa.Column("financial_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prospective_inquiries_case_id", "prospective_inquiries", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_prospective_inquiries_case_id", table_name="prospective_inquiries")
    op.drop_table("prospective_inquiries")
