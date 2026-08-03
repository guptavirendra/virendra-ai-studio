import os
import sys
from pathlib import Path

# Use a local SQLite test database for pytest so schema creation is preserved across connections.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
