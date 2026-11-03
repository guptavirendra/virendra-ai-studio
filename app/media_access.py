"""Short-lived signed access tokens for social platform media fetches."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

MEDIA_TOKEN_MAX_AGE_SECONDS = 3600


def create_media_token(content_id: int) -> str:
    serializer = URLSafeTimedSerializer(settings.SESSION_SECRET_KEY, salt="public-video")
    return serializer.dumps({"content_id": content_id})


def verify_media_token(token: str, content_id: int) -> bool:
    serializer = URLSafeTimedSerializer(settings.SESSION_SECRET_KEY, salt="public-video")
    try:
        payload = serializer.loads(token, max_age=MEDIA_TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return payload == {"content_id": content_id}
