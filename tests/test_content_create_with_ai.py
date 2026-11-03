from fastapi.testclient import TestClient
from pathlib import Path
import subprocess
import json
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from app.ai_suggestions import generate_ai_suggestions
from app.image_factory import generate_image_prompt
from app.main import app
from app.media_access import create_media_token, verify_media_token
from app.models import ContentItem, engine
from app.publishers import (
    PublisherConfigurationError,
    publish_instagram_reel,
    publish_facebook_video,
    publish_telegram_video,
)
from app.video_factory import generate_subtitles, render_mp4_video
from sqlalchemy.orm import sessionmaker


client = TestClient(app)
login_response = client.post(
    "/auth/login",
    json={"username": "test-admin", "password": "test-only-password-123"},
)
assert login_response.status_code == 200
client.headers.update({"X-CSRF-Token": login_response.json()["csrf_token"]})


def test_create_content_with_ai_endpoint():
    resp = client.post(
        "/content/create-with-ai",
        json={
            "topic": "EPFO नए नियम",
            "source": "government",
            "confidence": 5,
            "competition": "low",
            "estimated_views": "high",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["topic"] == "EPFO नए नियम"
    assert body["status"] == "draft"
    assert body["script"] is not None
    assert body["seo_title"] is not None
    assert body["seo_description"] is not None
    assert body["hashtags"] is not None


def test_publish_to_instagram_calls_live_publisher(monkeypatch, tmp_path):
    resp = client.post(
        "/content/create-with-ai",
        json={
            "topic": "PM-KISAN अपडेट",
            "source": "government",
            "confidence": 4,
            "competition": "medium",
            "estimated_views": "medium",
        },
    )
    item_id = resp.json()["id"]
    video_path = tmp_path / "rendered.mp4"
    video_path.write_bytes(b"video")

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
        item.video_path = str(video_path)
        db.commit()

    approve_resp = client.post(f"/content/{item_id}/approve")
    assert approve_resp.status_code == 200

    monkeypatch.setattr("app.services.settings.PUBLIC_MEDIA_BASE_URL", "https://studio.example.com/")
    published = []

    def fake_publish_instagram_reel(**kwargs):
        published.append(kwargs)
        return {
            "platform": "instagram",
            "status": "published",
            "external_id": "instagram-media-123",
            "message": "Instagram Reel published successfully.",
        }

    monkeypatch.setattr("app.services.publish_instagram_reel", fake_publish_instagram_reel)
    publish_resp = client.post(f"/content/{item_id}/publish/instagram")
    assert publish_resp.status_code == 200
    body = publish_resp.json()
    assert body["status"] == "published"
    assert body["published"] is True
    assert body["publish_target"] == "instagram"
    assert body["provider_status"]["external_id"] == "instagram-media-123"
    media_url = urlsplit(published[0]["video_url"])
    assert media_url.path == f"/content/{item_id}/video"
    assert verify_media_token(parse_qs(media_url.query)["media_token"][0], item_id)


def test_instagram_publisher_creates_polls_and_publishes_reel(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    responses = iter([
        {"id": "container-123"},
        {"status_code": "IN_PROGRESS", "status": "In progress"},
        {"status_code": "FINISHED", "status": "Finished"},
        {"id": "media-123"},
    ])
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse(next(responses))

    monkeypatch.setattr("app.publishers.urlopen", fake_urlopen)
    monkeypatch.setattr("app.publishers.time.sleep", lambda _: None)

    result = publish_instagram_reel(
        "https://studio.example.com/content/1/video",
        "A video caption",
        access_token="test-token",
        instagram_user_id="ig-user-1",
    )

    assert result["status"] == "published"
    assert result["external_id"] == "media-123"
    assert [request.method for request in requests] == ["POST", "GET", "GET", "POST"]
    assert requests[0].full_url.endswith("/ig-user-1/media")
    assert requests[1].full_url.endswith("/container-123?fields=status_code%2Cstatus")
    assert requests[2].full_url.endswith("/container-123?fields=status_code%2Cstatus")
    assert requests[3].full_url.endswith("/ig-user-1/media_publish")
    create_payload = parse_qs(requests[0].data.decode("utf-8"))
    assert create_payload["media_type"] == ["REELS"]
    assert create_payload["video_url"] == ["https://studio.example.com/content/1/video"]
    assert create_payload["caption"] == ["A video caption"]
    assert requests[0].get_header("Authorization") == "Bearer test-token"


def test_instagram_publisher_requires_credentials(monkeypatch):
    monkeypatch.setattr("app.publishers.settings.INSTAGRAM_ACCESS_TOKEN", None)
    monkeypatch.setattr("app.publishers.settings.INSTAGRAM_USER_ID", None)

    try:
        publish_instagram_reel("https://studio.example.com/video.mp4", "Caption")
    except PublisherConfigurationError as exc:
        assert "INSTAGRAM_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Missing Instagram credentials should fail explicitly")


def test_facebook_publisher_sends_page_video_request(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"id":"facebook-video-123"}'

    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setattr("app.publishers.urlopen", fake_urlopen)
    result = publish_facebook_video(
        video_url="https://studio.example.com/content/1/video",
        title="Page video",
        description="A video description",
        access_token="page-token",
        page_id="page-123",
    )

    assert result["status"] == "published"
    assert result["external_id"] == "facebook-video-123"
    assert requests[0].full_url.endswith("/page-123/videos")
    assert requests[0].get_header("Authorization").startswith("Bearer ")
    payload = parse_qs(requests[0].data.decode("utf-8"))
    assert payload["file_url"] == ["https://studio.example.com/content/1/video"]
    assert payload["title"] == ["Page video"]
    assert payload["description"] == ["A video description"]


def test_facebook_publish_requires_video_and_configured_public_url(monkeypatch, tmp_path):
    response = client.post(
        "/content/create-with-ai",
        json={"topic": "Facebook upload test", "source": "government"},
    )
    item_id = response.json()["id"]
    video_path = tmp_path / "rendered.mp4"
    video_path.write_bytes(b"video")

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
        item.video_path = str(video_path)
        db.commit()
    assert client.post(f"/content/{item_id}/approve").status_code == 200

    monkeypatch.setattr("app.services.settings.PUBLIC_MEDIA_BASE_URL", None)
    failed = client.post(f"/content/{item_id}/publish/facebook")
    assert failed.status_code == 503
    assert "PUBLIC_MEDIA_BASE_URL" in failed.json()["detail"]

    monkeypatch.setattr("app.services.settings.PUBLIC_MEDIA_BASE_URL", "https://studio.example.com/")
    published = []

    def fake_publish_facebook_video(**kwargs):
        published.append(kwargs)
        return {
            "platform": "facebook",
            "status": "published",
            "external_id": "facebook-video-123",
            "message": "Facebook Page video published successfully.",
        }

    monkeypatch.setattr("app.services.publish_facebook_video", fake_publish_facebook_video)
    success = client.post(f"/content/{item_id}/publish/facebook")
    assert success.status_code == 200
    assert success.json()["provider_status"]["external_id"] == "facebook-video-123"
    assert success.json()["status"] == "published"
    media_url = urlsplit(published[0]["video_url"])
    assert media_url.path == f"/content/{item_id}/video"
    assert verify_media_token(parse_qs(media_url.query)["media_token"][0], item_id)


def test_youtube_publish_uploads_approved_rendered_video(monkeypatch, tmp_path):
    create_resp = client.post(
        "/content/create-with-ai",
        json={"topic": "YouTube upload test", "source": "government"},
    )
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]
    video_path = tmp_path / "rendered.mp4"
    video_path.write_bytes(b"video")

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
        item.video_path = str(video_path)
        db.commit()

    assert client.post(f"/content/{item_id}/approve").status_code == 200
    uploads = []

    def fake_upload_video(**kwargs):
        uploads.append(kwargs)
        return {"id": "youtube-video-123", "status": {"privacyStatus": "private"}}

    monkeypatch.setattr("app.services.upload_video", fake_upload_video)
    response = client.post(f"/content/{item_id}/publish/youtube")

    assert response.status_code == 200
    assert uploads[0]["file_path"] == str(video_path)
    assert uploads[0]["privacy_status"] == "private"
    assert response.json()["provider_status"]["external_id"] == "youtube-video-123"
    assert response.json()["status"] == "uploaded"
    assert response.json()["published"] is False


def test_youtube_upload_requires_approval():
    create_resp = client.post(
        "/content/create-with-ai",
        json={"topic": "Approval required", "source": "government"},
    )
    assert create_resp.status_code == 200

    response = client.post(
        f"/content/{create_resp.json()['id']}/upload-youtube",
        json={"file_path": "/tmp/unrelated.mp4"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Content must be approved before upload"


def test_telegram_publisher_sends_video_url_and_returns_message_id(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b'{"ok":true,"result":{"message_id":42,"chat":{"id":-1001}}}'

    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse()

    monkeypatch.setattr("app.publishers.urlopen", fake_urlopen)
    result = publish_telegram_video(
        video_url="https://studio.example.com/content/1/video",
        caption="PM-KISAN update",
        bot_token="test-token",
        chat_id="@studio",
    )

    assert result["platform"] == "telegram"
    assert result["status"] == "published"
    assert result["external_id"] == "42"
    assert result["chat_id"] == "-1001"
    assert requests[0].full_url.endswith("/bottest-token/sendVideo")
    payload = parse_qs(requests[0].data.decode("utf-8"))
    assert payload["chat_id"] == ["@studio"]
    assert payload["video"] == ["https://studio.example.com/content/1/video"]
    assert payload["caption"] == ["PM-KISAN update"]


def test_telegram_publisher_requires_credentials(monkeypatch):
    monkeypatch.setattr("app.publishers.settings.TELEGRAM_BOT_TOKEN", None)
    monkeypatch.setattr("app.publishers.settings.TELEGRAM_CHAT_ID", None)

    try:
        publish_telegram_video("https://studio.example.com/video.mp4", "Caption")
    except PublisherConfigurationError as exc:
        assert "TELEGRAM_BOT_TOKEN" in str(exc)
    else:
        raise AssertionError("Missing Telegram credentials should fail explicitly")


def test_telegram_publish_requires_approved_video_and_public_url(monkeypatch, tmp_path):
    response = client.post(
        "/content/create-with-ai",
        json={"topic": "Telegram upload test", "source": "government"},
    )
    item_id = response.json()["id"]
    video_path = tmp_path / "rendered.mp4"
    video_path.write_bytes(b"video")

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
        item.video_path = str(video_path)
        db.commit()
    assert client.post(f"/content/{item_id}/approve").status_code == 200

    monkeypatch.setattr("app.services.settings.PUBLIC_MEDIA_BASE_URL", "https://studio.example.com/")
    published = []

    def fake_publish_telegram_video(**kwargs):
        published.append(kwargs)
        return {
            "platform": "telegram",
            "status": "published",
            "external_id": "51",
            "chat_id": "-1001",
            "message": "Telegram video sent successfully.",
        }

    monkeypatch.setattr("app.services.publish_telegram_video", fake_publish_telegram_video)
    result = client.post(f"/content/{item_id}/publish/telegram")

    assert result.status_code == 200
    assert result.json()["status"] == "published"
    assert result.json()["provider_status"]["external_id"] == "51"
    media_url = urlsplit(published[0]["video_url"])
    assert media_url.path == f"/content/{item_id}/video"
    assert verify_media_token(parse_qs(media_url.query)["media_token"][0], item_id)


def test_generate_subtitles_creates_valid_srt_content():
    script = "Hook: PM-KISAN अपडेट बहुत जरूरी है. Intro: आज हम समझेंगे सरकार की योजना. Step 1: लाभार्थी कैसे आवेदन करेंगे."
    result = generate_subtitles(script)

    assert result.startswith("1\n")
    assert "00:00:00,000 --> 00:00:02,000" in result
    assert "PM-KISAN" in result
    assert "Step 1" in result


def test_generate_image_prompt_creates_visual_brief():
    prompt = generate_image_prompt("PM-KISAN अपडेट", "government")

    assert "PM-KISAN" in prompt
    assert "government" in prompt.lower()
    assert "prompt" in prompt.lower()
    assert len(prompt) > 40


def test_render_mp4_video_returns_render_metadata():
    payload = render_mp4_video(
        "PM-KISAN update",
        "A simple update about this government scheme. Learn how to apply today.",
        "government",
    )

    assert payload["format"] == "mp4"
    assert payload["topic"] == "PM-KISAN update"
    assert payload["status"] == "rendered"
    assert payload["output_path"].endswith(".mp4")
    video_file = Path(payload["output_path"])
    subtitle_file = Path(payload["subtitle_path"])
    try:
        assert video_file.is_file()
        assert video_file.stat().st_size > 1000
        assert video_file.read_bytes()[4:8] == b"ftyp"
        media_info = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", str(video_file)],
            check=True,
            capture_output=True,
            text=True,
        )
        streams = json.loads(media_info.stdout)["streams"]
        assert {stream["codec_type"] for stream in streams} == {"video", "audio"}
        video_stream = next(stream for stream in streams if stream["codec_type"] == "video")
        assert float(video_stream["duration"]) > 1
        assert subtitle_file.is_file()
        assert "-->" in subtitle_file.read_text(encoding="utf-8")
    finally:
        video_file.unlink(missing_ok=True)
        subtitle_file.unlink(missing_ok=True)


def test_rendered_content_video_can_be_downloaded():
    create_response = client.post(
        "/content/create-with-ai",
        json={
            "topic": "Local upload video test",
            "source": "government",
            "confidence": 6,
            "competition": "low",
            "estimated_views": "medium",
        },
    )
    assert create_response.status_code == 200
    item_id = create_response.json()["id"]

    render_response = client.post(f"/content/{item_id}/render-video")
    assert render_response.status_code == 200
    video_path = Path(render_response.json()["video_path"])
    try:
        download_response = client.get(f"/content/{item_id}/video")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "video/mp4"
        assert download_response.content[4:8] == b"ftyp"
        subtitles_response = client.get(f"/content/{item_id}/subtitles")
        assert subtitles_response.status_code == 200
        assert "-->" in subtitles_response.text
    finally:
        video_path.unlink(missing_ok=True)
        video_path.with_suffix(".srt").unlink(missing_ok=True)


def test_signed_media_url_allows_external_video_fetch_without_session(tmp_path):
    create_response = client.post(
        "/content/create-with-ai",
        json={"topic": "Signed media test", "source": "government"},
    )
    item_id = create_response.json()["id"]
    video_path = tmp_path / "signed.mp4"
    video_path.write_bytes(b"video")

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
        item.video_path = str(video_path)
        db.commit()

    media_token = create_media_token(item_id)
    anonymous = TestClient(app)
    allowed = anonymous.get(f"/content/{item_id}/video", params={"media_token": media_token})
    denied = anonymous.get(f"/content/{item_id}/video", params={"media_token": "invalid"})

    assert allowed.status_code == 200
    assert allowed.content == b"video"
    assert denied.status_code == 401
    video_path.unlink(missing_ok=True)


def test_generate_ai_suggestions_returns_actionable_recommendations():
    suggestions = generate_ai_suggestions(
        topic="PM-KISAN अपडेट",
        views=25000,
        ctr=0.068,
        retention=52.4,
        subscribers=420,
    )

    assert isinstance(suggestions, list)
    assert len(suggestions) >= 2
    assert any("hook" in suggestion.lower() or "title" in suggestion.lower() for suggestion in suggestions)


def test_dashboard_content_summary_endpoint():
    create_resp = client.post(
        "/content/create-with-ai",
        json={
            "topic": "Dashboard summary test",
            "source": "government",
            "confidence": 7,
            "competition": "low",
            "estimated_views": "high",
        },
    )
    assert create_resp.status_code == 200

    list_resp = client.get("/content")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)
    assert len(list_resp.json()) >= 1

    summary_resp = client.get("/content/summary")
    assert summary_resp.status_code == 200
    body = summary_resp.json()
    assert "total" in body
    assert "draft" in body
    assert "approved" in body
    assert "published" in body


def test_default_database_url_uses_sqlite_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import importlib
    import app.models as models_module

    importlib.reload(models_module)

    assert models_module.DATABASE_URL.startswith("sqlite")
    assert "postgres" not in models_module.DATABASE_URL.lower()
