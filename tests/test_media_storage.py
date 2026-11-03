from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import media_storage
from app.main import app
from app.media_access import create_media_token
from app.models import ContentItem, engine
from app.services import upload_youtube_video
from sqlalchemy.orm import sessionmaker


class FakeBlobClient:
    def __init__(self):
        self.payload = b""
        self.content_type = None

    def upload_blob(self, payload, overwrite, content_settings):
        assert overwrite is False
        self.payload = payload.read()
        self.content_type = content_settings.content_type

    def exists(self):
        return bool(self.payload)

    def download_blob(self):
        return self

    def readall(self):
        return self.payload

    def chunks(self):
        yield self.payload[:3]
        yield self.payload[3:]

    def readinto(self, target):
        return target.write(self.payload)

    def delete_blob(self, delete_snapshots):
        assert delete_snapshots == "include"
        self.payload = b""


def test_local_media_storage_remains_default(monkeypatch, tmp_path):
    source = tmp_path / "rendered.mp4"
    source.write_bytes(b"local-video")
    monkeypatch.setattr(media_storage.settings, "AZURE_STORAGE_ACCOUNT_URL", None)
    monkeypatch.setattr(media_storage.settings, "AZURE_STORAGE_CONTAINER", None)

    stored_reference = media_storage.upload_media_file(source)

    assert stored_reference == str(source)
    assert media_storage.media_exists(stored_reference)
    assert media_storage.read_media_bytes(stored_reference) == b"local-video"
    assert list(media_storage.iter_media_chunks(stored_reference)) == [b"local-video"]
    with media_storage.local_media_file(stored_reference) as local_path:
        assert local_path == source.resolve()
    with pytest.raises(ValueError, match="outside the generated-media directory"):
        media_storage.delete_media(stored_reference)


def test_azure_media_upload_download_and_subtitle_reference(monkeypatch, tmp_path):
    source = tmp_path / "content-4-unique.mp4"
    source.write_bytes(b"azure-video-content")
    video_blob = FakeBlobClient()
    subtitle_blob = FakeBlobClient()
    blobs = {
        "videos/content-4-unique.mp4": video_blob,
        "videos/content-4-unique.srt": subtitle_blob,
    }

    monkeypatch.setattr(
        media_storage.settings,
        "AZURE_STORAGE_ACCOUNT_URL",
        "https://studio.blob.core.windows.net",
    )
    monkeypatch.setattr(media_storage.settings, "AZURE_STORAGE_CONTAINER", "private-media")
    monkeypatch.setattr(
        media_storage,
        "_get_blob_client",
        lambda container, name: blobs[name],
    )

    video_reference = media_storage.upload_media_file(source)
    subtitle_reference = media_storage.subtitle_reference(video_reference)
    subtitle_source = tmp_path / "content-4-unique.srt"
    subtitle_source.write_text("subtitle data", encoding="utf-8")
    media_storage.upload_media_file(subtitle_source)

    assert video_reference == "azure-blob://private-media/videos/content-4-unique.mp4"
    assert subtitle_reference == "azure-blob://private-media/videos/content-4-unique.srt"
    assert video_blob.content_type == "video/mp4"
    assert media_storage.media_exists(video_reference)
    assert media_storage.read_media_bytes(video_reference) == b"azure-video-content"
    assert b"".join(media_storage.iter_media_chunks(video_reference)) == b"azure-video-content"

    with media_storage.local_media_file(video_reference) as local_path:
        assert Path(local_path).read_bytes() == b"azure-video-content"
    assert not local_path.exists()

    media_storage.delete_media(video_reference)
    assert not media_storage.media_exists(video_reference)


def test_partial_azure_configuration_is_rejected(monkeypatch):
    monkeypatch.setattr(
        media_storage.settings,
        "AZURE_STORAGE_ACCOUNT_URL",
        "https://studio.blob.core.windows.net",
    )
    monkeypatch.setattr(media_storage.settings, "AZURE_STORAGE_CONTAINER", None)

    with pytest.raises(RuntimeError, match="must be configured together"):
        media_storage._storage_configuration()


def test_azure_storage_account_endpoint_requires_https(monkeypatch):
    monkeypatch.setattr(
        media_storage.settings,
        "AZURE_STORAGE_ACCOUNT_URL",
        "http://studio.blob.core.windows.net",
    )
    monkeypatch.setattr(media_storage.settings, "AZURE_STORAGE_CONTAINER", "private-media")

    with pytest.raises(RuntimeError, match="must use HTTPS"):
        media_storage._storage_configuration()


def test_signed_video_endpoint_streams_blob_storage_media(monkeypatch):
    session_local = sessionmaker(bind=engine)
    with session_local() as db:
        item = ContentItem(
            topic="Blob storage test",
            source="test",
            video_path="azure-blob://private-media/videos/content-91.mp4",
        )
        db.add(item)
        db.commit()
        item_id = item.id

    monkeypatch.setattr("app.main.media_exists", lambda reference: True)
    monkeypatch.setattr(
        "app.main.iter_media_chunks",
        lambda reference: iter((b"video-", b"from-blob")),
    )
    client = TestClient(app)
    response = client.get(
        f"/content/{item_id}/video",
        params={"media_token": create_media_token(item_id)},
    )

    assert response.status_code == 200
    assert response.content == b"video-from-blob"
    assert response.headers["content-type"] == "video/mp4"


def test_youtube_upload_uses_temporary_local_copy_of_blob(monkeypatch):
    blob = FakeBlobClient()
    blob.payload = b"youtube-upload-video"
    monkeypatch.setattr(
        media_storage.settings,
        "AZURE_STORAGE_ACCOUNT_URL",
        "https://studio.blob.core.windows.net",
    )
    monkeypatch.setattr(media_storage.settings, "AZURE_STORAGE_CONTAINER", "private-media")
    monkeypatch.setattr(media_storage, "_get_blob_client", lambda container, name: blob)
    uploaded_paths = []

    def fake_upload_video(**kwargs):
        uploaded_path = Path(kwargs["file_path"])
        uploaded_paths.append(uploaded_path)
        assert uploaded_path.read_bytes() == b"youtube-upload-video"
        return {"id": "youtube-video-id", "status": {"privacyStatus": "private"}}

    monkeypatch.setattr("app.services.upload_video", fake_upload_video)
    session_local = sessionmaker(bind=engine)
    with session_local() as db:
        item = ContentItem(
            topic="Blob YouTube upload",
            source="test",
            video_path="azure-blob://private-media/videos/content-youtube.mp4",
            approved=True,
            seo_title="Blob upload",
            seo_description="Upload from durable media storage",
        )
        db.add(item)
        db.commit()
        item_id = item.id

        result = upload_youtube_video(
            db,
            item_id,
            "azure-blob://private-media/videos/content-youtube.mp4",
        )

    assert result["id"] == "youtube-video-id"
    assert uploaded_paths
    assert not uploaded_paths[0].exists()
