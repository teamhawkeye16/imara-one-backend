"""
Search and Suggestions Tests
"""

def test_search_empty_query_rejected(client):
    response = client.get("/api/v1/search?q=")
    assert response.status_code == 422  # Pydantic validation error


def test_search_query_execution_with_results(client, seeded_db):
    response = client.get("/api/v1/search?q=privacy")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "privacy"
    assert data["total_hits"] >= 1
    assert len(data["hits"]) >= 1
    hit = data["hits"][0]
    assert "privacy" in hit["title"].lower() or "privacy" in hit["snippet"].lower()
    assert hit["domain"] == "docs.imaraone.com"
    assert data["response_time_ms"] >= 0.0


def test_search_empty_index_message(client, db_session):
    # db_session has no seeded docs
    response = client.get("/api/v1/search?q=nonexistentkeyword123")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hits"] == 0
    assert data["is_empty"] is True
    assert data["message"] is not None
    assert "empty" in data["message"].lower() or "no results" in data["message"].lower()


def test_search_suggestions(client, seeded_db):
    response = client.get("/api/v1/search/suggest?q=priv")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "priv"
    assert len(data["suggestions"]) >= 1
    assert any("privacy" in s.lower() for s in data["suggestions"])


def test_search_pagination(client, seeded_db):
    response = client.get("/api/v1/search?q=imara&page=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 1
    assert len(data["hits"]) == 1
    assert data["total_pages"] >= 2


def test_search_with_site_operator(client, seeded_db):
    response = client.get("/api/v1/search?q=privacy site:docs.imaraone.com")
    assert response.status_code == 200
    data = response.json()
    assert data["total_hits"] >= 1
    assert all("docs.imaraone.com" in h["domain"] for h in data["hits"])

    # Test filtering out a site that does not match
    nomatch_res = client.get("/api/v1/search?q=privacy site:nonexistentsite.org")
    assert nomatch_res.status_code == 200
    assert nomatch_res.json()["total_hits"] == 0

