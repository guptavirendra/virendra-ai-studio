"""Helper to create and save Google OAuth credentials for YouTube."""

import os

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def create_youtube_credentials():
    """Run the OAuth flow to create YouTube API credentials."""
    if not os.path.exists(settings.YOUTUBE_CLIENT_SECRETS):
        raise FileNotFoundError(
            f"Missing YouTube client secrets file: {settings.YOUTUBE_CLIENT_SECRETS}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(settings.YOUTUBE_CLIENT_SECRETS, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(settings.YOUTUBE_TOKEN_JSON, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())
    os.chmod(settings.YOUTUBE_TOKEN_JSON, 0o600)

    youtube = build("youtube", "v3", credentials=creds)
    channels = youtube.channels().list(part="snippet", mine=True).execute()
    items = channels.get("items", [])
    if not items:
        raise RuntimeError("The authorized Google account does not expose a YouTube channel")
    print(f"YouTube credentials saved to {settings.YOUTUBE_TOKEN_JSON}")
    print("Authorized YouTube channel(s):")
    for channel in items:
        print(f"- {channel['snippet']['title']} (channel ID: {channel['id']})")


if __name__ == "__main__":
    create_youtube_credentials()
