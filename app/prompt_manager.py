"""Reusable AI prompt templates for the Virendra AI Studio workflows."""


def get_script_prompt(topic: str) -> str:
    return (
        f"Write a Hindi YouTube script for a government services update on '{topic}'. "
        "Provide a clear structure with Hook, Intro, Step 1, Step 2, Step 3, Summary, and CTA. "
        "Use simple Hindi suitable for short-form video content."
    )


def get_seo_prompt(topic: str) -> str:
    return (
        f"You are a YouTube SEO expert. Create an optimized title, description, hashtags, tags, and chapters "
        f"for a Hindi government services video about '{topic}'. "
        "Use high-CTR language, include relevant keywords, and keep it concise."
    )


def get_thumbnail_prompt(topic: str) -> str:
    return (
        f"Create a bold Hindi YouTube thumbnail prompt for '{topic}' with high contrast colors, "
        "clear government-style visuals, and one strong headline that grabs attention."
    )
