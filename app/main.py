from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, ContentItem, engine
from app.schemas import ContentCreate, ContentOut
from app.services import approve_content, create_content_job, publish_content

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
