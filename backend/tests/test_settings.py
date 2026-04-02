from app.core.settings import AppSettings, get_settings


def test_settings_defaults() -> None:
    get_settings.cache_clear()
    settings = AppSettings()

    assert settings.app_title == "Music Platform Backend"
    assert settings.app_version == "1.0.0"
    assert settings.admin_api_key
    assert settings.access_token_ttl_seconds == 86400
    assert settings.database_url
    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]


def test_production_requires_real_secrets(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    try:
        AppSettings()
    except ValueError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("Expected production settings validation to fail")


def test_production_accepts_postgres_with_real_secrets(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("SECRET_KEY", "super-secret-value")
    monkeypatch.setenv("ADMIN_API_KEY", "super-admin-key")

    settings = AppSettings()

    assert settings.is_postgres is True
    assert settings.is_production is True
