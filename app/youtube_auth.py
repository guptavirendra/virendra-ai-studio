import os

from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def create_youtube_credentials():
    if not os.path.exists(settings.YOUTUBE_CLIENT_SECRETS):
        raise FileNotFoundError(
            f"Missing YouTube client secrets file: {settings.YOUTUBE_CLIENT_SECRETS}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(settings.YOUTUBE_CLIENT_SECRETS, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(settings.YOUTUBE_TOKEN_JSON, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())

    print(f"YouTube credentials saved to {settings.YOUTUBE_TOKEN_JSON}")


if __name__ == "__main__":
    create_youtube_credentials()
