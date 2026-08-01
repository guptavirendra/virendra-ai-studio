from typing import List, Optional
from pydantic import BaseModel


class ContentCreate(BaseModel):
    topic: str
    source: str = "government"
    confidence: int = 0
    competition: str = "medium"
    estimated_views: str = "medium"


class YouTubeUploadPayload(BaseModel):
    file_path: str
    privacy_status: str = "private"
    tags: Optional[List[str]] = None


class ContentOut(BaseModel):
    id: int
    topic: str
    source: str
    confidence: int
    competition: str
    estimated_views: str
    script: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    hashtags: Optional[str] = None
    status: str
    approved: bool
    published: bool


class AnalyticsCreate(BaseModel):
    views: int = 0
    ctr: float = 0.0
    retention: float = 0.0
    subscribers: int = 0
    rpm: float = 0.0
    top_keywords: Optional[str] = None


class LearningSignalCreate(BaseModel):
    title_style: Optional[str] = None
    thumbnail_style: Optional[str] = None
    best_upload_time: Optional[str] = None
    topic_category: Optional[str] = None
    ctr: float = 0.0
    retention: float = 0.0
    rpm: float = 0.0
