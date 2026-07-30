from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, ContentItem, engine
from app.schemas import ContentCreate, ContentOut, YouTubeUploadPayload
from app.services import (
    approve_content,
    create_content_job,
    generate_ai_content,
    publish_content,
    upload_youtube_video,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Virendra AI Studio")


def get_db():
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
