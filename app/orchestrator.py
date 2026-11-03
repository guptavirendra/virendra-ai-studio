"""Simple orchestration layer for content generation workflows."""

from app.agents import (
    build_image_agent,
    quality_agent,
    script_agent,
    seo_agent,
    thumbnail_agent,
    topic_agent,
)
from app.ai_suggestions import generate_ai_suggestions
from app.video_factory import build_video_plan


def orchestrate_content(topic: str) -> dict:
    """Build a complete content payload for a topic using separate workflow agents."""
    topic_result = topic_agent(topic)
    script_result = script_agent(topic)
    script = script_result["script"]
    seo_result = seo_agent(topic, script)
    seo_data = seo_result["payload"]
    thumbnail_result = thumbnail_agent(topic)
    image_result = build_image_agent(topic, "government")
    video_plan = build_video_plan(topic, script)
    quality_result = quality_agent(topic, script, seo_data)
    suggestions = generate_ai_suggestions(
        topic,
        views=50000,
        ctr=0.06,
        retention=50.0,
        subscribers=600,
    )

    return {
        "topic": topic,
        "script": script,
        "seo": {
            "title": seo_data["title"],
            "description": seo_data["description"],
            "hashtags": seo_data["hashtags"],
            "tags": seo_data["tags"],
        },
        "thumbnail_prompt": thumbnail_result["prompt"],
        "image_prompt": image_result["payload"]["prompt"],
        "video_assets": {
            "voice_style": video_plan["voice_style"],
            "estimated_duration_seconds": video_plan["estimated_duration_seconds"],
            "voiceover_script": video_plan["voiceover_script"],
            "subtitle_srt": video_plan["subtitle_srt"],
            "render": video_plan["render"],
        },
        "ai_suggestions": suggestions,
        "agent_summary": {
            "topic_agent": topic_result,
            "script_agent": script_result,
            "seo_agent": seo_result,
            "thumbnail_agent": thumbnail_result,
            "quality_agent": quality_result,
        },
        "quality_check": {
            "passed": quality_result["passed"],
            "notes": quality_result["notes"],
        },
    }
