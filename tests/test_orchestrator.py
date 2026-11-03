from app.orchestrator import orchestrate_content


def test_orchestrate_content_returns_complete_payload():
    result = orchestrate_content("EPFO नए नियम")

    assert result["topic"] == "EPFO नए नियम"
    assert "script" in result
    assert "seo" in result
    assert "thumbnail_prompt" in result
    assert "agent_summary" in result
    assert set(result["agent_summary"]).issuperset({"topic_agent", "script_agent", "seo_agent", "thumbnail_agent", "quality_agent"})
    assert result["quality_check"]["passed"] is True
    assert "EPFO" in result["script"] or "EPFO" in result["seo"]["title"]
