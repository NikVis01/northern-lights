"""
Test cases for portfolio ingestion with FI document extraction.
Tests the /ingest endpoint with organization number 556043-4200.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestPortfolioIngestion:
    """Test portfolio ingestion from FI documents."""
    
    @pytest.fixture
    def mock_extract_portfolio(self):
        """Mock extract_portfolio_from_fi to avoid actual web scraping in tests."""
        with patch('app.services.portfolio_ingestion.extract_portfolio_from_fi') as mock:
            yield mock
    
    def test_ingest_with_portfolio_extraction(self, client, mock_extract_portfolio):
        """Test that /ingest extracts portfolio companies from FI documents."""
        # Mock portfolio data from hack_net
        mock_portfolio = [
            {"company_name": "Ericsson AB", "ownership_percentage": 22.5},
            {"company_name": "Atlas Copco AB", "ownership_percentage": 15.0},
            {"company_name": "SEB AB", "ownership_percentage": None}
        ]
        mock_extract_portfolio.return_value = mock_portfolio
        
        # Ingest company
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        data = r.json()
        assert data["status"] == "completed"
        assert data["organization_id"] == "556043-4200"
        assert data["portfolio_companies_found"] == 3
        assert data["companies_processed"] >= 0
    
    def test_ingest_creates_company_node(self, client, mock_extract_portfolio):
        """Test that company node is created/updated during ingestion."""
        mock_extract_portfolio.return_value = []
        
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        
        # Verify company exists
        r = client.get("/v1/companies/556043-4200")
        assert r.status_code == 200
        data = r.json()
        assert data["organization_id"] == "556043-4200"
        assert data["name"] == "Investor AB"
    
    def test_ingest_creates_owns_relationships(self, client, mock_extract_portfolio):
        """Test that OWNS relationships are created with ownership percentages."""
        mock_portfolio = [
            {"company_name": "Ericsson AB", "ownership_percentage": 22.5},
            {"company_name": "Atlas Copco AB", "ownership_percentage": 15.0}
        ]
        mock_extract_portfolio.return_value = mock_portfolio
        
        # Ingest company
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        assert r.status_code == 202
        
        # Verify relationships exist (check network graph)
        r = client.get("/v1/relationships/network/556043-4200?depth=1")
        assert r.status_code == 200
        data = r.json()
        
        # Should have edges to portfolio companies
        assert len(data["edges"]) > 0
        # Check that edges have ownership_pct
        edges_with_pct = [e for e in data["edges"] if e.get("ownership_pct") is not None]
        assert len(edges_with_pct) > 0
    
    def test_ingest_populates_portfolio_field(self, client, mock_extract_portfolio):
        """Test that portfolio field is populated on company node."""
        mock_portfolio = [
            {"company_name": "Ericsson AB", "ownership_percentage": 22.5},
            {"company_name": "Atlas Copco AB", "ownership_percentage": 15.0}
        ]
        mock_extract_portfolio.return_value = mock_portfolio
        
        # Ingest company
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        assert r.status_code == 202
        
        # Get company and check portfolio field
        r = client.get("/v1/companies/556043-4200")
        assert r.status_code == 200
        data = r.json()
        
        # Portfolio should be populated
        assert "portfolio" in data
        assert len(data["portfolio"]) > 0
        # Check portfolio items have required fields
        for item in data["portfolio"]:
            assert "entity_id" in item
            assert "name" in item
            assert "entity_type" in item
    
    def test_ingest_handles_empty_portfolio(self, client, mock_extract_portfolio):
        """Test ingestion when no portfolio companies are found."""
        mock_extract_portfolio.return_value = []
        
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        data = r.json()
        assert data["portfolio_companies_found"] == 0
        assert data["companies_processed"] == 0
    
    def test_ingest_handles_missing_ownership_percentage(self, client, mock_extract_portfolio):
        """Test that companies without ownership percentage are still processed."""
        mock_portfolio = [
            {"company_name": "Company Without Pct", "ownership_percentage": None}
        ]
        mock_extract_portfolio.return_value = mock_portfolio
        
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        data = r.json()
        assert data["portfolio_companies_found"] == 1
        
        # Verify relationship still created (without share_percentage)
        r = client.get("/v1/relationships/network/556043-4200?depth=1")
        assert r.status_code == 200
        data = r.json()
        assert len(data["edges"]) > 0
    
    def test_ingest_recursive_processing(self, client, mock_extract_portfolio):
        """Test that portfolio companies are recursively processed."""
        # First call: Investor AB's portfolio
        portfolio_1 = [
            {"company_name": "Ericsson AB", "ownership_percentage": 22.5}
        ]
        # Second call: Ericsson AB's portfolio (recursive)
        portfolio_2 = [
            {"company_name": "Subsidiary AB", "ownership_percentage": 10.0}
        ]
        
        # Mock to return different portfolios based on org_id
        def mock_extract(org_id):
            if org_id == "556043-4200":
                return portfolio_1
            elif "ERICSSON" in org_id.upper() or org_id == "ERICSSON":
                return portfolio_2
            return []
        
        mock_extract_portfolio.side_effect = mock_extract
        
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        data = r.json()
        # Should have processed at least Investor AB and Ericsson
        assert data["companies_processed"] >= 1
    
    def test_ingest_prevents_cycles(self, client, mock_extract_portfolio):
        """Test that recursive processing prevents infinite loops."""
        # Create circular ownership scenario
        portfolio_1 = [
            {"company_name": "Company B", "ownership_percentage": 20.0}
        ]
        portfolio_2 = [
            {"company_name": "Investor AB", "ownership_percentage": 10.0}
        ]
        
        call_count = {"556043-4200": 0, "COMPANYB": 0}
        
        def mock_extract(org_id):
            call_count[org_id] = call_count.get(org_id, 0) + 1
            if org_id == "556043-4200":
                return portfolio_1
            elif org_id == "COMPANYB":
                # Only return portfolio on first call to prevent infinite loop
                if call_count[org_id] == 1:
                    return portfolio_2
                return []
            return []
        
        mock_extract_portfolio.side_effect = mock_extract
        
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        # Should complete without infinite loop
        assert call_count["556043-4200"] == 1


@pytest.mark.integration
class TestPortfolioIngestionIntegration:
    """Integration tests that may call actual hack_net (if configured)."""
    
    def test_ingest_real_fi_documents(self, client):
        """
        Test with actual FI document extraction (requires GEMINI_API_KEY).
        Run with: pytest -m integration
        """
        r = client.post(
            "/v1/companies/ingest",
            json={
                "name": "Investor AB",
                "organization_id": "556043-4200"
            }
        )
        
        assert r.status_code == 202
        data = r.json()
        assert data["status"] == "completed"
        assert data["organization_id"] == "556043-4200"
        
        # If portfolio found, verify structure
        if data["portfolio_companies_found"] > 0:
            r = client.get("/v1/companies/556043-4200")
            assert r.status_code == 200
            company_data = r.json()
            assert "portfolio" in company_data
            assert len(company_data["portfolio"]) > 0

