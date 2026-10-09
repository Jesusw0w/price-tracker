"""add products.unavailable_since

Revision ID: a41c6e0d9b27
Revises: 7f3e1b9a2c4d
Create Date: 2026-10-09 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a41c6e0d9b27"
down_revision: str | Sequence[str] | None = "7f3e1b9a2c4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("unavailable_since", sa.Date()))


def downgrade() -> None:
    op.drop_column("products", "unavailable_since")
