"""Image generation helpers for social and video cover assets."""

from __future__ import annotations


def generate_image_prompt(topic: str, style: str = "government") -> str:
    """Generate a rich visual prompt for a content thumbnail or cover image."""
    clean_topic = (topic or "government update").strip()
    clean_style = (style or "government").strip().lower()

    prompt = (
        f"Create a high-contrast {clean_style} visual prompt for '{clean_topic}'. "
        "Use an eye-catching hero composition, clear modern typography in Hindi, "
        "bright vibrant colors, simple layered shapes, and a polished YouTube thumbnail style. "
        "Keep the layout readable at small sizes, with a strong focal point and minimal clutter."
    )
    return prompt


def build_image_package(topic: str, style: str = "government") -> dict:
    """Return the image-generation payload used by the orchestration layer."""
    return {
        "topic": topic,
        "style": style,
        "prompt": generate_image_prompt(topic, style),
        "aspect_ratio": "16:9",
        "output_format": "jpg",
    }
