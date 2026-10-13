"""key products by id instead of ASIN

Revision ID: 5d2a9c41e7b3
Revises: c908f0b83664
Create Date: 2026-10-07 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5d2a9c41e7b3"
down_revision: str | Sequence[str] | None = "c908f0b83664"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres numbers the existing rows when an identity column is added
    op.add_column(
        "products", sa.Column("id", sa.Integer(), sa.Identity(), nullable=False)
    )
    op.add_column("products", sa.Column("url", sa.String(length=2048)))
    op.add_column("products", sa.Column("domain", sa.String()))
    op.add_column("products", sa.Column("currency", sa.String(length=3)))
    op.execute(
        "UPDATE products SET url = 'https://www.amazon.es/dp/' || asin,"
        " domain = 'amazon.es', currency = 'EUR'"
    )
    op.alter_column("products", "url", nullable=False)
    op.alter_column("products", "domain", nullable=False)
    op.create_unique_constraint("products_url_key", "products", ["url"])

    for table in ("prices", "refreshes"):
        op.add_column(table, sa.Column("product_id", sa.Integer()))
    op.execute(
        "UPDATE prices SET product_id = products.id FROM products"
        " WHERE products.asin = prices.asin"
    )
    op.execute(
        "UPDATE refreshes SET product_id = products.id FROM products"
        " WHERE products.asin = refreshes.asin"
    )
    for table in ("prices", "refreshes"):
        op.alter_column(table, "product_id", nullable=False)
        op.drop_constraint(f"{table}_asin_fkey", table, type_="foreignkey")
        op.drop_constraint(f"{table}_pkey", table, type_="primary")
        op.drop_column(table, "asin")

    op.drop_constraint("products_pkey", "products", type_="primary")
    op.drop_column("products", "asin")
    op.create_primary_key("products_pkey", "products", ["id"])
    op.create_primary_key("prices_pkey", "prices", ["product_id", "date"])
    op.create_primary_key("refreshes_pkey", "refreshes", ["product_id"])
    for table in ("prices", "refreshes"):
        op.create_foreign_key(
            f"{table}_product_id_fkey", table, "products", ["product_id"], ["id"]
        )


def downgrade() -> None:
    # Products from other shops have no ASIN to go back to
    raise NotImplementedError("Restore the pre-migration backup instead")
