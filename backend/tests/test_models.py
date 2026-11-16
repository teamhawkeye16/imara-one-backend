"""
Settings, Stats, and Security Events Tests
"""

def test_engine_stats(client, seeded_db):
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_indexed_documents"] >= 2
    assert data["total_domains"] >= 1


def test_user_settings_lifecycle(client):
    # 1. Fetch default settings
    response = client.get("/api/v1/settings", headers={"x-client-token": "test_user_token_1"})
    assert response.status_code == 200
    data = response.json()
    assert data["safe_search"] == "moderate"
    assert data["privacy_level"] == "maximum"

    # 2. Update settings
    update_res = client.post(
        "/api/v1/settings",
        json={"safe_search": "strict", "privacy_level": "maximum", "theme": "dark"},
        headers={"x-client-token": "test_user_token_1"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["safe_search"] == "strict"

    # 3. Verify updated settings
    verify_res = client.get("/api/v1/settings", headers={"x-client-token": "test_user_token_1"})
    assert verify_res.status_code == 200
    assert verify_res.json()["safe_search"] == "strict"

