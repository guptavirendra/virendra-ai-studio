"""FastAPI backend for Virendra AI Studio content workflows."""

from pathlib import Path
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    LOGIN_ATTEMPT_LIMIT,
    bootstrap_admin,
    clear_login_attempts,
    consume_login_attempt,
    create_user,
    login_retry_after,
    require_admin,
    require_user,
    reset_user_password,
    verify_password,
)
from app.config import settings
from app.media_access import verify_media_token
from app.models import ContentItem, User, engine
from app.schemas import (
    AnalyticsCreate,
    ContentCreate,
    ContentOut,
    LearningSignalCreate,
    PublishPayload,
    PublishResultOut,
    YouTubeUploadPayload,
)
from app.services import (
    approve_content,
    create_content_job,
    create_content_job_with_ai,
    generate_ai_content,
    publish_content,
    upload_youtube_video,
    render_content_video,
    add_analytics,
    add_learning_signal,
    get_content_review_queue,
    get_content_analytics,
    get_content_learning_signals,
    list_content_items,
    get_content_summary,
)

from app.orchestrator import orchestrate_content
from app.publishers import (
    FacebookPublishError,
    InstagramPublishError,
    PublisherConfigurationError,
    TelegramPublishError,
)

if len(settings.SESSION_SECRET_KEY) < 32:
    raise RuntimeError("SESSION_SECRET_KEY must contain at least 32 characters")
bootstrap_admin(settings.BOOTSTRAP_ADMIN_USERNAME, settings.BOOTSTRAP_ADMIN_PASSWORD)

app = FastAPI(title="Virendra AI Studio")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie="studio_session",
    max_age=8 * 60 * 60,
    same_site="strict",
    https_only=settings.SESSION_COOKIE_SECURE,
)

AUTH_REQUIRED = [Depends(require_user)]


class OrchestratePayload(BaseModel):
    topic: str


class LoginPayload(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)


class UserCreatePayload(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(min_length=12, max_length=128)
    role: str = "member"


class UserActivationPayload(BaseModel):
    is_active: bool


class UserPasswordResetPayload(BaseModel):
    password: str = Field(min_length=12, max_length=128)


def get_db():
    """Provide a database session for request handling."""
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def user_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
    }


@app.post("/auth/login")
def login(payload: LoginPayload, request: Request, db: Session = Depends(get_db)):
    attempts = consume_login_attempt(
        db, payload.username, settings.SESSION_SECRET_KEY
    )
    if attempts > LOGIN_ATTEMPT_LIMIT:
        retry_after = login_retry_after(db, payload.username, settings.SESSION_SECRET_KEY)
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    clear_login_attempts(db, payload.username, settings.SESSION_SECRET_KEY)
    request.session.clear()
    csrf_token = secrets.token_urlsafe(32)
    request.session.update({
        "user_id": user.id,
        "session_version": user.session_version,
        "csrf_token": csrf_token,
    })
    return {"user": user_response(user), "csrf_token": csrf_token}


@app.post("/auth/logout", dependencies=AUTH_REQUIRED)
def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}


@app.get("/auth/me", dependencies=AUTH_REQUIRED)
def get_session_user(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == request.session["user_id"]).first()
    return {"user": user_response(user), "csrf_token": request.session["csrf_token"]}


@app.get("/auth/users", dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.username).all()
    return [user_response(user) for user in users]


@app.post("/auth/users", status_code=201, dependencies=[Depends(require_admin)])
def add_user(payload: UserCreatePayload, db: Session = Depends(get_db)):
    try:
        user = create_user(db, payload.username, payload.password, payload.role)
        return user_response(user)
    except ValueError as exc:
        status_code = 409 if str(exc) == "Username already exists" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.patch("/auth/users/{user_id}/active")
def set_user_active(
    user_id: int,
    payload: UserActivationPayload,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active == payload.is_active:
        return user_response(user)
    if not payload.is_active:
        if user.id == admin.id:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
        if user.role == "admin":
            active_admins = db.query(User).filter(
                User.role == "admin",
                User.is_active.is_(True),
            ).count()
            if active_admins <= 1:
                raise HTTPException(status_code=409, detail="Cannot deactivate the last active administrator")

    user.is_active = payload.is_active
    user.session_version += 1
    db.commit()
    db.refresh(user)
    return user_response(user)


@app.post("/auth/users/{user_id}/password", dependencies=[Depends(require_admin)])
def reset_user_password_endpoint(
    user_id: int,
    payload: UserPasswordResetPayload,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        reset_user_password(db, user, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return user_response(user)


@app.post("/content/generate", response_model=ContentOut, dependencies=AUTH_REQUIRED)
def generate_content(payload: ContentCreate, db: Session = Depends(get_db)):
    item = create_content_job(
        db=db,
        topic=payload.topic,
        source=payload.source,
        confidence=payload.confidence,
        competition=payload.competition,
        estimated_views=payload.estimated_views,
    )
    return item


@app.post("/content/create-with-ai", response_model=ContentOut, dependencies=AUTH_REQUIRED)
def create_content_with_ai(payload: ContentCreate, db: Session = Depends(get_db)):
    try:
        item = create_content_job_with_ai(
            db=db,
            topic=payload.topic,
            source=payload.source,
            confidence=payload.confidence,
            competition=payload.competition,
            estimated_views=payload.estimated_views,
        )
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/content/{item_id}/generate-ai", response_model=ContentOut, dependencies=AUTH_REQUIRED)
def generate_ai(item_id: int, db: Session = Depends(get_db)):
    try:
        item = generate_ai_content(db, item_id)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/content/{item_id}/render-video", response_model=ContentOut, dependencies=AUTH_REQUIRED)
def render_video(item_id: int, db: Session = Depends(get_db)):
    try:
        return render_content_video(db, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/content/{item_id}/video")
def download_video(
    item_id: int,
    request: Request,
    media_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if not (media_token and verify_media_token(media_token, item_id)):
        require_user(request, db)
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item or not item.video_path or not Path(item.video_path).is_file():
        raise HTTPException(status_code=404, detail="Rendered video not found")
    return FileResponse(item.video_path, media_type="video/mp4", filename=Path(item.video_path).name)


@app.get("/content/{item_id}/subtitles", dependencies=AUTH_REQUIRED)
def download_subtitles(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    subtitle_path = Path(item.video_path).with_suffix(".srt") if item and item.video_path else None
    if not subtitle_path or not subtitle_path.is_file():
        raise HTTPException(status_code=404, detail="Rendered subtitles not found")
    return FileResponse(subtitle_path, media_type="application/x-subrip", filename=subtitle_path.name)


@app.post("/content/{item_id}/upload-youtube", dependencies=AUTH_REQUIRED)
def upload_youtube(item_id: int, payload: YouTubeUploadPayload, db: Session = Depends(get_db)):
    try:
        result = upload_youtube_video(
            db=db,
            item_id=item_id,
            file_path=payload.file_path,
            privacy_status=payload.privacy_status,
            tags=payload.tags,
        )
        return {"status": "uploaded", "youtube_response": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/content/{item_id}/analytics", dependencies=AUTH_REQUIRED)
def submit_analytics(item_id: int, payload: AnalyticsCreate, db: Session = Depends(get_db)):
    try:
        analytics = add_analytics(
            db=db,
            item_id=item_id,
            views=payload.views,
            ctr=payload.ctr,
            retention=payload.retention,
            subscribers=payload.subscribers,
            rpm=payload.rpm,
            top_keywords=payload.top_keywords,
        )
        return analytics
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/content/{item_id}/learning", dependencies=AUTH_REQUIRED)
def submit_learning_signal(item_id: int, payload: LearningSignalCreate, db: Session = Depends(get_db)):
    try:
        learning = add_learning_signal(
            db=db,
            item_id=item_id,
            title_style=payload.title_style,
            thumbnail_style=payload.thumbnail_style,
            best_upload_time=payload.best_upload_time,
            topic_category=payload.topic_category,
            ctr=payload.ctr,
            retention=payload.retention,
            rpm=payload.rpm,
        )
        return learning
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/content/review", dependencies=AUTH_REQUIRED)
def content_review_queue(db: Session = Depends(get_db)):
    items = get_content_review_queue(db)
    return items

@app.get("/content/{item_id}/analytics", dependencies=AUTH_REQUIRED)
def get_analytics(item_id: int, db: Session = Depends(get_db)):
    analytics = get_content_analytics(db, item_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Analytics not found")
    return analytics

@app.get("/content/{item_id}/learning", dependencies=AUTH_REQUIRED)
def get_learning_signals(item_id: int, db: Session = Depends(get_db)):
    learning = get_content_learning_signals(db, item_id)
    if learning is None:
        raise HTTPException(status_code=404, detail="Learning signals not found")
    return learning


@app.get("/content", response_model=list[ContentOut], dependencies=AUTH_REQUIRED)
def list_content(db: Session = Depends(get_db)):
    return list_content_items(db)


@app.get("/content/summary", dependencies=AUTH_REQUIRED)
def content_summary(db: Session = Depends(get_db)):
    return get_content_summary(db)


@app.get("/content/{item_id}", response_model=ContentOut, dependencies=AUTH_REQUIRED)
def get_content(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@app.post("/content/{item_id}/approve", response_model=ContentOut, dependencies=AUTH_REQUIRED)
def approve(item_id: int, db: Session = Depends(get_db)):
    try:
        item = approve_content(db, item_id)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/content/{item_id}/publish/{platform}", response_model=PublishResultOut, dependencies=AUTH_REQUIRED)
def publish_platform(item_id: int, platform: str, db: Session = Depends(get_db)):
    try:
        item = publish_content(db, item_id, platform=platform)
        result = PublishResultOut.model_validate(item)
        result.provider_status = getattr(item, "provider_status", None)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PublisherConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InstagramPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FacebookPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TelegramPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/content/{item_id}/publish", response_model=PublishResultOut, dependencies=AUTH_REQUIRED)
def publish(item_id: int, payload: PublishPayload | None = None, db: Session = Depends(get_db)):
    try:
        item = publish_content(
            db,
            item_id,
            platform=payload.platform if payload else None,
            platforms=payload.platforms if payload else None,
        )
        result = PublishResultOut.model_validate(item)
        result.provider_status = getattr(item, "provider_status", None)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PublisherConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except InstagramPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FacebookPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except TelegramPublishError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "virendra-ai-studio"}


@app.post("/content/orchestrate", dependencies=AUTH_REQUIRED)
def orchestrate_endpoint(payload: OrchestratePayload):
    try:
        result = orchestrate_content(payload.topic)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
