"""OpenAI integration helpers for script and SEO generation."""

import openai

from app.config import settings

openai.api_key = settings.OPENAI_API_KEY


def generate_script(topic: str) -> str:
    """Generate a Hindi YouTube script for a government services topic."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = (
        f"Write a Hindi YouTube script for a government services update on '{topic}'. "
        "Provide a clear structure with Hook, Intro, Step 1, Step 2, Step 3, Summary, and CTA. "
        "Use simple Hindi and keep it concise for a short informative video."
    )

    response = openai.ChatCompletion.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that writes Hindi YouTube scripts."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


def generate_seo(topic: str, script: str) -> dict:
    """Generate SEO metadata such as title, description, hashtags, and tags."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    prompt = (
        f"You are a YouTube SEO expert. Create an optimized title, description, hashtags, tags, and chapters "
        f"for a Hindi government services video about '{topic}'. "
        "Use short, high-CTR language and include relevant keywords."
    )

    response = openai.ChatCompletion.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a YouTube SEO content assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.6,
    )

    result = response.choices[0].message.content.strip()
    return {
        "title": topic,
        "description": result,
        "hashtags": "#government #india #updates",
        "tags": [topic, "government update", "online service", "how to"],
        "chapters": result,
    }
