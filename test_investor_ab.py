#!/usr/bin/env python3
"""
Test script to create Investor AB and test edge creation with multiple companies.
"""
import requests
import json
import os
from typing import Dict, Any

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "test-key")  # Update with your actual API key
API_VERSION = "v1"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}


def create_investor(investor_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an investor (Fund)"""
    url = f"{API_BASE_URL}/{API_VERSION}/investors"
    response = requests.post(url, json=investor_data, headers=headers)
    response.raise_for_status()
    return response.json()


def create_company(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a company"""
    url = f"{API_BASE_URL}/{API_VERSION}/companies"
    response = requests.post(url, json=company_data, headers=headers)
    response.raise_for_status()
    return response.json()


def create_relationship(source_id: str, target_id: str, ownership_pct: float = None) -> Dict[str, Any]:
    """Create an ownership relationship"""
    url = f"{API_BASE_URL}/{API_VERSION}/relationships"
    data = {
        "source_id": source_id,
        "target_id": target_id,
        "rel_type": "OWNS",
        "ownership_pct": ownership_pct
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()


def get_network(entity_id: str, depth: int = 2) -> Dict[str, Any]:
    """Get network graph for an entity"""
    url = f"{API_BASE_URL}/{API_VERSION}/relationships/network/{entity_id}"
    params = {"depth": depth}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def get_portfolio(investor_id: str) -> Dict[str, Any]:
    """Get portfolio for an investor"""
    url = f"{API_BASE_URL}/{API_VERSION}/investors/{investor_id}/portfolio"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    print("🚀 Testing Investor AB Edge Creation\n")
    
    # Investor AB data (Swedish investment company)
    investor_ab = {
        "name": "Investor AB",
        "organization_id": "556013-8298",  # Real org number
        "investor_type": "fund",
        "country_code": "SE",
        "description": "Swedish investment company, one of the largest in the Nordics"
    }
    
    # Companies that Investor AB owns
    companies = [
        {
            "name": "Ericsson AB",
            "organization_id": "556016-0680",
            "country_code": "SE",
            "description": "Swedish multinational networking and telecommunications company",
            "sectors": ["Telecommunications", "Technology"]
        },
        {
            "name": "Atlas Copco AB",
            "organization_id": "556014-2720",
            "country_code": "SE",
            "description": "Swedish industrial company that manufactures compressors, vacuum solutions and air treatment systems",
            "sectors": ["Industrial", "Manufacturing"]
        },
        {
            "name": "SEB AB",
            "organization_id": "556013-8298",
            "country_code": "SE",
            "description": "Swedish financial services group",
            "sectors": ["Financial Services", "Banking"]
        }
    ]
    
    # Ownership percentages (example data)
    ownership_data = {
        "556016-0680": 22.0,  # Ericsson
        "556014-2720": 17.0,  # Atlas Copco
    }
    
    try:
        # 1. Create Investor AB
        print("1️⃣  Creating Investor AB...")
        investor_result = create_investor(investor_ab)
        investor_id = investor_result["organization_id"]
        print(f"   ✅ Created: {investor_result['name']} (ID: {investor_id})\n")
        
        # 2. Create companies
        print("2️⃣  Creating companies...")
        company_ids = {}
        for company in companies:
            try:
                result = create_company(company)
                company_ids[result["organization_id"]] = result["name"]
                print(f"   ✅ Created: {result['name']} (ID: {result['organization_id']})")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 409:  # Already exists
                    print(f"   ℹ️  Already exists: {company['name']} (ID: {company['organization_id']})")
                    company_ids[company['organization_id']] = company['name']
                else:
                    raise
        print()
        
        # 3. Create ownership relationships
        print("3️⃣  Creating ownership relationships...")
        investor_org_id = investor_ab["organization_id"]
        relationships_created = []
        
        for company_id, ownership_pct in ownership_data.items():
            if company_id in company_ids:
                try:
                    rel_result = create_relationship(
                        source_id=investor_org_id,
                        target_id=company_id,
                        ownership_pct=ownership_pct
                    )
                    relationships_created.append((company_ids[company_id], ownership_pct))
                    print(f"   ✅ Created relationship: Investor AB → {company_ids[company_id]} ({ownership_pct}%)")
                except requests.exceptions.HTTPError as e:
                    print(f"   ❌ Failed to create relationship for {company_ids[company_id]}: {e}")
                    if e.response.text:
                        print(f"      Error: {e.response.text}")
        print()
        
        # 4. Verify portfolio
        print("4️⃣  Verifying portfolio...")
        try:
            portfolio = get_portfolio(investor_id)
            print(f"   ✅ Portfolio contains {len(portfolio.get('holdings', []))} companies:")
            for holding in portfolio.get('holdings', [])[:5]:  # Show first 5
                print(f"      - {holding.get('name', 'Unknown')} ({holding.get('ownership_pct', 'N/A')}%)")
        except Exception as e:
            print(f"   ❌ Failed to get portfolio: {e}")
        print()
        
        # 5. Get network graph
        print("5️⃣  Getting network graph...")
        try:
            network = get_network(investor_id, depth=2)
            print(f"   ✅ Network contains:")
            print(f"      - {len(network.get('nodes', []))} nodes")
            print(f"      - {len(network.get('edges', []))} edges")
            print(f"      - Depth: {network.get('depth', 'N/A')}")
            
            # Show some edges
            edges = network.get('edges', [])
            if edges:
                print(f"\n   Sample edges:")
                for edge in edges[:5]:
                    print(f"      {edge.get('source', '?')} → {edge.get('target', '?')} ({edge.get('rel_type', '?')})")
        except Exception as e:
            print(f"   ❌ Failed to get network: {e}")
        print()
        
        print("✨ Test completed!")
        print(f"\nSummary:")
        print(f"  - Investor created: {investor_result['name']}")
        print(f"  - Companies created/verified: {len(company_ids)}")
        print(f"  - Relationships created: {len(relationships_created)}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        return 1
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())







