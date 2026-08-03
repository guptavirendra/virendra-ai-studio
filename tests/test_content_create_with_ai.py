from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_content_with_ai_endpoint():
    resp = client.post(
        "/content/create-with-ai",
        json={
            "topic": "EPFO नए नियम",
            "source": "government",
            "confidence": 5,
            "competition": "low",
            "estimated_views": "high",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["topic"] == "EPFO नए नियम"
    assert body["status"] == "draft"
    assert body["script"] is not None
    assert body["seo_title"] is not None
    assert body["seo_description"] is not None
    assert body["hashtags"] is not None
