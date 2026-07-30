from sqlalchemy.orm import Session

from app.models import ContentItem


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
