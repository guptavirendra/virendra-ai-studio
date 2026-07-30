from typing import Optional
from pydantic import BaseModel


class ContentCreate(BaseModel):
    topic: str
    source: str = "government"
    confidence: int = 0
    competition: str = "medium"
    estimated_views: str = "medium"


class ContentOut(BaseModel):
    id: int
    topic: str
    source: str
    confidence: int
    competition: str
    estimated_views: str
    script: Optional[str] = None
    status: str
    approved: bool
    published: bool
