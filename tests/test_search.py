class TestUnifiedSearch:
    def test_search_all(self, client):
        r = client.post("/v1/search/", json={"query": "technology"})
        assert r.status_code == 200
        results = r.json()
        assert len(results) > 0
        types = {item["entity_type"] for item in results}
        assert "company" in types
        assert "investor" in types

    def test_search_companies_only(self, client):
        r = client.post("/v1/search/", json={
            "query": "music",
            "entity_types": ["company"]
        })
        assert r.status_code == 200
        results = r.json()
        assert all(item["entity_type"] == "company" for item in results)

    def test_search_sorted_by_score(self, client):
        r = client.post("/v1/search/", json={"query": "test"})
        assert r.status_code == 200
        results = r.json()
        scores = [item["score"] for item in results]
        assert scores == sorted(scores, reverse=True)

