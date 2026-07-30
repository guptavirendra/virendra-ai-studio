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
