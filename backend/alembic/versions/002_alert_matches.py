"""Add alert_matches table and monitor columns.

Revision ID: 002_alert_matches
Revises: 001_baseline
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_alert_matches"
down_revision: Union[str, None] = "001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sys
    from pathlib import Path

    backend = Path(__file__).resolve().parents[2]
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    from app.database import Base
    import models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    pass
