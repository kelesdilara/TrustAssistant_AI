from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint_returns_healthy():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_analysis_route_is_registered():
    paths = {route.path for route in app.routes}

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/analysis/" in paths
    assert "/api/v1/analysis/history" in paths
    assert "/scraper/product" in paths
