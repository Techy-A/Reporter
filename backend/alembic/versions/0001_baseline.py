"""Baseline: all tables as of Phase 2.

Creates any table that is missing and leaves existing ones alone, so it is safe on a database that was
set up before Alembic. Later schema changes go in new numbered files: `alembic revision -m "what changed"`.

Revision ID: 0001
Revises:
"""
from alembic import op

from peoplepilot import models  # noqa: F401
from peoplepilot.db import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    raise RuntimeError("The baseline cannot be undone; restore from a backup instead.")
