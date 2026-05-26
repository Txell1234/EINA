"""Add optional institution_subtype and signal_type to extracted_statements.

Revision ID: 004_extract_typology_columns
Revises: 003_alert_monitor_columns
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_extract_typology_columns"
down_revision: Union[str, None] = "003_alert_monitor_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    cols = _columns("extracted_statements")
    if "institution_subtype" not in cols:
        op.add_column(
            "extracted_statements",
            sa.Column("institution_subtype", sa.String(), nullable=True),
        )
    if "signal_type" not in cols:
        op.add_column(
            "extracted_statements",
            sa.Column("signal_type", sa.String(), nullable=True),
        )


def downgrade() -> None:
    pass
