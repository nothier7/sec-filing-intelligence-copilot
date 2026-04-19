from fastapi.testclient import TestClient

from sec_copilot.config import parse_cors_allowed_origins
from sec_copilot.db.session import normalize_database_url
from sec_copilot.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sec-filing-intelligence-copilot",
        "environment": "development",
    }


def test_parse_cors_allowed_origins() -> None:
    assert parse_cors_allowed_origins("https://app.example.com, http://localhost:3000,") == [
        "https://app.example.com",
        "http://localhost:3000",
    ]


def test_normalize_database_url_uses_installed_postgres_driver() -> None:
    assert (
        normalize_database_url("postgresql://user:pass@example.com:5432/app")
        == "postgresql+psycopg://user:pass@example.com:5432/app"
    )
    assert (
        normalize_database_url("postgres://user:pass@example.com:5432/app")
        == "postgresql+psycopg://user:pass@example.com:5432/app"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@example.com:5432/app")
        == "postgresql+psycopg://user:pass@example.com:5432/app"
    )
