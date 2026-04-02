from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


def create_test_client() -> TestClient:
    tmp_path = Path(__file__).resolve().parent.parent / ".test-temp"
    tmp_path.mkdir(exist_ok=True)
    database_url = f"sqlite:///{tmp_path / f'auth-test-{uuid4().hex}.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


def test_register_device_returns_access_token() -> None:
    client = create_test_client()

    response = client.post(
        "/register-device",
        json={"telegram": False, "user_agent": "pytest-browser"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    app.dependency_overrides.clear()


def test_playback_requires_bearer_token() -> None:
    client = create_test_client()

    response = client.post(
        "/engagement/playback",
        json={
            "artist": "Tester",
            "song_id": "song-auth-check",
            "title": "Auth Check",
        },
    )

    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_playback_uses_authenticated_user() -> None:
    client = create_test_client()

    register = client.post(
        "/register-device",
        json={"telegram": False, "user_agent": "pytest-browser"},
    )
    token = register.json()["access_token"]
    user_id = register.json()["user_id"]

    response = client.post(
        "/engagement/playback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "artist": "Tester",
            "genre": "Test",
            "song_id": "song-auth-success",
            "title": "Authenticated Playback",
            "user_id": 999999,
        },
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    app.dependency_overrides.clear()
