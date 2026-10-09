"""add product owners, sessions and user settings

Revision ID: 7f3e1b9a2c4d
Revises: 5d2a9c41e7b3
Create Date: 2026-10-08 18:00:00.000000

Existing products need an owner: ``alembic -x owner=<cognito sub> upgrade head``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "7f3e1b9a2c4d"
down_revision: str | Sequence[str] | None = "5d2a9c41e7b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    owner = context.get_x_argument(as_dictionary=True).get("owner")
    if not owner and op.get_bind().scalar(sa.text("SELECT count(*) FROM products")):
        raise RuntimeError(
            "Products exist; give them an owner with -x owner=<cognito sub>"
        )

    op.add_column("products", sa.Column("owner_id", sa.String(length=64)))
    op.add_column(
        "products",
        sa.Column("public", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    if owner:
        op.execute(
            sa.text("UPDATE products SET owner_id = :owner").bindparams(owner=owner)
        )
    op.alter_column("products", "owner_id", nullable=False)
    op.drop_constraint("products_url_key", "products", type_="unique")
    op.create_unique_constraint(
        "products_owner_id_url_key", "products", ["owner_id", "url"]
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_sub", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_user_sub", "sessions", ["user_sub"])
    op.create_table(
        "user_settings",
        sa.Column("user_sub", sa.String(length=64), primary_key=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    # No policies, so Supabase's public REST API can't reach them; the app's owner
    # role bypasses RLS
    for table in ("sessions", "user_settings"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index("ix_sessions_user_sub", table_name="sessions")
    op.drop_table("sessions")
    # Fails if two users track the same URL, which the old schema can't hold
    op.drop_constraint("products_owner_id_url_key", "products", type_="unique")
    op.create_unique_constraint("products_url_key", "products", ["url"])
    op.drop_column("products", "public")
    op.drop_column("products", "owner_id")
