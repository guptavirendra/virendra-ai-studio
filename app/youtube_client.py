import os
from typing import List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_youtube_service():
    if not os.path.exists(settings.YOUTUBE_TOKEN_JSON):
        raise FileNotFoundError(
            f"YouTube token not found. Generate credentials with the OAuth flow and save to {settings.YOUTUBE_TOKEN_JSON}."
        )

    creds = Credentials.from_authorized_user_file(settings.YOUTUBE_TOKEN_JSON, SCOPES)
    return build("youtube", "v3", credentials=creds)


def upload_video(
    file_path: str,
    title: str,
    description: str,
    tags: List[str] | None = None,
    privacy_status: str = None,
) -> dict:
    if privacy_status is None:
        privacy_status = settings.YOUTUBE_PRIVACY_STATUS

    youtube = get_youtube_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": settings.YOUTUBE_CATEGORY_ID,
        },
        "status": {"privacyStatus": privacy_status},
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    return request.execute()
