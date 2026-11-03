"""Application configuration and environment variable loading."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    SESSION_SECRET_KEY: str
    BOOTSTRAP_ADMIN_USERNAME: str | None = None
    BOOTSTRAP_ADMIN_PASSWORD: str | None = None
    SESSION_COOKIE_SECURE: bool = True
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    YOUTUBE_CLIENT_SECRETS: str = "client_secrets.json"
    YOUTUBE_TOKEN_JSON: str = "youtube_token.json"
    YOUTUBE_CATEGORY_ID: str = "25"
    YOUTUBE_PRIVACY_STATUS: str = "private"
    DAILY_NEWS_AUTOPUBLISH_ENABLED: bool = False
    DAILY_NEWS_PUBLISH_TIME: str = "20:00"
    DAILY_NEWS_TIMEZONE: str = "Asia/Kolkata"
    INSTAGRAM_ACCESS_TOKEN: str | None = None
    INSTAGRAM_USER_ID: str | None = None
    INSTAGRAM_GRAPH_API_VERSION: str = "v22.0"
    FACEBOOK_PAGE_ACCESS_TOKEN: str | None = None
    FACEBOOK_PAGE_ID: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    PUBLIC_MEDIA_BASE_URL: str | None = None
    AZURE_STORAGE_ACCOUNT_URL: str | None = None
    AZURE_STORAGE_CONTAINER: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
