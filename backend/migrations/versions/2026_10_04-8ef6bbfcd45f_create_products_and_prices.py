"""create products and prices

Revision ID: 8ef6bbfcd45f
Revises:
Create Date: 2026-10-04 09:08:25.713812
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8ef6bbfcd45f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("tracked", sa.Boolean(), nullable=False),
        sa.Column("added_at", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("asin"),
    )
    op.create_table(
        "prices",
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["asin"], ["products.asin"]),
        sa.PrimaryKeyConstraint("asin", "date"),
    )
    # No policies, so Supabase's public REST API can't reach these tables.
    # The app connects as the owner role, which bypasses RLS.
    for table in ("products", "prices", "alembic_version"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("prices")
    op.drop_table("products")
