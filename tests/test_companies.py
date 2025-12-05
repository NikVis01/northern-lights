import pytest


class TestGetCompany:
    def test_existing(self, client):
        r = client.get("/v1/companies/5591234567")
        assert r.status_code == 200
        data = r.json()
        assert data["organization_id"] == "5591234567"
        assert data["name"] == "Spotify AB"
        assert "Technology" in data["sectors"]

    def test_not_found(self, client):
        r = client.get("/v1/companies/9999999999")
        assert r.status_code == 404


class TestIngest:
    def test_ingest_returns_job_id(self, client):
        r = client.post("/v1/companies/ingest", json={"name": "Test Company AB", "organization_id": "1234567890"})
        assert r.status_code == 202
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["name"] == "Test Company AB"


class TestSearch:
    def test_search_basic(self, client):
        r = client.post("/v1/companies/search", json={"query": "music streaming"})
        assert r.status_code == 200
        results = r.json()
        assert len(results) > 0
        assert all("score" in item for item in results)

    def test_search_with_sector_filter(self, client):
        r = client.post("/v1/companies/search", json={
            "query": "technology",
            "sectors": ["Fintech"]
        })
        assert r.status_code == 200
        results = r.json()
        for item in results:
            assert any(s in item["sectors"] for s in ["Fintech", "Banking"])

    def test_search_limit(self, client):
        r = client.post("/v1/companies/search", json={"query": "company", "limit": 1})
        assert r.status_code == 200
        assert len(r.json()) <= 1


class TestLeads:
    def test_leads_same_cluster(self, client):
        r = client.get("/v1/companies/5591234567/leads")
        assert r.status_code == 200
        data = r.json()
        assert data["organization_id"] == "5591234567"
        assert data["cluster_id"] == 1
        # Northvolt is in same cluster
        lead_ids = [l["organization_id"] for l in data["leads"]]
        assert "5569876543" in lead_ids

    def test_leads_not_found(self, client):
        r = client.get("/v1/companies/9999999999/leads")
        assert r.status_code == 404

