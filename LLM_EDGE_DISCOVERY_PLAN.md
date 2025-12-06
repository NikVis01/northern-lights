# LLM-Driven Edge Discovery & Automatic Edge Creation

## Current State vs. Desired State

### Current State
1. **LLM structures data** → Extracts `portfolio`, `shareholders`, `customers` as `EntityRef[]` lists
2. **Data stored in Neo4j** → Company nodes with properties, but **no edges created**
3. **Manual edge creation** → Must call `POST /v1/relationships` manually

### Desired State
1. **LLM structures data** → Extracts relationships from unstructured text
2. **Automatic edge creation** → When LLM finds "Investor AB invests in Ericsson", create `OWNS` edge
3. **Common investor discovery** → If Company A and B both have Investor X, they share a common investor
4. **Bidirectional discovery** → From both `portfolio` (what I own) and `shareholders` (who owns me)

## Implementation Strategy

### Option 1: Post-Processing After LLM Structuring (Recommended)
**When:** After LLM returns structured `CompanyIngest` data

**Flow:**
```
LLM Structures Data → CompanyIngest (with portfolio/shareholders)
    ↓
Process EntityRef Lists
    ↓
For each EntityRef in portfolio: Create (source)-[:OWNS]->(target)
For each EntityRef in shareholders: Create (shareholder)-[:OWNS]->(source)
    ↓
Upsert Company Node + Create Edges
```

**Pros:**
- Uses existing LLM output (EntityRef lists)
- No additional LLM calls needed
- Fast and efficient

**Cons:**
- Relies on LLM correctly extracting relationships
- May miss implicit relationships

### Option 2: Dedicated LLM Relationship Extraction
**When:** Separate analysis step after initial structuring

**Flow:**
```
LLM Structures Basic Data → Company Node Created
    ↓
LLM Analyzes Text for Relationships
    ↓
Extract: "Investor AB owns 22% of Ericsson"
    ↓
Create Edge with ownership_pct
```

**Pros:**
- Can extract ownership percentages
- Can discover relationships not in structured fields
- More accurate relationship data

**Cons:**
- Additional LLM call (cost + latency)
- More complex implementation

### Option 3: Hybrid Approach (Best)
**When:** Both during structuring and post-processing

**Flow:**
1. **During Structuring:** LLM extracts EntityRef lists (current)
2. **Post-Processing:** Create edges from EntityRef lists
3. **Optional Enhancement:** LLM analyzes text for ownership percentages

## Required Changes

### 1. Fix ID Mapping Consistency

**Problem:** API uses `organization_id`, DB uses `company_id`

**Solution:** Standardize on `organization_id` everywhere OR add mapping layer

**Files to change:**
- `app/db/queries/company_queries.py` - Use `organization_id` instead of `company_id`
- `app/db/queries/investor_queries.py` - Use `organization_id`
- `app/db/queries/relationship_queries.py` - Use `organization_id`

**OR** add mapping in routers:
```python
# In routers, map organization_id → company_id before DB calls
company_id = organization_id  # They're the same (Swedish org number)
```

### 2. Create Edge Processing Service

**New File:** `app/services/edge_service.py`

```python
class EdgeService:
    def process_portfolio_relationships(
        self, 
        source_org_id: str, 
        portfolio: list[EntityRef]
    ):
        """Create OWNS edges from portfolio list"""
        for entity in portfolio:
            # Try to find existing node by org_id or name
            # Create edge: (source)-[:OWNS]->(target)
            pass
    
    def process_shareholder_relationships(
        self,
        target_org_id: str,
        shareholders: list[EntityRef]
    ):
        """Create OWNS edges from shareholders list (reverse)"""
        for shareholder in shareholders:
            # Create edge: (shareholder)-[:OWNS]->(target)
            pass
    
    def discover_common_investors(self, org_id: str):
        """Find companies with common investors"""
        # Query: Find all companies that share shareholders with this company
        pass
```

### 3. Complete Ingestion Pipeline

**Current:** `POST /v1/companies` just returns `job_id`

**Change:** Actually process the data

**Option A: Synchronous Processing**
```python
@router.post("/ingest")
async def ingest_company(body: CompanyIngest, ...):
    # 1. Upsert company node
    company_queries.upsert_company(...)
    
    # 2. Process relationships
    edge_service = EdgeService()
    edge_service.process_portfolio_relationships(
        body.organization_id, 
        body.portfolio
    )
    edge_service.process_shareholder_relationships(
        body.organization_id,
        body.shareholders
    )
    
    return {"status": "completed", ...}
```

**Option B: Async via Pub/Sub (Original Plan)**
```python
@router.post("/ingest")
async def ingest_company(body: CompanyIngest, ...):
    # Push to Pub/Sub
    pubsub_client.publish(topic, body.model_dump_json())
    return {"job_id": job_id, "status": "queued"}

# Separate worker processes Pub/Sub messages
def process_ingestion(message):
    data = CompanyIngest.parse_raw(message)
    # Upsert + create edges
```

### 4. Enhanced LLM Prompt for Relationship Extraction

**Add to `structure_data.xml`:**
```xml
<relationship_extraction>
    <instruction>
        When extracting portfolio/shareholders, also extract ownership percentages if mentioned.
        Format: {"entity_id": "...", "name": "...", "ownership_pct": 22.0}
    </instruction>
    <examples>
        "Investor AB owns 22% of Ericsson" → portfolio: [{"entity_id": "556013-8298", "name": "Investor AB", "ownership_pct": 22.0}]
        "Major shareholders include Investor AB (22%) and Handelsbanken (5%)" → shareholders: [{"entity_id": "556013-8298", "name": "Investor AB", "ownership_pct": 22.0}, ...]
    </examples>
</relationship_extraction>
```

**OR create separate prompt:** `extract_relationships.xml`
- Input: Unstructured text about company
- Output: List of relationships with ownership percentages

### 5. Update EntityRef Model

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
    relationship_type: Optional[str] = None  # "OWNS", "INVESTED_IN", etc.
```

### 6. Database Query Updates

**New function in `relationship_queries.py`:**
```python
def create_relationships_from_entity_refs(
    source_org_id: str,
    entity_refs: list[EntityRef],
    relationship_direction: str = "outgoing"  # "outgoing" = source OWNS target, "incoming" = target OWNS source
):
    """
    Create multiple OWNS relationships from EntityRef list.
    
    For portfolio: relationship_direction="outgoing" → (source)-[:OWNS]->(target)
    For shareholders: relationship_direction="incoming" → (shareholder)-[:OWNS]->(source)
    """
    for entity_ref in entity_refs:
        # Try to find target node by organization_id
        # If not found, try by name (may need fuzzy matching)
        # Create edge with ownership_pct if available
        pass
```

## Implementation Steps

### Phase 1: Foundation (Required)
1. ✅ Fix ID mapping (`organization_id` vs `company_id`)
2. ✅ Create `EdgeService` class
3. ✅ Add `create_relationships_from_entity_refs()` to `relationship_queries.py`
4. ✅ Update `EntityRef` model to include `ownership_pct`

### Phase 2: Integration (Core Feature)
5. ✅ Update ingestion endpoint to process relationships
6. ✅ Call `EdgeService` after company upsert
7. ✅ Handle missing nodes (create placeholder or skip)

### Phase 3: Enhancement (Optional)
8. ✅ Add LLM relationship extraction prompt
9. ✅ Implement common investor discovery
10. ✅ Add relationship confidence scores

## Example Flow: Investor AB → Ericsson

### Step 1: LLM Structures Data
**Input:** Unstructured text about Ericsson
**Output:**
```json
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
```

### Step 2: Upsert Company Node
```cypher
MERGE (c:Company {company_id: "556016-0680"})
SET c.name = "Ericsson AB", ...
```

### Step 3: Process Shareholders (Automatic)
```python
edge_service.process_shareholder_relationships(
    "556016-0680",  # Ericsson
    [EntityRef(entity_id="556013-8298", name="Investor AB", ownership_pct=22.0)]
)
```

### Step 4: Create Edge
```cypher
MATCH (investor {company_id: "556013-8298"})  # Investor AB
MATCH (company:Company {company_id: "556016-0680"})  # Ericsson
MERGE (investor)-[r:OWNS]->(company)
SET r.share_percentage = 22.0, r.source = "llm_ingest"
```

### Step 5: Discover Common Investors
```cypher
// Find all companies that share Investor AB as shareholder
MATCH (investor {company_id: "556013-8298"})-[r:OWNS]->(company:Company)
RETURN company.organization_id, company.name
// Result: Ericsson, Atlas Copco, SEB, etc.
```

## Code Structure

```
app/
├── services/
│   ├── edge_service.py          # NEW: Edge processing logic
│   └── graph_service.py          # Existing
├── db/
│   └── queries/
│       └── relationship_queries.py  # ADD: create_relationships_from_entity_refs()
├── routers/
│   └── companies.py              # UPDATE: Process edges in /ingest
└── models/
    └── company.py                 # UPDATE: EntityRef with ownership_pct
```

## Testing Strategy

1. **Unit Tests:** `EdgeService` methods
2. **Integration Tests:** Full ingestion flow with edge creation
3. **End-to-End:** 
   - Ingest Ericsson with Investor AB as shareholder
   - Verify `GET /v1/investors/556013-8298/portfolio` returns Ericsson
   - Verify `GET /v1/relationships/network/556013-8298` shows edge

## Benefits

1. **Automatic Discovery:** No manual edge creation needed
2. **Comprehensive Graph:** All relationships from LLM extraction
3. **Common Investor Analysis:** Easy to find companies with shared investors
4. **Scalable:** Works for thousands of companies automatically





