"""Business logic services for content creation, AI generation, publishing, analytics, and learning."""

from sqlalchemy.orm import Session

from app.models import ContentItem
from app.models import Analytics, LearningSignal
from app.fallbacks import build_script, build_seo
from app.openai_client import generate_script, generate_seo
from app.youtube_client import upload_video


def build_script(topic: str) -> str:
    """Build a simple placeholder Hindi script for the given topic."""
    return f"""
Hook: {topic} पर आज का सबसे ज़रूरी अपडेट

Intro:
आज हम आपको {topic} के बारे में सरल भाषा में समझाएंगे।

Step 1:
सबसे पहले आपको जानकारी की मूल बात समझनी होगी।

Step 2:
फिर इसे अपने लिए लागू करना सीखें।

Step 3:
अंत में सबसे जरूरी सुझाव जानें।

Summary:
यह अपडेट आपके लिए महत्वपूर्ण हो सकता है।

CTA:
अगर आप चाहें, तो मैं इसे और आसान तरीके से भी समझा सकता हूँ।
"""


def build_seo(topic: str):
    """Build a simple placeholder SEO metadata payload for the given topic."""
    return {
        "title": f"{topic} | आसान समझ में",
        "description": f"{topic} पर आसान और उपयोगी जानकारी।",
        "hashtags": "#government #india #updates #news",
        "tags": [topic, "government update", "india"],
    }


def create_content_job(db: Session, topic: str, source: str, confidence: int, competition: str, estimated_views: str):
    """Create a new draft content item in the database."""
    item = ContentItem(
        topic=topic,
        source=source,
        confidence=confidence,
        competition=competition,
        estimated_views=estimated_views,
        status="draft",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_content_job_with_ai(db: Session, topic: str, source: str, confidence: int, competition: str, estimated_views: str):
    """Create a new content item and immediately generate AI script and SEO metadata."""
    item = create_content_job(db, topic, source, confidence, competition, estimated_views)
    return generate_ai_content(db, item.id)


def generate_ai_content(db: Session, item_id: int):
    """Generate script and SEO metadata for an existing content item."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")

    item.script = generate_script(item.topic)
    seo_data = generate_seo(item.topic, item.script)
    item.seo_title = seo_data.get("title")
    item.seo_description = seo_data.get("description")
    item.hashtags = seo_data.get("hashtags")
    db.commit()
    db.refresh(item)
    return item


def upload_youtube_video(db: Session, item_id: int, file_path: str, privacy_status: str = "private", tags=None):
    """Upload a prepared video to YouTube and update the content item state."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")

    if not item.seo_title or not item.seo_description:
        raise ValueError("SEO metadata is required before uploading")

    response = upload_video(
        file_path=file_path,
        title=item.seo_title,
        description=item.seo_description,
        tags=tags or [item.topic, "government update", "online service"],
        privacy_status=privacy_status,
    )

    item.video_path = file_path
    item.status = "uploaded"
    if privacy_status == "public":
        item.published = True
    db.commit()
    db.refresh(item)
    return response


def add_analytics(db: Session, item_id: int, views: int, ctr: float, retention: float, subscribers: int, rpm: float, top_keywords: str | None = None):
    """Record analytics metrics for a content item."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")

    analytics = Analytics(
        content_id=item.id,
        views=views,
        ctr=ctr,
        retention=retention,
        subscribers=subscribers,
        rpm=rpm,
        top_keywords=top_keywords,
    )
    db.add(analytics)
    db.commit()
    db.refresh(analytics)
    return analytics


def add_learning_signal(
    db: Session,
    item_id: int,
    title_style: str | None = None,
    thumbnail_style: str | None = None,
    best_upload_time: str | None = None,
    topic_category: str | None = None,
    ctr: float = 0.0,
    retention: float = 0.0,
    rpm: float = 0.0,
):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")

    learning_signal = LearningSignal(
        content_id=item.id,
        title_style=title_style,
        thumbnail_style=thumbnail_style,
        best_upload_time=best_upload_time,
        topic_category=topic_category,
        ctr=ctr,
        retention=retention,
        rpm=rpm,
    )
    db.add(learning_signal)
    db.commit()
    db.refresh(learning_signal)
    return learning_signal


def approve_content(db: Session, item_id: int):
    """Mark a content item as approved for publication."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    item.approved = True
    item.status = "approved"
    db.commit()
    return item


def publish_content(db: Session, item_id: int):
    """Publish an approved content item."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    if not item.approved:
        raise ValueError("Content must be approved before publish")
    item.published = True
    item.status = "published"
    db.commit()
    return item


def get_content_review_queue(db: Session):
    """Return content items that are pending review."""
    return db.query(ContentItem).filter(ContentItem.approved == False).order_by(ContentItem.created_at.desc()).all()


def get_content_analytics(db: Session, item_id: int):
    """Fetch analytics history for a content item."""
    return db.query(Analytics).filter(Analytics.content_id == item_id).order_by(Analytics.created_at.desc()).all()


def get_content_learning_signals(db: Session, item_id: int):
    """Fetch learning signal history for a content item."""
    return db.query(LearningSignal).filter(LearningSignal.content_id == item_id).order_by(LearningSignal.created_at.desc()).all()
