"""Simple orchestration layer for content generation workflows."""

from app.services import build_script, build_seo


def orchestrate_content(topic: str) -> dict:
    """Build a complete content payload for a topic using local fallbacks."""
    script = build_script(topic)
    seo = build_seo(topic)

    return {
        "topic": topic,
        "script": script,
        "seo": {
            "title": seo["title"],
            "description": seo["description"],
            "hashtags": seo["hashtags"],
            "tags": seo["tags"],
        },
        "thumbnail_prompt": (
            f"Create a bold thumbnail for '{topic}' with strong Hindi typography, "
            "high contrast colors, and a clear visual hook."
        ),
        "quality_check": {
            "passed": bool(topic and script and seo.get("title") and seo.get("description")),
            "notes": "Generated with local fallback content and passed basic validation.",
        },
    }
