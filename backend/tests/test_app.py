"""Tests for basic application setup and configuration."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_middleware_configured(client: TestClient):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_settings_defaults():
    s = Settings(database_url="postgresql+asyncpg://test:test@localhost/test", gemini_api_key="test-key")
    assert s.cache_ttl_hours == 24
    assert s.pikabu_retry_delay_429 == 60
    assert s.pikabu_retry_count_5xx == 3
    assert s.pikabu_retry_delay_5xx == 10
    assert s.gemini_max_retries == 3
    assert s.llm_context_window == 131_072


def test_cors_origins_list_parsing():
    s = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        gemini_api_key="test-key",
        cors_origins="http://a.com, http://b.com , http://c.com",
    )
    assert s.cors_origins_list == ["http://a.com", "http://b.com", "http://c.com"]


def test_cors_origins_list_empty_entries():
    s = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        gemini_api_key="test-key",
        cors_origins="http://a.com,,http://b.com,",
    )
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]
