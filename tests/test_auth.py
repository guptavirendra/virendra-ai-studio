from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.auth import LOGIN_ATTEMPT_LIMIT


ADMIN_CREDENTIALS = {"username": "test-admin", "password": "test-only-password-123"}


def authenticated_client(username: str, password: str) -> TestClient:
    client = TestClient(app)
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    client.headers.update({"X-CSRF-Token": response.json()["csrf_token"]})
    return client


def test_content_api_requires_authentication_and_login_sets_secure_session_cookie():
    anonymous = TestClient(app)
    assert anonymous.get("/content").status_code == 401

    client = authenticated_client(**ADMIN_CREDENTIALS)
    cookie = client.cookies.get("studio_session")
    assert cookie
    cookie_header = client.get("/auth/me").headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=strict" in cookie_header

    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"


def test_mutations_require_csrf_and_admin_provisions_member_accounts():
    no_csrf = TestClient(app)
    login_response = no_csrf.post("/auth/login", json=ADMIN_CREDENTIALS)
    assert login_response.status_code == 200
    assert no_csrf.post(
        "/content/generate",
        json={"topic": "CSRF check", "source": "test"},
    ).status_code == 403

    admin = authenticated_client(**ADMIN_CREDENTIALS)
    member_username = f"team-{uuid4().hex[:8]}"
    created = admin.post(
        "/auth/users",
        json={"username": member_username, "password": "member-password-123", "role": "member"},
    )
    assert created.status_code == 201
    assert created.json()["username"] == member_username
    assert created.json()["role"] == "member"

    member = authenticated_client(member_username, "member-password-123")
    assert member.get("/content").status_code == 200
    assert member.post(
        "/auth/users",
        json={"username": f"second-{uuid4().hex[:8]}", "password": "member-password-456", "role": "member"},
    ).status_code == 403


def test_login_rejects_invalid_password_without_disclosing_user_existence():
    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"username": "test-admin", "password": "incorrect-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_login_rate_limit_returns_retry_after_after_ten_attempts():
    client = TestClient(app)
    username = f"missing-{uuid4().hex[:12]}"

    for _ in range(LOGIN_ATTEMPT_LIMIT):
        response = client.post(
            "/auth/login",
            json={"username": username, "password": "incorrect-password"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json={"username": username, "password": "incorrect-password"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0


def test_successful_login_clears_failed_attempts():
    client = TestClient(app)
    for _ in range(3):
        response = client.post(
            "/auth/login",
            json={"username": ADMIN_CREDENTIALS["username"], "password": "incorrect-password"},
        )
        assert response.status_code == 401

    successful = client.post("/auth/login", json=ADMIN_CREDENTIALS)
    assert successful.status_code == 200

    for _ in range(LOGIN_ATTEMPT_LIMIT - 1):
        response = client.post(
            "/auth/login",
            json={"username": ADMIN_CREDENTIALS["username"], "password": "incorrect-password"},
        )
        assert response.status_code == 401
    assert client.post("/auth/login", json=ADMIN_CREDENTIALS).status_code == 200


def test_admin_can_deactivate_and_reactivate_user_and_old_session_stays_revoked():
    admin = authenticated_client(**ADMIN_CREDENTIALS)
    username = f"lifecycle-{uuid4().hex[:8]}"
    created = admin.post(
        "/auth/users",
        json={"username": username, "password": "member-password-123", "role": "member"},
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    member = authenticated_client(username, "member-password-123")

    deactivated = admin.patch(f"/auth/users/{user_id}/active", json={"is_active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert member.get("/auth/me").status_code == 401

    reactivated = admin.patch(f"/auth/users/{user_id}/active", json={"is_active": True})
    assert reactivated.status_code == 200
    assert member.get("/auth/me").status_code == 401
    assert authenticated_client(username, "member-password-123").get("/auth/me").status_code == 200


def test_admin_password_reset_revokes_existing_sessions_and_password():
    admin = authenticated_client(**ADMIN_CREDENTIALS)
    username = f"reset-{uuid4().hex[:8]}"
    created = admin.post(
        "/auth/users",
        json={"username": username, "password": "member-password-123", "role": "member"},
    )
    user_id = created.json()["id"]
    old_session = authenticated_client(username, "member-password-123")

    reset = admin.post(
        f"/auth/users/{user_id}/password",
        json={"password": "replacement-password-456"},
    )
    assert reset.status_code == 200
    assert old_session.get("/auth/me").status_code == 401
    assert TestClient(app).post(
        "/auth/login",
        json={"username": username, "password": "member-password-123"},
    ).status_code == 401
    assert authenticated_client(username, "replacement-password-456").get("/auth/me").status_code == 200


def test_admin_cannot_deactivate_self():
    admin = authenticated_client(**ADMIN_CREDENTIALS)
    admin_user = admin.get("/auth/me").json()["user"]

    self_deactivation = admin.patch(
        f"/auth/users/{admin_user['id']}/active",
        json={"is_active": False},
    )
    assert self_deactivation.status_code == 400
