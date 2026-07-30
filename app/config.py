import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/youtube_ai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    YOUTUBE_CLIENT_SECRETS: str = "client_secrets.json"
    YOUTUBE_TOKEN_JSON: str = "youtube_token.json"
    YOUTUBE_CATEGORY_ID: str = "25"
    YOUTUBE_PRIVACY_STATUS: str = "private"

    class Config:
        env_file = ".env"


settings = Settings()
