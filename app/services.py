from sqlalchemy.orm import Session

from app.models import ContentItem
from app.openai_client import generate_script, generate_seo
from app.youtube_client import upload_video


def build_script(topic: str) -> str:
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
    return {
        "title": f"{topic} | आसान समझ में",
        "description": f"{topic} पर आसान और उपयोगी जानकारी।",
        "hashtags": "#government #india #updates #news",
        "tags": [topic, "government update", "india"],
    }


def create_content_job(db: Session, topic: str, source: str, confidence: int, competition: str, estimated_views: str):
    item = ContentItem(
        topic=topic,
        source=source,
        confidence=confidence,
        competition=competition,
        estimated_views=estimated_views,
        script=build_script(topic),
        status="draft",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def generate_ai_content(db: Session, item_id: int):
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


def approve_content(db: Session, item_id: int):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    item.approved = True
    item.status = "approved"
    db.commit()
    return item


def publish_content(db: Session, item_id: int):
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
        raise ValueError("Content not found")
    if not item.approved:
        raise ValueError("Content must be approved before publish")
    item.published = True
    item.status = "published"
    db.commit()
    return item
