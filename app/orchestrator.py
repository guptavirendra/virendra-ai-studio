"""Simple orchestration layer for content generation workflows."""

from app.openai_client import generate_script, generate_seo
from app.prompt_manager import get_thumbnail_prompt


def orchestrate_content(topic: str) -> dict:
    """Build a complete content payload for a topic using AI-enabled prompts."""
    script = generate_script(topic)
    seo_data = generate_seo(topic, script)
    thumbnail_prompt = get_thumbnail_prompt(topic)

    return {
        "topic": topic,
        "script": script,
        "seo": {
            "title": seo_data["title"],
            "description": seo_data["description"],
            "hashtags": seo_data["hashtags"],
            "tags": seo_data["tags"],
        },
        "thumbnail_prompt": thumbnail_prompt,
        "quality_check": {
            "passed": bool(topic and script and seo_data.get("title") and seo_data.get("description")),
            "notes": "Generated with AI prompt manager and fallback logic.",
        },
    }
