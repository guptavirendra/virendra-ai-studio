"""OpenAI integration helpers for script and SEO generation."""

import openai

from app.config import settings
from app.fallbacks import build_script, build_seo
from app.prompt_manager import get_script_prompt, get_seo_prompt

openai.api_key = settings.OPENAI_API_KEY


def _openai_completion(messages, max_tokens: int):
    return openai.ChatCompletion.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )


def generate_script(topic: str) -> str:
    """Generate a Hindi YouTube script for a government services topic."""
    prompt = get_script_prompt(topic)
    try:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = _openai_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes Hindi YouTube scripts."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )

        return response.choices[0].message.content.strip()
    except Exception:
        return build_script(topic)


def generate_seo(topic: str, script: str) -> dict:
    """Generate SEO metadata such as title, description, hashtags, and tags."""
    prompt = get_seo_prompt(topic)
    try:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        response = _openai_completion(
            messages=[
                {"role": "system", "content": "You are a YouTube SEO content assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
        )

        result = response.choices[0].message.content.strip()
        return {
            "title": topic,
            "description": result,
            "hashtags": "#government #india #updates",
            "tags": [topic, "government update", "online service", "how to"],
            "chapters": result,
        }
    except Exception:
        return build_seo(topic)
