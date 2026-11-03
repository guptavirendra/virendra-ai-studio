"""AI-generated recommendations based on content analytics."""

from __future__ import annotations


def generate_ai_suggestions(
    topic: str,
    views: int = 0,
    ctr: float = 0.0,
    retention: float = 0.0,
    subscribers: int = 0,
) -> list[str]:
    """Return actionable, analytics-based suggestions for improving a content item."""
    topic_name = (topic or "government update").strip()
    suggestions: list[str] = []

    if ctr < 0.05:
        suggestions.append(
            f"Improve the title hook for '{topic_name}' by making the first 3 seconds more urgent and benefit-driven."
        )
    else:
        suggestions.append(
            f"Keep the current title structure for '{topic_name}' but tighten the first sentence to improve retention."
        )

    if retention < 45:
        suggestions.append(
            "Trim the intro and move the key update into the first 5 seconds to reduce drop-off and improve viewer retention."
        )
    else:
        suggestions.append(
            "Maintain the current pacing and test one alternate thumbnail variant to lift CTR without losing retention."
        )

    if views < 10000:
        suggestions.append(
            "Publish shorter, sharper clips around the same topic and use a stronger thumbnail headline to reach a broader audience."
        )
    else:
        suggestions.append(
            "Double down on the current topic angle and create a follow-up video that expands the most-watched section."
        )

    if subscribers < 500:
        suggestions.append(
            "Add a direct call to action in the final 10 seconds asking viewers to subscribe for more policy updates."
        )

    return suggestions[:4]
