"""Local-development and Azure Blob Storage media operations."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
import mimetypes
from pathlib import Path, PurePosixPath
import tempfile
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from app.config import settings
from app.video_factory import DEFAULT_VIDEO_DIR

AZURE_BLOB_SCHEME = "azure-blob"


def _storage_configuration() -> tuple[str, str] | None:
    account_url = settings.AZURE_STORAGE_ACCOUNT_URL
    container = settings.AZURE_STORAGE_CONTAINER
    if bool(account_url) != bool(container):
        raise RuntimeError(
            "AZURE_STORAGE_ACCOUNT_URL and AZURE_STORAGE_CONTAINER must be configured together"
        )
    if not account_url:
        return None
    if not account_url.startswith("https://"):
        raise RuntimeError("AZURE_STORAGE_ACCOUNT_URL must use HTTPS")
    return account_url.rstrip("/"), container


@lru_cache(maxsize=4)
def _blob_service_client(account_url: str):
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    return BlobServiceClient(account_url, credential=DefaultAzureCredential())


def _blob_reference(container: str, blob_name: str) -> str:
    return urlunsplit((AZURE_BLOB_SCHEME, container, "/" + quote(blob_name, safe="/"), "", ""))


def _blob_location(reference: str) -> tuple[str, str]:
    parsed = urlsplit(reference)
    if parsed.scheme != AZURE_BLOB_SCHEME or not parsed.netloc or not parsed.path.strip("/"):
        raise ValueError("Invalid Azure Blob media reference")
    return parsed.netloc, unquote(parsed.path.lstrip("/"))


def is_blob_reference(reference: str) -> bool:
    return reference.startswith(f"{AZURE_BLOB_SCHEME}://")


def is_managed_local_media(reference: str) -> bool:
    path = Path(reference).resolve()
    media_root = DEFAULT_VIDEO_DIR.resolve()
    return path != media_root and path.is_relative_to(media_root)


def subtitle_reference(video_reference: str) -> str:
    if is_blob_reference(video_reference):
        container, blob_name = _blob_location(video_reference)
        subtitle_name = str(PurePosixPath(blob_name).with_suffix(".srt"))
        return _blob_reference(container, subtitle_name)
    return str(Path(video_reference).with_suffix(".srt"))


def _get_blob_client(container: str, blob_name: str):
    configuration = _storage_configuration()
    if not configuration:
        raise RuntimeError("Azure Blob Storage is not configured")
    account_url, configured_container = configuration
    if container != configured_container:
        raise ValueError("Media reference uses an unexpected Azure Blob container")
    return _blob_service_client(account_url).get_blob_client(container, blob_name)


def upload_media_file(local_path: str | Path, blob_prefix: str = "videos") -> str:
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")
    configuration = _storage_configuration()
    if not configuration:
        return str(path)

    _, container = configuration
    blob_name = f"{blob_prefix}/{path.name}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    from azure.storage.blob import ContentSettings

    with path.open("rb") as media_file:
        _get_blob_client(container, blob_name).upload_blob(
            media_file,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )
    return _blob_reference(container, blob_name)


def delete_media(reference: str) -> None:
    if not is_blob_reference(reference):
        if not is_managed_local_media(reference):
            raise ValueError("Refusing to delete media outside the generated-media directory")
        Path(reference).unlink(missing_ok=True)
        return
    from azure.core.exceptions import ResourceNotFoundError

    container, blob_name = _blob_location(reference)
    try:
        _get_blob_client(container, blob_name).delete_blob(delete_snapshots="include")
    except ResourceNotFoundError:
        pass


def media_exists(reference: str | None) -> bool:
    if not reference:
        return False
    if not is_blob_reference(reference):
        return Path(reference).is_file()
    container, blob_name = _blob_location(reference)
    return _get_blob_client(container, blob_name).exists()


def read_media_bytes(reference: str) -> bytes:
    if not is_blob_reference(reference):
        return Path(reference).read_bytes()
    container, blob_name = _blob_location(reference)
    return _get_blob_client(container, blob_name).download_blob().readall()


def iter_media_chunks(reference: str):
    if not is_blob_reference(reference):
        with Path(reference).open("rb") as media_file:
            while chunk := media_file.read(1024 * 1024):
                yield chunk
        return
    container, blob_name = _blob_location(reference)
    yield from _get_blob_client(container, blob_name).download_blob().chunks()


@contextmanager
def local_media_file(reference: str):
    if not is_blob_reference(reference):
        path = Path(reference).resolve()
        if not path.is_file():
            raise FileNotFoundError("Rendered video file not found")
        yield path
        return

    container, blob_name = _blob_location(reference)
    suffix = Path(blob_name).suffix
    with tempfile.TemporaryDirectory(prefix="studio-media-") as temp_dir:
        local_path = Path(temp_dir) / f"media{suffix}"
        with local_path.open("wb") as target:
            _get_blob_client(container, blob_name).download_blob().readinto(target)
        yield local_path
