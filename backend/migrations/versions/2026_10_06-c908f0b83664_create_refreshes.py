"""create refreshes

Revision ID: c908f0b83664
Revises: 8ef6bbfcd45f
Create Date: 2026-10-06 13:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c908f0b83664"
down_revision: str | Sequence[str] | None = "8ef6bbfcd45f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refreshes",
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", native_enum=False),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["asin"], ["products.asin"]),
        sa.PrimaryKeyConstraint("asin"),
    )
    # Same as products and prices: no policies, so the Supabase REST API can't reach it
    op.execute("ALTER TABLE refreshes ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("refreshes")
