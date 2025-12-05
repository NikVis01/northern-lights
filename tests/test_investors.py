class TestGetInvestor:
    def test_existing(self, client):
        r = client.get("/v1/investors/INV001")
        assert r.status_code == 200
        data = r.json()
        assert data["investor_id"] == "INV001"
        assert data["name"] == "Sequoia Capital"

    def test_not_found(self, client):
        r = client.get("/v1/investors/INVALID")
        assert r.status_code == 404


class TestPortfolio:
    def test_portfolio(self, client):
        r = client.get("/v1/investors/INV001/portfolio")
        assert r.status_code == 200
        data = r.json()
        assert data["investor_id"] == "INV001"
        assert len(data["holdings"]) > 0
        assert data["holdings"][0]["company_name"] == "Spotify AB"

    def test_portfolio_not_found(self, client):
        r = client.get("/v1/investors/INVALID/portfolio")
        assert r.status_code == 404


class TestCreateInvestor:
    def test_create(self, client):
        r = client.post("/v1/investors/", json={
            "name": "New Fund AB",
            "organization_id": "5563333333",
            "investor_type": "fund"
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "New Fund AB"
        assert "investor_id" in data

