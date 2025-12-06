# Edge Generation - Current Implementation

## Overview
Edges (relationships) in the Neo4j graph are created through the **`POST /v1/relationships`** endpoint. Currently, there is **no automatic edge creation** from portfolio/shareholders data during ingestion.

## Current Flow

### 1. Manual Edge Creation via API

**Endpoint:** `POST /v1/relationships`

**Request Body:**
```json
{
  "source_id": "556013-8298",      // Investor AB's org number
  "target_id": "556016-0680",      // Ericsson's org number
  "rel_type": "OWNS",
  "ownership_pct": 22.0,           // Optional: ownership percentage
  "amount": null                   // Optional: investment amount in SEK
}
```

**Flow:**
1. API receives `RelationshipCreate` model
2. Maps `ownership_pct` → `share_percentage` property
3. Calls `relationship_queries.add_ownership()`
4. Neo4j query executes:
   ```cypher
   MATCH (owner {company_id: $owner_id})
   WHERE 'Fund' IN labels(owner) OR 'Company' IN labels(owner)
   MATCH (target:Company {company_id: $company_id})
   MERGE (owner)-[r:OWNS]->(target)
   SET r += $properties, r.updated_at = datetime()
   ```

### 2. Database Query Implementation

**File:** `app/db/queries/relationship_queries.py`

**Function:** `add_ownership(owner_id, company_id, properties)`

**Key Points:**
- Uses `company_id` property in Neo4j (not `organization_id`)
- Source can be `:Fund` or `:Company`
- Target must be `:Company`
- Uses `MERGE` to avoid duplicate edges
- Sets relationship properties: `share_percentage`, `amount`, `updated_at`

### 3. ID Field Mismatch ⚠️

**Issue:** There's a potential mismatch between API and database:

- **API Models** use `organization_id` (Swedish org number)
- **Database Queries** use `company_id` property
- **Mapping:** The routers convert between them in `_db_to_company_out()`

**Current State:**
- `company_queries.py` uses `company_id` in queries
- `relationship_queries.py` uses `company_id` in queries
- API endpoints accept `organization_id` but need to map to `company_id` for DB

### 4. What's NOT Currently Working

#### ❌ Automatic Edge Creation from Portfolio Data
The `CompanyBase` model includes:
- `portfolio: list[EntityRef]` - companies this entity owns
- `shareholders: list[EntityRef]` - entities that own this company
- `customers: list[EntityRef]` - customer relationships

**However:**
- The `/ingest` endpoint (`POST /v1/companies`) only returns a `job_id` - it doesn't process the data
- There's a TODO comment: `# TODO: Push to Pub/Sub`
- No automatic edge creation from these fields

#### ❌ Notebook Script Not Integrated
The `gemini_scraper_test.ipynb` notebook has code to create portfolio relationships:
```python
portfolio_query = """
MATCH (source:Company {company_id: $source_id})
UNWIND $portfolio as item
MERGE (target:Company {name: item.name})
ON CREATE SET target.company_id = coalesce(item.entity_id, randomUUID())
MERGE (source)-[r:OWNS]->(target)
SET r.source = 'llm_ingest'
"""
```

But this is **not integrated into the API** - it's only in the notebook.

## Current Edge Types

Only one relationship type is currently implemented:
- **`OWNS`** - Ownership/investment relationship
  - Properties: `share_percentage`, `amount`, `updated_at`

Other types defined in `RelationType` enum but not used:
- `INVESTED_IN` - Not implemented
- `SUBSIDIARY_OF` - Not implemented

## Reading Edges

### Get Portfolio
**Endpoint:** `GET /v1/investors/{investor_id}/portfolio`

Returns all companies owned by an investor.

### Get Network Graph
**Endpoint:** `GET /v1/relationships/network/{entity_id}?depth=2`

Returns nodes and edges up to specified depth using variable-length path query:
```cypher
MATCH path = (root {company_id: $entity_id})-[r:OWNS*1..$depth]-(connected)
```

## Testing Edge Creation

To test with Investor AB:

1. **Create Investor AB:**
   ```bash
   POST /v1/investors
   {
     "name": "Investor AB",
     "organization_id": "556013-8298",
     "investor_type": "fund",
     "country_code": "SE"
   }
   ```

2. **Create Companies:**
   ```bash
   POST /v1/companies
   {
     "name": "Ericsson AB",
     "organization_id": "556016-0680",
     "country_code": "SE"
   }
   ```

3. **Create Relationship:**
   ```bash
   POST /v1/relationships
   {
     "source_id": "556013-8298",  # Investor AB
     "target_id": "556016-0680",  # Ericsson
     "rel_type": "OWNS",
     "ownership_pct": 22.0
   }
   ```

4. **Verify:**
   ```bash
   GET /v1/investors/556013-8298/portfolio
   GET /v1/relationships/network/556013-8298?depth=2
   ```

## Recommendations

1. **Fix ID Mapping:** Ensure `organization_id` from API is correctly mapped to `company_id` in Neo4j queries
2. **Implement Automatic Edge Creation:** Process `portfolio`, `shareholders`, and `customers` fields during ingestion
3. **Complete Ingestion Pipeline:** Implement the Pub/Sub processing that creates edges from portfolio data
4. **Add Relationship Types:** Implement `INVESTED_IN` and `SUBSIDIARY_OF` if needed

