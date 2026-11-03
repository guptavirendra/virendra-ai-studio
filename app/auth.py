"""Authentication helpers for browser sessions and local user accounts."""

import hashlib
import hmac
import math
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import LoginRateLimit, User, engine

PASSWORD_ITERATIONS = 600_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
LOGIN_ATTEMPT_LIMIT = 10
LOGIN_ATTEMPT_WINDOW = timedelta(minutes=15)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_auth_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hash = password_hash.split("$")
        iterations = int(iterations)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 1_000_000:
            return False
        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculated_hash.hex(), expected_hash)


def _login_rate_limit_key(username: str, secret_key: str) -> str:
    normalized_username = username.strip().casefold().encode("utf-8")
    return hmac.new(
        secret_key.encode("utf-8"),
        b"login-rate-limit:" + normalized_username,
        hashlib.sha256,
    ).hexdigest()


def consume_login_attempt(
    db: Session,
    username: str,
    secret_key: str,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - LOGIN_ATTEMPT_WINDOW
    key_hash = _login_rate_limit_key(username, secret_key)
    db.query(LoginRateLimit).filter(
        LoginRateLimit.window_started_at <= cutoff
    ).delete(synchronize_session=False)
    expired_window = LoginRateLimit.window_started_at <= cutoff
    updated = (
        db.query(LoginRateLimit)
        .filter(LoginRateLimit.key_hash == key_hash)
        .update(
            {
                LoginRateLimit.attempts: case(
                    (expired_window, 1),
                    else_=LoginRateLimit.attempts + 1,
                ),
                LoginRateLimit.window_started_at: case(
                    (expired_window, now),
                    else_=LoginRateLimit.window_started_at,
                ),
            },
            synchronize_session=False,
        )
    )
    if not updated:
        db.add(
            LoginRateLimit(
                key_hash=key_hash,
                attempts=1,
                window_started_at=now,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return consume_login_attempt(db, username, secret_key, now)
        return 1

    db.commit()
    return db.query(LoginRateLimit.attempts).filter(
        LoginRateLimit.key_hash == key_hash
    ).scalar()


def clear_login_attempts(db: Session, username: str, secret_key: str) -> None:
    key_hash = _login_rate_limit_key(username, secret_key)
    db.query(LoginRateLimit).filter(LoginRateLimit.key_hash == key_hash).delete()
    db.commit()


def login_retry_after(
    db: Session,
    username: str,
    secret_key: str,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    key_hash = _login_rate_limit_key(username, secret_key)
    window_started_at = db.query(LoginRateLimit.window_started_at).filter(
        LoginRateLimit.key_hash == key_hash
    ).scalar()
    if window_started_at is None:
        return 1
    return max(1, math.ceil((window_started_at + LOGIN_ATTEMPT_WINDOW - now).total_seconds()))


def validate_new_user(username: str, password: str, role: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username must be 3-64 characters using letters, numbers, '.', '_' or '-'")
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if len(password) > 128:
        raise ValueError("Password must be no more than 128 characters")
    if role not in {"admin", "member"}:
        raise ValueError("Role must be admin or member")


def create_user(db: Session, username: str, password: str, role: str = "member") -> User:
    username = username.strip()
    validate_new_user(username, password, role)
    if db.query(User).filter(User.username == username).first():
        raise ValueError("Username already exists")

    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, user: User, password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")
    if len(password) > 128:
        raise ValueError("Password must be no more than 128 characters")
    user.password_hash = hash_password(password)
    user.session_version += 1
    db.commit()


def bootstrap_admin(username: str | None, password: str | None) -> None:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        if db.query(User.id).first():
            return
        if not username or not password:
            raise RuntimeError(
                "No users exist. Configure BOOTSTRAP_ADMIN_USERNAME and "
                "BOOTSTRAP_ADMIN_PASSWORD to create the first administrator."
            )
        try:
            create_user(db, username, password, "admin")
        except ValueError as exc:
            raise RuntimeError(f"Unable to create the bootstrap administrator: {exc}") from exc


def require_user(request: Request, db: Session = Depends(get_auth_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Authentication required")

    if request.session.get("session_version") != user.session_version:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Session has been revoked")

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        expected = request.session.get("csrf_token")
        supplied = request.headers.get("x-csrf-token")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user
