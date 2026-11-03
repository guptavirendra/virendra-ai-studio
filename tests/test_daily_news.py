from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from io import BytesIO
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import daily_news
from app.config import settings
from app.models import Base


def _story(title, publisher, hours_ago=1, url_suffix="story"):
    return daily_news.NewsStory(
        title=title,
        summary="A report about a Bollywood film and its cast.",
        source=publisher,
        url=f"https://{publisher.lower().replace(' ', '')}.example/{url_suffix}",
        published_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    )


def _database():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)()


def test_fetch_feed_keeps_only_recent_https_stories(monkeypatch):
    now = datetime.now(timezone.utc)
    recent = format_datetime(now - timedelta(hours=2))
    stale = format_datetime(now - timedelta(hours=30))
    payload = f"""<?xml version="1.0"?>
    <rss><channel>
      <item><title>Film release update</title><link>https://publisher.example/recent</link>
        <description>&lt;p&gt;A new movie&lt;/p&gt;</description>
        <source>Publisher</source><pubDate>{recent}</pubDate></item>
      <item><title>Old Bollywood report</title><link>https://publisher.example/old</link>
        <description>Old item</description><source>Publisher</source><pubDate>{stale}</pubDate></item>
      <item><title>Unsafe link</title><link>http://publisher.example/no</link>
        <description>Item</description><source>Publisher</source><pubDate>{recent}</pubDate></item>
      <item><title>Bollywood report</title><link>https://publisher.example/fallback</link>
        <description>Another item</description>
        <pubDate>{(now - timedelta(hours=3)).isoformat()}</pubDate></item>
    </channel></rss>""".encode()

    class Response(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(daily_news, "urlopen", lambda request, timeout: Response(payload))

    stories = daily_news._fetch_feed("https://publisher.example/rss", now, "Publisher")

    assert len(stories) == 2
    assert stories[0].title == "Film release update"
    assert stories[0].summary == "A new movie"
    assert stories[1].source == "Publisher"


def test_collect_fresh_stories_deduplicates_and_requires_varied_sources(monkeypatch):
    first = _story("Bollywood film release", "Publisher A")
    duplicate = _story("Bollywood film release", "Publisher B", hours_ago=3, url_suffix="duplicate")
    second = _story("Hindi cinema begins filming a new movie", "Publisher B")
    third = _story("Hindi cinema box office report", "Publisher C")
    monkeypatch.setattr(
        daily_news,
        "FEEDS",
        (("A", "feed-a"), ("B", "feed-b"), ("C", "feed-c")),
    )
    monkeypatch.setattr(
        daily_news,
        "_fetch_feed",
        lambda feed_url, now, publisher: {
            "feed-a": [first],
            "feed-b": [duplicate, second],
            "feed-c": [third],
        }[feed_url],
    )

    result = daily_news.collect_fresh_stories(datetime.now(timezone.utc))

    assert len(result) == 3
    assert len({story.source for story in result}) == 3
    assert len({story.title for story in result}) == 3


def test_collect_fresh_stories_fails_if_only_one_publisher_has_news(monkeypatch):
    monkeypatch.setattr(daily_news, "FEEDS", (("A", "feed-a"),))
    monkeypatch.setattr(
        daily_news,
        "_fetch_feed",
        lambda feed_url, now, publisher: [
            _story("Bollywood film one", "Publisher A", url_suffix="one"),
            _story("Bollywood film two", "Publisher A", url_suffix="two"),
            _story("Bollywood film three", "Publisher A", url_suffix="three"),
        ],
    )

    with pytest.raises(RuntimeError, match="at least 3 stories from 2 publishers"):
        daily_news.collect_fresh_stories(datetime.now(timezone.utc))


def test_collect_fresh_stories_excludes_non_indian_cinema(monkeypatch):
    monkeypatch.setattr(daily_news, "FEEDS", (("A", "feed-a"),))
    monkeypatch.setattr(
        daily_news,
        "_fetch_feed",
        lambda feed_url, now, publisher: [
            _story("Nicolas Cage discusses a Hollywood movie", "Publisher A", url_suffix="hollywood"),
            _story("Hindi cinema announces a new release", "Publisher A", url_suffix="hindi"),
            _story("Bollywood film casts a new actor", "Publisher A", url_suffix="bollywood"),
        ],
    )

    with pytest.raises(daily_news.InsufficientNewsError):
        daily_news.collect_fresh_stories(datetime.now(timezone.utc))


def test_generate_news_package_uses_only_validated_hindi_fields(monkeypatch):
    result = {"title": "आज की बॉलीवुड खबरें", "script": "आज की खबरें।", "description": "आज का समाचार।"}

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(content=json.dumps(result, ensure_ascii=False))
                            )
                        ]
                    )
                )
            )

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(daily_news, "OpenAI", FakeClient)
    stories = [_story("Film release", "Publisher")]

    package = daily_news.generate_news_package(stories, "2026-11-03")

    assert package == result


def test_scheduler_configuration_requires_valid_time_and_oauth_token(monkeypatch, tmp_path):
    token_file = tmp_path / "youtube_token.json"
    token_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "DAILY_NEWS_PUBLISH_TIME", "20:00")
    monkeypatch.setattr(settings, "DAILY_NEWS_TIMEZONE", "Asia/Kolkata")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "YOUTUBE_TOKEN_JSON", str(token_file))

    zone, hour, minute = daily_news.validate_scheduler_configuration()

    assert str(zone) == "Asia/Kolkata"
    assert (hour, minute) == (20, 0)


def test_daily_scheduler_is_off_by_default(monkeypatch):
    monkeypatch.setattr(settings, "DAILY_NEWS_AUTOPUBLISH_ENABLED", False)

    assert daily_news.start_daily_news_scheduler() is None


def test_daily_run_publishes_once_and_records_public_status(monkeypatch, tmp_path):
    db = _database()
    video_path = tmp_path / "daily-news.mp4"
    video_path.write_bytes(b"mp4")
    uploaded = []

    monkeypatch.setattr(
        daily_news,
        "collect_fresh_stories",
        lambda now: [
            _story("Bollywood film one", "Publisher A"),
            _story("Bollywood film two", "Publisher B"),
            _story("Bollywood film three", "Publisher C"),
        ],
    )
    monkeypatch.setattr(
        daily_news,
        "generate_news_package",
        lambda stories, publish_date: {
            "title": "आज की बॉलीवुड खबरें",
            "script": "आज की खबरें।",
            "description": "तीन खबरों का सार।",
        },
    )

    def render(db_session, item_id):
        item = db_session.query(daily_news.ContentItem).filter_by(id=item_id).one()
        item.video_path = str(video_path)
        db_session.commit()
        return item

    monkeypatch.setattr(daily_news, "render_content_video", render)

    def upload_video(**kwargs):
        uploaded.append(kwargs)
        assert kwargs["privacy_status"] == "public"
        return {"id": "youtube-id", "status": {"privacyStatus": "public"}}

    monkeypatch.setattr(daily_news, "upload_video", upload_video)
    run_at = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)

    first = daily_news.run_daily_news(db, run_at)
    second = daily_news.run_daily_news(db, run_at)

    assert first.published is True
    assert first.status == "uploaded"
    assert second.id == first.id
    assert len(uploaded) == 1
    assert "Sources (read the original reporting)" in uploaded[0]["description"]


def test_failed_daily_run_is_not_automatically_retried(monkeypatch):
    db = _database()
    monkeypatch.setattr(
        daily_news,
        "collect_fresh_stories",
        lambda now: (_ for _ in ()).throw(RuntimeError("feed failure")),
    )
    run_at = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(RuntimeError, match="feed failure"):
        daily_news.run_daily_news(db, run_at)
    failed_item = db.query(daily_news.ContentItem).one()
    assert failed_item.status == "failed"

    with pytest.raises(RuntimeError, match="already exists"):
        daily_news.run_daily_news(db, run_at)


def test_insufficient_news_is_recorded_as_skipped(monkeypatch):
    db = _database()
    monkeypatch.setattr(
        daily_news,
        "collect_fresh_stories",
        lambda now: (_ for _ in ()).throw(daily_news.InsufficientNewsError("not enough reports")),
    )

    item = daily_news.run_daily_news(db, datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc))

    assert item.status == "skipped"
    assert item.published is False
