"""Business logic services for content creation, AI generation, publishing, analytics, and learning."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ContentItem
from app.models import Analytics, LearningSignal
from app.media_access import create_media_token
from app.fallbacks import build_script, build_seo
from app.openai_client import generate_script, generate_seo
from app.publishers import (
    publish_facebook_video,
    publish_instagram_reel,
    publish_telegram_video,
)
from app.youtube_client import upload_video
from app.video_factory import render_mp4_video


def _public_video_url(item_id: int) -> str:
    if not settings.PUBLIC_MEDIA_BASE_URL:
        raise RuntimeError("Set PUBLIC_MEDIA_BASE_URL to an externally reachable HTTPS backend URL")
    media_base_url = settings.PUBLIC_MEDIA_BASE_URL.rstrip("/")
    if not media_base_url.startswith("https://"):
        raise RuntimeError("PUBLIC_MEDIA_BASE_URL must use HTTPS")
    token = create_media_token(item_id)
    return f"{media_base_url}/content/{item_id}/video?media_token={token}"


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


def render_content_video(db: Session, item_id: int):
    """Render a saved script into a local MP4 and attach it to the content item."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    if not item.script:
        raise ValueError("Generate a script before rendering the video")

    render = render_mp4_video(
        topic=item.topic,
        description=item.script,
        output_name=f"content-{item.id}-{__import__('uuid').uuid4().hex}.mp4",
    )
    item.video_path = render["output_path"]
    db.commit()
    db.refresh(item)
    return item


def upload_youtube_video(db: Session, item_id: int, file_path: str, privacy_status: str = "private", tags=None):
    """Upload a prepared video to YouTube and update the content item state."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    if not item.approved:
        raise ValueError("Content must be approved before upload")

    if not item.seo_title or not item.seo_description:
        raise ValueError("SEO metadata is required before uploading")

    stored_path = Path(item.video_path).resolve() if item.video_path else None
    requested_path = Path(file_path).resolve()
    if stored_path is None or requested_path != stored_path:
        raise ValueError("file_path must match the rendered video for this content item")
    if not stored_path.is_file():
        raise FileNotFoundError("Rendered video file not found")

    response = upload_video(
        file_path=str(stored_path),
        title=item.seo_title,
        description=item.seo_description,
        tags=tags or [item.topic, "government update", "online service"],
        privacy_status=privacy_status,
    )

    item.video_path = str(stored_path)
    item.status = "uploaded"
    uploaded_privacy = response.get("status", {}).get("privacyStatus", privacy_status)
    item.published = uploaded_privacy == "public"
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


def normalize_publish_targets(platform: str | None = None, platforms: list[str] | None = None) -> str | None:
    """Normalize one or more social publishing targets into a comma-separated string."""
    targets = []
    if platform:
        targets.append(platform)
    if platforms:
        targets.extend(platforms)

    cleaned = []
    for target in targets:
        value = str(target).strip().lower()
        if value and value not in cleaned:
            cleaned.append(value)

    if not cleaned:
        return None
    return ",".join(cleaned)


def publish_content(db: Session, item_id: int, platform: str | None = None, platforms: list[str] | None = None):
    """Publish an approved content item to a platform such as YouTube, Instagram, Facebook, or Telegram."""
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    if not item.approved:
        raise ValueError("Content must be approved before publish")

    target = normalize_publish_targets(platform=platform, platforms=platforms)
    if target:
        item.publish_target = target
    elif not item.publish_target:
        item.publish_target = "youtube"

    first_target = item.publish_target.split(",")[0].strip() if item.publish_target else "youtube"
    if first_target == "youtube":
        if not item.video_path:
            raise ValueError("Render a video before uploading to YouTube")
        tags = [tag.lstrip("#") for tag in (item.hashtags or "").split() if tag.startswith("#")]
        response = upload_youtube_video(
            db=db,
            item_id=item.id,
            file_path=item.video_path,
            privacy_status=settings.YOUTUBE_PRIVACY_STATUS,
            tags=tags or None,
        )
        item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
        item.provider_status = {
            "platform": "youtube",
            "status": "uploaded",
            "external_id": response.get("id"),
            "privacy_status": response.get("status", {}).get(
                "privacyStatus", settings.YOUTUBE_PRIVACY_STATUS
            ),
        }
        db.commit()
        db.refresh(item)
        return item

    if first_target == "instagram":
        if not item.video_path:
            raise ValueError("Render a video before publishing to Instagram")
        if not Path(item.video_path).is_file():
            raise FileNotFoundError("Rendered video file not found")
        caption = "\n\n".join(
            part for part in (item.seo_title or item.topic, item.seo_description, item.hashtags) if part
        )
        item.provider_status = publish_instagram_reel(
            video_url=_public_video_url(item.id),
            caption=caption,
        )
        item.published = True
        item.status = "published"
        db.commit()
        db.refresh(item)
        return item

    if first_target == "facebook":
        if not item.video_path:
            raise ValueError("Render a video before publishing to Facebook")
        if not Path(item.video_path).is_file():
            raise FileNotFoundError("Rendered video file not found")
        description = "\n\n".join(
            part for part in (item.seo_description or item.script, item.hashtags) if part
        )
        item.provider_status = publish_facebook_video(
            video_url=_public_video_url(item.id),
            title=item.seo_title or item.topic,
            description=description,
        )
        item.published = True
        item.status = "published"
        db.commit()
        db.refresh(item)
        return item

    if first_target == "telegram":
        if not item.video_path:
            raise ValueError("Render a video before publishing to Telegram")
        if not Path(item.video_path).is_file():
            raise FileNotFoundError("Rendered video file not found")
        caption = "\n\n".join(
            part for part in (item.seo_title or item.topic, item.seo_description, item.hashtags) if part
        )
        item.provider_status = publish_telegram_video(
            video_url=_public_video_url(item.id),
            caption=caption,
        )
        item.published = True
        item.status = "published"
        db.commit()
        db.refresh(item)
        return item

    raise ValueError(f"Unsupported publishing platform: {first_target}")


def get_content_review_queue(db: Session):
    """Return content items that are pending review."""
    return db.query(ContentItem).filter(ContentItem.approved == False).order_by(ContentItem.created_at.desc()).all()


def list_content_items(db: Session, limit: int = 20):
    """Return the most recent content items for the dashboard."""
    return db.query(ContentItem).order_by(ContentItem.created_at.desc()).limit(limit).all()


def get_content_summary(db: Session):
    """Return a summary of the current content pipeline state for dashboard widgets."""
    items = db.query(ContentItem).all()
    return {
        "total": len(items),
        "draft": sum(1 for item in items if item.status == "draft"),
        "approved": sum(1 for item in items if item.approved),
        "published": sum(1 for item in items if item.published),
        "review_queue": sum(1 for item in items if not item.approved and item.status != "published"),
    }


def get_content_analytics(db: Session, item_id: int):
    """Fetch analytics history for a content item."""
    return db.query(Analytics).filter(Analytics.content_id == item_id).order_by(Analytics.created_at.desc()).all()


def get_content_learning_signals(db: Session, item_id: int):
    """Fetch learning signal history for a content item."""
    return db.query(LearningSignal).filter(LearningSignal.content_id == item_id).order_by(LearningSignal.created_at.desc()).all()
