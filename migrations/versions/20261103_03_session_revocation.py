"""Add user session versions for account-level revocation.

Revision ID: 20261103_03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261103_03"
down_revision = "20261103_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "session_version" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "session_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "session_version" in columns:
        op.drop_column("users", "session_version")
