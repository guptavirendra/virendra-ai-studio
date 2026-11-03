import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

# Use a local SQLite test database for pytest so schema creation is preserved across connections.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SESSION_SECRET_KEY"] = "test-only-session-secret-key-that-is-long-enough"
os.environ["BOOTSTRAP_ADMIN_USERNAME"] = "test-admin"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "test-only-password-123"
os.environ["SESSION_COOKIE_SECURE"] = "false"

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

command.upgrade(Config(str(ROOT / "alembic.ini")), "head")

from app.models import Base, LoginRateLimit, engine

Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    connection.execute(LoginRateLimit.__table__.delete())
