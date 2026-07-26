"""Create the asynchronous API migration baseline.

Revision ID: 20260724_0001
Revises:
Create Date: 2026-07-24
"""

from typing import Sequence


revision: str = "20260724_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The initial schema has no application tables."""


def downgrade() -> None:
    """The initial schema has no application tables."""
