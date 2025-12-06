# LLM Edge Discovery - Implementation Summary

## How It Currently Works

### Current Flow
1. **LLM extracts structured data** → `CompanyIngest` with `portfolio[]`, `shareholders[]`, `customers[]`
2. **Data stored in Neo4j** → Company node properties only (no edges)
3. **Manual edge creation required** → Must call `POST /v1/relationships` for each relationship

### The Gap
- LLM **already extracts** relationship data (EntityRef lists)
- But this data is **not automatically converted to edges**
- Relationships exist as **properties**, not as **graph relationships**

## What Needs to Change

### 1. **ID Mapping Fix** (Critical)
**Issue:** API uses `organization_id`, DB queries use `company_id`

**Current:**
```python
# API endpoint
@router.get("/{organization_id}")
db_data = company_queries.get_company(organization_id)  # Passes org_id

# DB query
def get_company(company_id: str):  # Expects company_id
    MATCH (c:Company {company_id: $company_id})  # Uses company_id property
```

**Fix:** Either:
- **Option A:** Store `organization_id` as `company_id` in Neo4j (they're the same value)
- **Option B:** Add mapping layer in routers/queries

**Recommendation:** Option A - Swedish org numbers are unique identifiers, so `organization_id` = `company_id`

### 2. **Create EdgeService** (New Component)

**Purpose:** Process EntityRef lists and create edges automatically

**Location:** `app/services/edge_service.py`

**Key Methods:**
```python
class EdgeService:
    def process_portfolio_relationships(source_org_id, portfolio: list[EntityRef])
        # For each entity in portfolio:
        #   Create edge: (source)-[:OWNS]->(target)
    
    def process_shareholder_relationships(target_org_id, shareholders: list[EntityRef])
        # For each shareholder:
        #   Create edge: (shareholder)-[:OWNS]->(target)
    
    def find_or_create_node(entity_ref: EntityRef)
        # Find node by organization_id or name
        # Create placeholder if not found
```

### 3. **Update Ingestion Endpoint** (Integration Point)

**Current:**
```python
@router.post("/ingest")
async def ingest_company(body: CompanyIngest, ...):
    job_id = str(uuid4())
    # TODO: Push to Pub/Sub
    return {"job_id": job_id, "status": "queued"}
```

**New:**
```python
@router.post("/ingest")
async def ingest_company(body: CompanyIngest, ...):
    # 1. Upsert company node
    company_queries.upsert_company(body.model_dump())
    
    # 2. Process relationships (NEW)
    edge_service = EdgeService()
    if body.portfolio:
        edge_service.process_portfolio_relationships(
            body.organization_id, 
            body.portfolio
        )
    if body.shareholders:
        edge_service.process_shareholder_relationships(
            body.organization_id,
            body.shareholders
        )
    
    return {"status": "completed", "organization_id": body.organization_id}
```

### 4. **Update Relationship Queries** (Database Layer)

**Add new function:**
```python
# app/db/queries/relationship_queries.py

def create_relationship_from_entity_ref(
    source_org_id: str,
    target_entity_ref: EntityRef,
    direction: str = "outgoing"  # "outgoing" or "incoming"
):
    """
    Create OWNS relationship from EntityRef.
    
    direction="outgoing": (source)-[:OWNS]->(target)
    direction="incoming": (target)-[:OWNS]->(source)
    """
    properties = {}
    if target_entity_ref.ownership_pct:
        properties["share_percentage"] = target_entity_ref.ownership_pct
    
    if direction == "outgoing":
        # (source)-[:OWNS]->(target)
        owner_id = source_org_id
        company_id = target_entity_ref.entity_id
    else:
        # (target)-[:OWNS]->(source)
        owner_id = target_entity_ref.entity_id
        company_id = source_org_id
    
    add_ownership(owner_id, company_id, properties)
```

### 5. **Enhance EntityRef Model** (Data Model)

**Current:**
```python
class EntityRef(BaseModel):
    entity_id: str
    name: str
    entity_type: str = "company"
```

**Enhanced:**
```python
class EntityRef(BaseModel):
    entity_id: str
    name: str
    entity_type: str = "company"
    ownership_pct: Optional[float] = None  # NEW: From LLM extraction
```

**Update LLM prompt** to extract ownership percentages when available.

## Example: Investor AB → Ericsson

### Current (Manual)
```bash
# 1. Create Investor AB
POST /v1/investors
{"name": "Investor AB", "organization_id": "556013-8298", ...}

# 2. Create Ericsson
POST /v1/companies
{"name": "Ericsson AB", "organization_id": "556016-0680", ...}

# 3. Manually create edge
POST /v1/relationships
{
  "source_id": "556013-8298",
  "target_id": "556016-0680",
  "rel_type": "OWNS",
  "ownership_pct": 22.0
}
```

### New (Automatic)
```bash
# 1. LLM structures Ericsson data (includes shareholders)
POST /v1/companies/ingest
{
  "name": "Ericsson AB",
  "organization_id": "556016-0680",
  "shareholders": [
    {
      "entity_id": "556013-8298",
      "name": "Investor AB",
      "entity_type": "fund",
      "ownership_pct": 22.0
    }
  ]
}

# 2. System automatically:
#    - Creates Ericsson node
#    - Finds/creates Investor AB node
#    - Creates edge: (Investor AB)-[:OWNS]->(Ericsson)
#    - Sets share_percentage = 22.0

# 3. Verify (no manual step needed)
GET /v1/investors/556013-8298/portfolio
# Returns: [{"name": "Ericsson AB", "ownership_pct": 22.0, ...}]
```

## Common Investor Discovery

### How It Works
Once edges are created, you can query for common investors:

```cypher
// Find all companies that share Investor AB as shareholder
MATCH (investor {company_id: "556013-8298"})-[r:OWNS]->(company:Company)
RETURN company.name, r.share_percentage

// Find companies with common investors
MATCH (investor)-[:OWNS]->(company1:Company {company_id: "556016-0680"})
MATCH (investor)-[:OWNS]->(company2:Company)
WHERE company1 <> company2
RETURN company2.name, investor.name
```

### API Endpoint (Future Enhancement)
```python
@router.get("/companies/{org_id}/common-investors")
async def get_companies_with_common_investors(org_id: str):
    """
    Find companies that share investors with the given company.
    """
    # Query Neo4j for companies with overlapping shareholders
    pass
```

## Implementation Priority

### Phase 1: Core Functionality (Required)
1. ✅ Fix ID mapping (`organization_id` → `company_id`)
2. ✅ Create `EdgeService` class
3. ✅ Add `create_relationship_from_entity_ref()` to queries
4. ✅ Update `EntityRef` model with `ownership_pct`
5. ✅ Integrate edge creation into ingestion endpoint

### Phase 2: Enhancements (Nice to Have)
6. ✅ Handle missing nodes (create placeholders or fuzzy match)
7. ✅ Add relationship confidence scores
8. ✅ Implement common investor discovery endpoint
9. ✅ Add batch processing for multiple companies

## Files to Create/Modify

### New Files
- `app/services/edge_service.py` - Edge processing logic

### Modified Files
- `app/models/company.py` - Add `ownership_pct` to `EntityRef`
- `app/db/queries/relationship_queries.py` - Add `create_relationship_from_entity_ref()`
- `app/routers/companies.py` - Process edges in `/ingest` endpoint
- `app/db/queries/company_queries.py` - Fix ID mapping
- `app/db/queries/investor_queries.py` - Fix ID mapping
- `app/services/prompts/structure_data.xml` - Enhance to extract ownership percentages

## Testing

### Test Case: Investor AB → Ericsson
1. Ingest Ericsson with Investor AB in shareholders
2. Verify Investor AB node exists (or created)
3. Verify edge exists: `(Investor AB)-[:OWNS]->(Ericsson)`
4. Verify `GET /v1/investors/556013-8298/portfolio` returns Ericsson
5. Verify `GET /v1/relationships/network/556013-8298` shows edge

### Test Case: Multiple Companies, Common Investor
1. Ingest Ericsson (shareholder: Investor AB)
2. Ingest Atlas Copco (shareholder: Investor AB)
3. Query for common investors → Should return Investor AB for both




