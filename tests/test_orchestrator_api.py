import os
# Force SQLite in-memory DB for tests to avoid requiring Postgres during CI/local runs
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)
login_response = client.post(
    "/auth/login",
    json={"username": "test-admin", "password": "test-only-password-123"},
)
assert login_response.status_code == 200
client.headers.update({"X-CSRF-Token": login_response.json()["csrf_token"]})


def test_orchestrate_api_endpoint():
    resp = client.post("/content/orchestrate", json={"topic": "EPFO नए नियम"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["topic"] == "EPFO नए नियम"
    assert "script" in body
    assert "seo" in body
    assert body["quality_check"]["passed"] is True
