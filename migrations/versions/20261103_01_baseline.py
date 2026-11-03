"""Create application tables without replacing existing data.

Revision ID: 20261103_01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261103_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(length=64), nullable=False),
            sa.Column("password_hash", sa.String(length=256), nullable=False),
            sa.Column("role", sa.String(length=16), nullable=False, server_default="member"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if "content_items" not in existing_tables:
        op.create_table(
            "content_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("topic", sa.Text(), nullable=False),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("competition", sa.String(), nullable=True, server_default="medium"),
            sa.Column("estimated_views", sa.String(), nullable=True, server_default="medium"),
            sa.Column("script", sa.Text()),
            sa.Column("voice_file", sa.Text()),
            sa.Column("thumbnail_path", sa.Text()),
            sa.Column("video_path", sa.Text()),
            sa.Column("seo_title", sa.Text()),
            sa.Column("seo_description", sa.Text()),
            sa.Column("hashtags", sa.Text()),
            sa.Column("status", sa.String(), nullable=True, server_default="draft"),
            sa.Column("publish_target", sa.String()),
            sa.Column("approved", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("published", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if "analytics" not in existing_tables:
        op.create_table(
            "analytics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_items.id")),
            sa.Column("views", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("ctr", sa.Numeric(5, 2), nullable=True, server_default="0"),
            sa.Column("retention", sa.Numeric(5, 2), nullable=True, server_default="0"),
            sa.Column("subscribers", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("rpm", sa.Numeric(10, 2), nullable=True, server_default="0"),
            sa.Column("top_keywords", sa.Text()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    if "learning_signals" not in existing_tables:
        op.create_table(
            "learning_signals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_items.id")),
            sa.Column("title_style", sa.Text()),
            sa.Column("thumbnail_style", sa.Text()),
            sa.Column("best_upload_time", sa.Text()),
            sa.Column("topic_category", sa.Text()),
            sa.Column("ctr", sa.Numeric(5, 2), nullable=True, server_default="0"),
            sa.Column("retention", sa.Numeric(5, 2), nullable=True, server_default="0"),
            sa.Column("rpm", sa.Numeric(10, 2), nullable=True, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    indexes = {
        "users": [("ix_users_id", "id", False), ("ix_users_username", "username", True)],
        "content_items": [("ix_content_items_id", "id", False)],
        "analytics": [("ix_analytics_id", "id", False)],
        "learning_signals": [("ix_learning_signals_id", "id", False)],
    }
    for table_name, table_indexes in indexes.items():
        existing_indexes = {index["name"] for index in inspect(bind).get_indexes(table_name)}
        for index_name, column_name, unique in table_indexes:
            if index_name not in existing_indexes:
                op.create_index(index_name, table_name, [column_name], unique=unique)


def downgrade() -> None:
    # This baseline may represent tables that predate Alembic; dropping them is unsafe.
    pass
