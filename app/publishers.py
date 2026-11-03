"""Publisher adapters for social platforms used in the content workflow."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings

class PublisherConfigurationError(RuntimeError):
    """Raised when a live publisher is missing required configuration."""


class InstagramPublishError(RuntimeError):
    """Raised when the Instagram Graph API rejects or fails a publish request."""


class FacebookPublishError(RuntimeError):
    """Raised when the Facebook Graph API rejects or fails a publish request."""


class TelegramPublishError(RuntimeError):
    """Raised when the Telegram Bot API rejects or fails a publish request."""


def _instagram_request(
    path: str,
    access_token: str,
    params: dict[str, str],
    method: str | None = None,
) -> dict[str, Any]:
    request_method = method or ("POST" if params else "GET")
    url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_API_VERSION}/{path}"
    if request_method == "GET" and params:
        url = f"{url}?{urlencode(params)}"
    request = Request(
        url,
        data=urlencode(params).encode("utf-8") if request_method == "POST" else None,
        headers={"Authorization": f"Bearer {access_token}"},
        method=request_method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", str(exc))
        except (json.JSONDecodeError, UnicodeDecodeError):
            details = str(exc)
        raise InstagramPublishError(f"Instagram Graph API request failed: {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise InstagramPublishError(f"Instagram Graph API request failed: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InstagramPublishError("Instagram Graph API returned an invalid response") from exc


def publish_instagram_reel(
    video_url: str,
    caption: str,
    access_token: str | None = None,
    instagram_user_id: str | None = None,
) -> dict[str, Any]:
    """Create and publish an Instagram Reel from a publicly reachable HTTPS video URL."""
    token = access_token or settings.INSTAGRAM_ACCESS_TOKEN
    user_id = instagram_user_id or settings.INSTAGRAM_USER_ID
    if not token or not user_id:
        raise PublisherConfigurationError(
            "Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID to enable Instagram publishing"
        )
    if not video_url.startswith("https://"):
        raise PublisherConfigurationError("Instagram video hosting URL must use HTTPS")

    media = _instagram_request(
        f"{user_id}/media",
        token,
        {"media_type": "REELS", "video_url": video_url, "caption": caption[:2200]},
    )
    creation_id = media.get("id")
    if not creation_id:
        raise InstagramPublishError("Instagram did not return a Reel container ID")

    for attempt in range(30):
        status = _instagram_request(
            str(creation_id),
            token,
            {"fields": "status_code,status"},
            method="GET",
        )
        status_code = status.get("status_code")
        if status_code == "FINISHED":
            break
        if status_code in {"ERROR", "EXPIRED"}:
            raise InstagramPublishError(
                f"Instagram Reel processing ended with status {status_code}: "
                f"{status.get('status', 'no details provided')}"
            )
        if attempt == 29:
            raise InstagramPublishError("Timed out waiting for Instagram to process the Reel")
        time.sleep(2)

    published = _instagram_request(
        f"{user_id}/media_publish",
        token,
        {"creation_id": str(creation_id)},
    )
    media_id = published.get("id")
    if not media_id:
        raise InstagramPublishError("Instagram did not return a published media ID")

    return {
        "platform": "instagram",
        "status": "published",
        "external_id": media_id,
        "creation_id": str(creation_id),
        "message": "Instagram Reel published successfully.",
    }


def publish_facebook_video(
    video_url: str,
    title: str,
    description: str,
    access_token: str | None = None,
    page_id: str | None = None,
) -> dict[str, Any]:
    """Publish a rendered video to a Facebook Page using Meta's hosted-video flow."""
    token = access_token or settings.FACEBOOK_PAGE_ACCESS_TOKEN
    target_page = page_id or settings.FACEBOOK_PAGE_ID
    if not token or not target_page:
        raise PublisherConfigurationError(
            "Set FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID to enable Facebook publishing"
        )
    if not video_url.startswith("https://"):
        raise PublisherConfigurationError("Facebook video hosting URL must use HTTPS")

    url = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_API_VERSION}/{target_page}/videos"
    request = Request(
        url,
        data=urlencode(
            {
                "file_url": video_url,
                "title": title[:255],
                "description": description,
            }
        ).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", str(exc))
        except (json.JSONDecodeError, UnicodeDecodeError):
            details = str(exc)
        raise FacebookPublishError(f"Facebook Graph API request failed: {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise FacebookPublishError(f"Facebook Graph API request failed: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FacebookPublishError("Facebook Graph API returned an invalid response") from exc

    video_id = result.get("id")
    if not video_id:
        raise FacebookPublishError("Facebook did not return a published video ID")

    return {
        "platform": "facebook",
        "status": "published",
        "external_id": video_id,
        "message": "Facebook Page video published successfully.",
    }


def publish_telegram_video(
    video_url: str,
    caption: str,
    bot_token: str | None = None,
    chat_id: str | None = None,
) -> dict[str, Any]:
    """Send an externally hosted MP4 video to a Telegram chat or channel."""
    token = bot_token or settings.TELEGRAM_BOT_TOKEN
    target_chat = chat_id or settings.TELEGRAM_CHAT_ID
    if not token or not target_chat:
        raise PublisherConfigurationError(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable Telegram publishing"
        )
    if not video_url.startswith("https://"):
        raise PublisherConfigurationError("Telegram video hosting URL must use HTTPS")

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    request = Request(
        url,
        data=urlencode(
            {
                "chat_id": target_chat,
                "video": video_url,
                "caption": caption[:1024],
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            details = json.loads(exc.read().decode("utf-8")).get("description", "Telegram rejected the request")
        except (json.JSONDecodeError, UnicodeDecodeError):
            details = "Telegram request failed"
        raise TelegramPublishError(f"Telegram Bot API request failed: {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise TelegramPublishError("Telegram Bot API request failed due to a network error") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TelegramPublishError("Telegram Bot API returned an invalid response") from exc

    if not result.get("ok"):
        raise TelegramPublishError(
            f"Telegram Bot API rejected the request: {result.get('description', 'unknown error')}"
        )

    message = result.get("result", {})
    message_id = message.get("message_id")
    if message_id is None:
        raise TelegramPublishError("Telegram did not return a message ID")

    return {
        "platform": "telegram",
        "status": "published",
        "external_id": str(message_id),
        "chat_id": str(message.get("chat", {}).get("id", target_chat)),
        "message": "Telegram video sent successfully.",
    }
