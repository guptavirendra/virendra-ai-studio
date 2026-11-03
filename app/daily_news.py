"""Opt-in daily Bollywood news video generation and YouTube publishing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import logging
from pathlib import Path
import re
from typing import Iterable
from urllib.parse import urlsplit
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import OpenAI
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.media_storage import local_media_file
from app.models import ContentItem, engine
from app.services import render_content_video
from app.youtube_client import upload_video

logger = logging.getLogger(__name__)

MAX_FEED_BYTES = 2_000_000
MAX_STORIES = 5
MIN_STORIES = 3
MAX_STORIES_PER_SOURCE = 2
FEEDS = (
    ("Hindustan Times", "https://www.hindustantimes.com/feeds/rss/entertainment/rssfeed.xml"),
    ("The Times of India", "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms"),
    ("The Indian Express", "https://indianexpress.com/section/entertainment/feed/"),
)
INDIAN_CINEMA_TERMS = re.compile(
    r"\b(bollywood|hindi(?:\s+(?:cinema|film|movie))|indian(?:\s+(?:cinema|film))|"
    r"shah rukh|srk|salman khan|aamir khan|akshay kumar|amitabh|ranbir|alia bhatt|"
    r"deepika|ranveer|kareena|katrina|tiger shroff|kartik aaryan|"
    r"ayushmann|kiara advani|shraddha kapoor|vicky kaushal)\b",
    re.IGNORECASE,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@dataclass(frozen=True)
class NewsStory:
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime


class InsufficientNewsError(RuntimeError):
    """Raised when fresh reports do not meet the minimum coverage threshold."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: str | None) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    return " ".join(" ".join(parser.parts).split())


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == name:
            return (child.text or "").strip()
    return ""


def _is_bollywood_story(story: NewsStory) -> bool:
    path = urlsplit(story.url).path.lower()
    return (
        "/bollywood/" in path
        or "/hindi/" in path
        or bool(INDIAN_CINEMA_TERMS.search(f"{story.title} {story.summary}"))
    )


def _fetch_feed(feed_url: str, now: datetime, publisher: str) -> list[NewsStory]:
    request = Request(
        feed_url,
        headers={"User-Agent": "VirendraAIStudio/1.0 (daily news RSS reader)"},
    )
    with urlopen(request, timeout=15) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError(f"RSS feed exceeds the {MAX_FEED_BYTES}-byte limit: {feed_url}")

    root = ET.fromstring(payload)
    stories: list[NewsStory] = []
    cutoff = now - timedelta(hours=24)
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "item":
            continue
        title = _plain_text(_child_text(element, "title"))
        link = _child_text(element, "link")
        source = _plain_text(_child_text(element, "source")) or publisher
        summary = _plain_text(_child_text(element, "description"))
        published_text = _child_text(element, "pubDate")
        if not title or not link or not source or not published_text:
            continue
        if not link.startswith("https://"):
            continue
        try:
            published_at = parsedate_to_datetime(published_text)
        except (TypeError, ValueError):
            try:
                published_at = datetime.fromisoformat(published_text.replace("Z", "+00:00"))
            except ValueError:
                continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        published_at = published_at.astimezone(timezone.utc)
        if cutoff <= published_at <= now + timedelta(minutes=5):
            stories.append(
                NewsStory(
                    title=title,
                    summary=summary[:600],
                    source=source,
                    url=link,
                    published_at=published_at,
                )
            )
    return stories


def collect_fresh_stories(now: datetime | None = None) -> list[NewsStory]:
    """Fetch recent Bollywood-related RSS stories directly from publishers."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    instant = instant.astimezone(timezone.utc)

    stories: list[NewsStory] = []
    successful_feeds = 0
    for publisher, feed_url in FEEDS:
        try:
            feed_stories = _fetch_feed(feed_url, instant, publisher)
        except (URLError, TimeoutError, OSError, ET.ParseError, ValueError) as exc:
            logger.warning("Could not read the %s news feed: %s", publisher, exc)
            continue
        successful_feeds += 1
        stories.extend(feed_stories)

    if not successful_feeds:
        raise RuntimeError("All configured Bollywood news publisher feeds failed")

    unique_stories: dict[str, NewsStory] = {}
    for story in sorted(stories, key=lambda item: item.published_at, reverse=True):
        if not _is_bollywood_story(story):
            continue
        normalized_title = "".join(char.casefold() for char in story.title if char.isalnum())
        unique_stories.setdefault(normalized_title, story)

    selected: list[NewsStory] = []
    source_counts: dict[str, int] = {}
    for story in unique_stories.values():
        if source_counts.get(story.source, 0) >= MAX_STORIES_PER_SOURCE:
            continue
        selected.append(story)
        source_counts[story.source] = source_counts.get(story.source, 0) + 1
        if len(selected) == MAX_STORIES:
            break

    if len(selected) < MIN_STORIES or len({story.source for story in selected}) < 2:
        raise InsufficientNewsError(
            f"Only {len(selected)} fresh Bollywood stories from "
            f"{len({story.source for story in selected})} publishers were found; "
            f"need at least {MIN_STORIES} stories from 2 publishers"
        )
    return selected


def generate_news_package(stories: Iterable[NewsStory], publish_date: str) -> dict[str, str]:
    """Create an original Hindi script using only the supplied reporting."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for daily news script generation")

    story_data = [
        {
            "publisher": story.source,
            "headline": story.title,
            "reported_summary": story.summary,
        }
        for story in stories
    ]
    prompt = (
        "Write an original Hindi-language YouTube news digest about Bollywood for "
        f"{publish_date}. Use only these source facts: {json.dumps(story_data, ensure_ascii=False)}. "
        "Do not invent details, make predictions, or state allegations as facts. "
        "Paraphrase; do not reproduce article text or headlines. Attribute each item "
        "to its publisher in the narration, distinguish reports from confirmed facts, "
        "and keep the script concise (about 60-90 seconds). Return JSON only with "
        'string fields "title", "script", and "description".'
    )
    response = OpenAI(api_key=settings.OPENAI_API_KEY).chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You write careful, factual Hindi entertainment news summaries.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=1200,
        temperature=0.3,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty daily news script")
    try:
        package = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("OpenAI returned invalid JSON for the daily news script") from exc

    for field in ("title", "script", "description"):
        if not isinstance(package.get(field), str) or not package[field].strip():
            raise ValueError(f"OpenAI daily news response must include a non-empty {field}")
        package[field] = package[field].strip()
    if len(package["title"]) > 100:
        raise ValueError("Generated YouTube title exceeds the 100-character limit")
    return package


def _source_credits(stories: list[NewsStory]) -> str:
    entries = "\n".join(f"- {story.source}: {story.url}" for story in stories)
    return (
        "Sources (read the original reporting):\n"
        f"{entries}\n\n"
        "This video contains original summaries of the linked reporting. "
        "Please check the linked sources for full context."
    )


def _existing_daily_item(db: Session, source_key: str) -> ContentItem | None:
    return (
        db.query(ContentItem)
        .filter(ContentItem.source == source_key)
        .order_by(ContentItem.id.desc())
        .first()
    )


def run_daily_news(db: Session, now: datetime | None = None) -> ContentItem | None:
    """Build and publish one public video; a date key prevents repeat uploads."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    local_date = instant.astimezone(ZoneInfo(settings.DAILY_NEWS_TIMEZONE)).date()
    source_key = f"daily-bollywood-news:{local_date.isoformat()}"
    existing = _existing_daily_item(db, source_key)
    if existing:
        if existing.published:
            logger.info("Daily Bollywood video for %s is already public; skipping", local_date)
            return existing
        if existing.status == "skipped":
            logger.info("Daily Bollywood video for %s was skipped; not retrying", local_date)
            return existing
        raise RuntimeError(
            f"A daily news run for {local_date} already exists with status "
            f"{existing.status!r}; inspect its YouTube status before retrying"
        )

    item = ContentItem(
        topic=f"आज की बॉलीवुड खबरें | {local_date.strftime('%d-%m-%Y')}",
        source=source_key,
        confidence=0,
        competition="medium",
        estimated_views="medium",
        status="processing",
        approved=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    try:
        stories = collect_fresh_stories(instant)
        package = generate_news_package(stories, local_date.isoformat())
        item.script = package["script"]
        item.seo_title = package["title"]
        item.seo_description = f'{package["description"]}\n\n{_source_credits(stories)}'
        item.hashtags = "#Bollywood #BollywoodNews #HindiCinema"
        db.commit()

        render_content_video(db, item.id)
        with local_media_file(item.video_path) as video_path:
            response = upload_video(
                file_path=str(video_path),
                title=item.seo_title,
                description=item.seo_description,
                tags=["Bollywood", "Bollywood news", "Hindi cinema"],
                privacy_status="public",
            )

        privacy_status = response.get("status", {}).get("privacyStatus")
        item.status = "uploaded" if privacy_status == "public" else "uploaded_not_public"
        item.published = privacy_status == "public"
        db.commit()
        if not item.published:
            raise RuntimeError(
                "YouTube accepted the upload but did not make it public; "
                f"reported privacy status: {privacy_status!r}. Check Google API project verification."
            )
        logger.info(
            "Published daily Bollywood video for %s (YouTube video ID: %s)",
            local_date,
            response.get("id", "not returned"),
        )
        return item
    except InsufficientNewsError as exc:
        item.status = "skipped"
        item.seo_description = str(exc)
        db.commit()
        logger.info("Skipping daily Bollywood video for %s: %s", local_date, exc)
        return item
    except Exception:
        db.rollback()
        item = db.query(ContentItem).filter(ContentItem.id == item.id).one()
        if item.status == "processing":
            item.status = "failed"
            db.commit()
        logger.exception("Daily Bollywood publishing failed for %s", local_date)
        raise


def validate_scheduler_configuration() -> tuple[ZoneInfo, int, int]:
    """Fail fast when public auto-publishing is enabled without its prerequisites."""
    if not isinstance(settings.DAILY_NEWS_PUBLISH_TIME, str) or not re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d", settings.DAILY_NEWS_PUBLISH_TIME
    ):
        raise ValueError("DAILY_NEWS_PUBLISH_TIME must be a valid HH:MM time")
    hour, minute = (int(part) for part in settings.DAILY_NEWS_PUBLISH_TIME.split(":"))
    try:
        schedule_timezone = ZoneInfo(settings.DAILY_NEWS_TIMEZONE)
    except (KeyError, ValueError) as exc:
        raise ValueError("DAILY_NEWS_TIMEZONE must name a valid IANA timezone") from exc
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("Set OPENAI_API_KEY before enabling daily news auto-publishing")
    if not Path(settings.YOUTUBE_TOKEN_JSON).is_file():
        raise FileNotFoundError(
            f"YouTube OAuth token not found: {settings.YOUTUBE_TOKEN_JSON}. "
            "Complete the Google OAuth setup before enabling daily auto-publishing."
        )
    return schedule_timezone, hour, minute


def start_daily_news_scheduler() -> BackgroundScheduler | None:
    if not settings.DAILY_NEWS_AUTOPUBLISH_ENABLED:
        logger.info("Daily Bollywood public auto-publishing is disabled")
        return None

    schedule_timezone, hour, minute = validate_scheduler_configuration()
    scheduler = BackgroundScheduler(timezone=schedule_timezone)
    scheduler.add_job(
        _scheduled_daily_news,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=schedule_timezone),
        id="daily-bollywood-public-upload",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Daily Bollywood public auto-publishing scheduled for %02d:%02d %s",
        hour,
        minute,
        settings.DAILY_NEWS_TIMEZONE,
    )
    return scheduler


def _scheduled_daily_news() -> None:
    with SessionLocal() as db:
        run_daily_news(db)
