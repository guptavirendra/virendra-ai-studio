"""Separate workflow agents for topic research, script writing, SEO, thumbnails, and quality checks."""

from app.image_factory import build_image_package
from app.openai_client import generate_script, generate_seo
from app.prompt_manager import get_thumbnail_prompt


def topic_agent(topic: str) -> dict:
    """Summarize the topic-level intent for the workflow."""
    return {
        "name": "topic_agent",
        "status": "completed",
        "summary": f"Prepared a content plan for '{topic}' with an audience-first angle and a government update framing.",
        "topic": topic,
    }


def script_agent(topic: str) -> dict:
    """Generate the script for the requested topic."""
    script = generate_script(topic)
    return {
        "name": "script_agent",
        "status": "completed",
        "summary": f"Generated a script for '{topic}' with hook, key steps, summary, and CTA.",
        "script": script,
    }


def seo_agent(topic: str, script: str) -> dict:
    """Generate SEO metadata for the script."""
    seo_data = generate_seo(topic, script)
    return {
        "name": "seo_agent",
        "status": "completed",
        "summary": f"Generated optimized title, description, tags, and hashtags for '{topic}'.",
        "payload": seo_data,
    }


def thumbnail_agent(topic: str) -> dict:
    """Generate the thumbnail prompt for the topic."""
    prompt = get_thumbnail_prompt(topic)
    return {
        "name": "thumbnail_agent",
        "status": "completed",
        "summary": f"Created a thumbnail direction for '{topic}' using a high-contrast, attention-first style.",
        "prompt": prompt,
    }


def quality_agent(topic: str, script: str, seo_data: dict) -> dict:
    """Check whether the generated content passes the minimum quality bar."""
    passed = bool(topic and script and seo_data.get("title") and seo_data.get("description"))
    return {
        "name": "quality_agent",
        "status": "completed",
        "summary": "Validated the generated content for completeness and launch readiness." if passed else "Generated content is incomplete and needs review.",
        "passed": passed,
        "notes": "Content is ready for review and publishing." if passed else "Missing script or SEO essentials.",
    }


def build_image_agent(topic: str, source: str = "government") -> dict:
    """Generate the visual image prompt package alongside the script workflow."""
    image_package = build_image_package(topic, source)
    return {
        "name": "image_agent",
        "status": "completed",
        "summary": f"Created a thumbnail/cover visual prompt for '{topic}'.",
        "payload": image_package,
    }
