"""
AI Search and RAG Pipeline Tests
"""

def test_ai_search_with_offline_fallback(client, seeded_db):
    response = client.post(
        "/api/v1/search/ai",
        json={"query": "What is IMARA ONE privacy architecture?", "max_citations": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "What is IMARA ONE privacy architecture?"
    # Citations should be retrieved from seeded documents
    assert len(data["citations"]) >= 1
    citation = data["citations"][0]
    assert "url" in citation
    assert "snippet" in citation
    assert "https://docs.imaraone.com" in citation["url"]
    assert data["is_available"] is False  # AI_ENABLED is false by default in config


def test_ai_search_empty_context(client, db_session):
    response = client.post(
        "/api/v1/search/ai",
        json={"query": "random obscure non-existent topic xyz123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) == 0
    assert "no relevant indexed documents" in data["answer"].lower()

