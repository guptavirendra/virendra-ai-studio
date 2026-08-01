import os
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai")
engine = create_engine(DATABASE_URL)
Base = declarative_base()


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    confidence = Column(Integer, default=0)
    competition = Column(String, default="medium")
    estimated_views = Column(String, default="medium")
    script = Column(Text, nullable=True)
    voice_file = Column(Text, nullable=True)
    thumbnail_path = Column(Text, nullable=True)
    video_path = Column(Text, nullable=True)
    seo_title = Column(Text, nullable=True)
    seo_description = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)
    status = Column(String, default="draft")
    publish_target = Column(String, nullable=True)
    approved = Column(Boolean, default=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default="NOW")

    analytics = relationship("Analytics", back_populates="content_item", cascade="all, delete-orphan")
    learning_signals = relationship("LearningSignal", back_populates="content_item", cascade="all, delete-orphan")


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_items.id"))
    views = Column(Integer, default=0)
    ctr = Column(Numeric(5, 2), default=0)
    retention = Column(Numeric(5, 2), default=0)
    subscribers = Column(Integer, default=0)
    rpm = Column(Numeric(10, 2), default=0)
    top_keywords = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default="NOW")

    content_item = relationship("ContentItem", back_populates="analytics")


class LearningSignal(Base):
    __tablename__ = "learning_signals"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_items.id"))
    title_style = Column(Text, nullable=True)
    thumbnail_style = Column(Text, nullable=True)
    best_upload_time = Column(Text, nullable=True)
    topic_category = Column(Text, nullable=True)
    ctr = Column(Numeric(5, 2), default=0)
    retention = Column(Numeric(5, 2), default=0)
    rpm = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, nullable=False, server_default="NOW")

    content_item = relationship("ContentItem", back_populates="learning_signals")
