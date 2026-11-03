import os
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./youtube_ai.db"
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if DATABASE_URL == "sqlite:///:memory:":
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **engine_kwargs)
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
    created_at = Column(DateTime, nullable=False, server_default=func.now())

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
    created_at = Column(DateTime, nullable=False, server_default=func.now())

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
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    content_item = relationship("ContentItem", back_populates="learning_signals")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(16), nullable=False, default="member")
    is_active = Column(Boolean, nullable=False, default=True)
    session_version = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class LoginRateLimit(Base):
    __tablename__ = "login_rate_limits"

    key_hash = Column(String(64), primary_key=True)
    attempts = Column(Integer, nullable=False)
    window_started_at = Column(DateTime, nullable=False, index=True)
