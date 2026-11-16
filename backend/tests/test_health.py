"""
Health Check and Root API Tests
"""

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["brand"] == "IMARA ONE"
    assert data["product"] == "IMARA ONE Search"
    assert "version" in data


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data
    assert "database" in data["services"]
    assert data["services"]["database"]["status"] == "healthy"


def test_security_headers_present(client):
    response = client.get("/api/v1/health")
    headers = response.headers
    assert "content-security-policy" in headers
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert "strict-transport-security" in headers
    assert headers.get("x-powered-by") == "IMARA-ONE-Core"

