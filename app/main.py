"""FastAPI backend for Virendra AI Studio content workflows."""

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, ContentItem, engine
from app.schemas import (
    AnalyticsCreate,
    ContentCreate,
    ContentOut,
    LearningSignalCreate,
    YouTubeUploadPayload,
)
from app.services import (
    approve_content,
    create_content_job,
    generate_ai_content,
    publish_content,
    upload_youtube_video,
    add_analytics,
    add_learning_signal,
    get_content_review_queue,
    get_content_analytics,
    get_content_learning_signals,
)

from app.orchestrator import orchestrate_content

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Virendra AI Studio")


class OrchestratePayload(BaseModel):
    topic: str


def get_db():
    """Provide a database session for request handling."""
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/content/generate", response_model=ContentOut)
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


@app.post("/content/{item_id}/generate-ai", response_model=ContentOut)
def generate_ai(item_id: int, db: Session = Depends(get_db)):
    try:
        item = generate_ai_content(db, item_id)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/content/{item_id}/upload-youtube")
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

@app.post("/content/{item_id}/analytics")
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

@app.post("/content/{item_id}/learning")
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

@app.get("/content/review")
def content_review_queue(db: Session = Depends(get_db)):
    items = get_content_review_queue(db)
    return items

@app.get("/content/{item_id}/analytics")
def get_analytics(item_id: int, db: Session = Depends(get_db)):
    analytics = get_content_analytics(db, item_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Analytics not found")
    return analytics

@app.get("/content/{item_id}/learning")
def get_learning_signals(item_id: int, db: Session = Depends(get_db)):
    learning = get_content_learning_signals(db, item_id)
    if learning is None:
        raise HTTPException(status_code=404, detail="Learning signals not found")
    return learning


@app.get("/content/{item_id}", response_model=ContentOut)
def get_content(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return item


@app.post("/content/{item_id}/approve", response_model=ContentOut)
def approve(item_id: int, db: Session = Depends(get_db)):
    try:
        item = approve_content(db, item_id)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/content/{item_id}/publish", response_model=ContentOut)
def publish(item_id: int, db: Session = Depends(get_db)):
    try:
        item = publish_content(db, item_id)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "virendra-ai-studio"}


@app.post("/content/orchestrate")
def orchestrate_endpoint(payload: OrchestratePayload):
    try:
        result = orchestrate_content(payload.topic)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
