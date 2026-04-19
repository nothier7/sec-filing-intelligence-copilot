from fastapi.testclient import TestClient

from sec_copilot.config import parse_cors_allowed_origins
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
