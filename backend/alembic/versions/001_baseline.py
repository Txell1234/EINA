"""Baseline schema — create_all per instal·lacions noves PostgreSQL.

Instal·lacions existents (SQLite dev amb create_all): alembic stamp head

Revision ID: 001_baseline
Revises:
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "001_baseline"
down_revision: Union[str, None] = None
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
