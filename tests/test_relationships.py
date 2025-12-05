class TestCreateRelationship:
    def test_create(self, client):
        r = client.post("/v1/relationships/", json={
            "source_id": "INV001",
            "target_id": "5591234567",
            "rel_type": "INVESTED_IN",
            "ownership_pct": 5.0
        })
        assert r.status_code == 201
        data = r.json()
        assert data["source_id"] == "INV001"
        assert data["rel_type"] == "INVESTED_IN"


class TestNetwork:
    def test_network_spotify(self, client):
        r = client.get("/v1/relationships/network/5591234567")
        assert r.status_code == 200
        data = r.json()
        assert data["root_id"] == "5591234567"
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0

    def test_network_unknown(self, client):
        r = client.get("/v1/relationships/network/UNKNOWN")
        assert r.status_code == 200
        data = r.json()
        assert data["root_id"] == "UNKNOWN"
        assert len(data["edges"]) == 0

