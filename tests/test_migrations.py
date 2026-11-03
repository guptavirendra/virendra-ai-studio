import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database_url: str, *arguments: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["SESSION_SECRET_KEY"] = "migration-test-session-key-that-is-long-enough"
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), *arguments],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_baseline_migration_creates_fresh_schema_and_is_repeatable(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"

    run_alembic(database_url, "upgrade", "head")
    run_alembic(database_url, "upgrade", "head")
    run_alembic(database_url, "check")

    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "analytics",
        "content_items",
        "learning_signals",
        "login_rate_limits",
        "users",
    }


def test_baseline_migration_adopts_existing_tables_without_losing_rows(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE content_items "
                "(id INTEGER PRIMARY KEY, topic TEXT NOT NULL, source TEXT NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO content_items (id, topic, source) VALUES (9, 'Saved content', 'legacy')")
        )
        connection.execute(
            text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(64) NOT NULL, "
                "password_hash VARCHAR(256) NOT NULL, role VARCHAR(16) NOT NULL, "
                "is_active BOOLEAN NOT NULL, created_at TIMESTAMP NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, is_active, created_at) "
                "VALUES (7, 'legacy-admin', 'legacy-hash', 'admin', 1, CURRENT_TIMESTAMP)"
            )
        )

    run_alembic(database_url, "upgrade", "head")

    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, topic, source FROM content_items WHERE id = 9")
        ).one()
        user = connection.execute(
            text("SELECT id, username, session_version FROM users WHERE id = 7")
        ).one()
    assert row == (9, "Saved content", "legacy")
    assert user == (7, "legacy-admin", 0)
    assert "users" in inspect(engine).get_table_names()
