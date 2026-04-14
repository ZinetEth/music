from fastapi.testclient import TestClient

from app.main import app


def test_recommendation_feed_returns_source_fields() -> None:
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register-device",
        json={"telegram": False, "user_agent": "pytest-browser"},
    )
    token = register.json()["access_token"]
    user_id = register.json()["user_id"]

    playback = client.post(
        "/api/v1/playback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "artist": "Route Tester",
            "genre": "Jazz",
            "song_id": "route-test-song",
            "title": "Route Test Song",
            "tempo": 110,
            "completed_ratio": 0.95,
        },
    )
    assert playback.status_code == 200

    response = client.get(f"/api/v1/recommendations/feed?user_id={user_id}&limit=3")
    assert response.status_code == 200
    body = response.json()
    assert len(body["recommendations"]) == 3
    first = body["recommendations"][0]
    assert "source" in first
    assert "source_metadata" in first
