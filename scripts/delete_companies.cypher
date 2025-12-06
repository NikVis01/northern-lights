// Delete company nodes by organization_id (company_id in Neo4j)
// Usage: Replace <id> with actual organization numbers

// Option 1: Delete a single company and all its relationships
MATCH (c:Company {company_id: "556043-4200"})
DETACH DELETE c;

// Option 2: Delete multiple companies by ID list
MATCH (c:Company)
WHERE c.company_id IN ["556043-4200", "556016-0680", "556013-8298"]
DETACH DELETE c;

// Option 3: Delete company and preserve relationships (delete relationships first, then node)
MATCH (c:Company {company_id: "556043-4200"})-[r]-()
DELETE r, c;

// Option 4: Delete company and all connected nodes (be careful - this is destructive!)
MATCH (c:Company {company_id: "556043-4200"})
OPTIONAL MATCH (c)-[r]-()
DELETE r, c;

// Option 5: Delete companies matching a pattern (e.g., placeholder IDs)
MATCH (c:Company)
WHERE c.company_id =~ '^[A-Z]{1,10}$'  // Matches placeholder IDs like "ERICSSON", "SANDVIK"
DETACH DELETE c;

// Option 6: Safe delete - check what will be deleted first, then delete
// Step 1: See what will be deleted
MATCH (c:Company {company_id: "556043-4200"})
OPTIONAL MATCH (c)-[r]-(connected)
RETURN c, r, connected;

// Step 2: If satisfied, delete
// MATCH (c:Company {company_id: "556043-4200"})
// DETACH DELETE c;


