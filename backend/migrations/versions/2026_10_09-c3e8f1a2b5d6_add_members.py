"""add members, approved by the owner

Revision ID: c3e8f1a2b5d6
Revises: a41c6e0d9b27
Create Date: 2026-10-09 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3e8f1a2b5d6"
down_revision: str | Sequence[str] | None = "a41c6e0d9b27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("sub", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", native_enum=False),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
    )
    # No policies, so Supabase's public REST API can't reach it
    op.execute("ALTER TABLE members ENABLE ROW LEVEL SECURITY")
    # Everyone who signed in before approvals existed was invited by the owner
    op.execute(
        "INSERT INTO members (sub, email, status, requested_at) "
        "SELECT user_sub, max(email), 'approved', CURRENT_TIMESTAMP FROM sessions "
        "GROUP BY user_sub"
    )


def downgrade() -> None:
    op.drop_table("members")
