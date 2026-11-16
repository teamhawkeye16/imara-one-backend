"""
Crawler API and SSRF Protection Tests
"""

def test_crawler_submit_rejects_private_ip(client):
    response = client.post(
        "/api/v1/crawler/submit",
        json={"url": "http://127.0.0.1:8000/admin"},
    )
    assert response.status_code == 400
    assert "ssrf" in response.json()["detail"].lower()


def test_crawler_submit_rejects_localhost(client):
    response = client.post(
        "/api/v1/crawler/submit",
        json={"url": "http://localhost:3000"},
    )
    assert response.status_code == 400


def test_crawler_submit_accepts_valid_public_domain(client):
    response = client.post(
        "/api/v1/crawler/submit",
        json={"url": "https://example.com", "max_pages": 5, "max_depth": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert data["domain"] == "example.com"


def test_crawler_status_not_found(client):
    response = client.get("/api/v1/crawler/status/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

