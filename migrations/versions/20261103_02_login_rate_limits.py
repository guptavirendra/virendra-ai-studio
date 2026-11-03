"""Add persistent login rate-limit buckets.

Revision ID: 20261103_02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261103_02"
down_revision = "20261103_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "login_rate_limits" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "login_rate_limits",
            sa.Column("key_hash", sa.String(length=64), primary_key=True),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("window_started_at", sa.DateTime(), nullable=False),
        )
    existing_indexes = {
        index["name"] for index in inspect(op.get_bind()).get_indexes("login_rate_limits")
    }
    if "ix_login_rate_limits_window_started_at" not in existing_indexes:
        op.create_index(
            "ix_login_rate_limits_window_started_at",
            "login_rate_limits",
            ["window_started_at"],
        )


def downgrade() -> None:
    op.drop_table("login_rate_limits")
