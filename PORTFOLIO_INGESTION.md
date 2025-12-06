# Portfolio Ingestion Implementation

## Overview
The `/ingest` endpoint now integrates `hack_net.py` to extract portfolio companies from Finansinspektionen (FI) documents and recursively process them.

## Flow

1. **POST `/v1/companies/ingest`** with `{name, organization_id}`
2. **Extract Portfolio**: Calls `hack_net.py` to search FI documents and extract portfolio companies
3. **Create/Update Companies**: For each portfolio company:
   - Look up or create company node in Neo4j
   - Create `OWNS` relationship with `share_percentage` property
   - Add to source company's `portfolio` field
4. **Recursive Processing**: For each portfolio company found, recursively:
   - Extract their portfolio from FI documents
   - Process their portfolio companies
   - Prevent cycles using `visited` set

## Key Components

### `app/services/portfolio_ingestion.py`
- `extract_portfolio_from_fi()`: Wraps `hack_net.py` functions
- `lookup_or_create_company()`: Finds or creates company nodes
- `process_portfolio_companies()`: Creates OWNS edges and EntityRefs
- `ingest_company_with_portfolio()`: Main orchestration function

### Updated Models
- `EntityRef`: Added `ownership_pct: Optional[float]` field

### Updated Queries
- `company_queries.upsert_company()`: Now stores `portfolio` field on company node
- `relationship_queries.add_ownership()`: Creates OWNS relationships with `share_percentage`

## Data Structure

### Input
```json
POST /v1/companies/ingest
{
  "name": "Investor AB",
  "organization_id": "556043-4200"
}
```

### Output
```json
{
  "job_id": "...",
  "status": "completed",
  "organization_id": "556043-4200",
  "portfolio_companies_found": 15,
  "companies_processed": 25
}
```

### Neo4j Structure
```
(Company {company_id: "556043-4200", portfolio: [...]})
  -[:OWNS {share_percentage: 22.5}]->(Company {company_id: "556016-0680"})
  -[:OWNS {share_percentage: 15.0}]->(Company {company_id: "..."})
```

## Recursion Prevention
- Uses `visited: Set[str]` to track processed organization IDs
- Prevents infinite loops when companies own each other
- Each company is processed only once per ingestion run




