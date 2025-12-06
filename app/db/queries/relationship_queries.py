from app.db.neo4j_client import get_driver
from typing import List, Dict, Any


def add_ownership(owner_id: str, company_id: str, properties: Dict[str, Any] = None) -> None:
    """
    Create an OWNS relationship from an owner (Fund or Company) to a target (Fund or Company).
    Supports bidirectional ownership (Fund A can own Fund B, and Fund B can own Fund A).
    Prevents self-ownership (a company/fund cannot own itself).

    owner_id: company_id of the owner (Fund or Company)
    company_id: company_id of the target (Fund or Company)
    properties: Additional properties for the relationship (e.g., share_percentage)
    """
    # Prevent self-ownership
    if owner_id == company_id:
        return

    # Both source and target can be Fund or Company
    # This allows bidirectional ownership between funds

    query = """
    MATCH (owner)
    WHERE owner.company_id = $owner_id AND ('Fund' IN labels(owner) OR 'Company' IN labels(owner))
    MATCH (target)
    WHERE target.company_id = $company_id AND ('Fund' IN labels(target) OR 'Company' IN labels(target))
    MERGE (owner)-[r:OWNS]->(target)
    SET r += $properties, r.updated_at = datetime()
    """

    if properties is None:
        properties = {}

    driver = get_driver()
    with driver.session() as session:
        session.run(query, owner_id=owner_id, company_id=company_id, properties=properties)


def get_company_owners(company_id: str) -> List[Dict[str, Any]]:
    """
    Get all owners (Funds or Companies) of a specific company.
    Returns a list of dictionaries containing owner details and relationship properties.
    """
    query = """
    MATCH (owner)-[r:OWNS]->(target:Company {company_id: $company_id})
    RETURN owner, r, labels(owner) as labels
    """

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, company_id=company_id)
        owners = []
        for record in result:
            owner_data = dict(record["owner"])
            owner_data["_labels"] = record["labels"]
            owner_data["_relationship"] = dict(record["r"])
            owners.append(owner_data)
        return owners


def get_portfolio(owner_id: str) -> List[Dict[str, Any]]:
    """
    Get all entities (Funds or Companies) owned by a specific entity (Fund or Company).
    """
    query = """
    MATCH (owner {company_id: $owner_id})-[r:OWNS]->(target)
    WHERE 'Fund' IN labels(target) OR 'Company' IN labels(target)
    RETURN target, r
    """

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, owner_id=owner_id)
        portfolio = []
        for record in result:
            target_data = dict(record["target"])
            target_data["_relationship"] = dict(record["r"])
            portfolio.append(target_data)
        return portfolio


def get_network_graph(entity_id: str, depth: int = 2) -> Dict[str, Any]:
    """
    Get ownership network graph around an entity up to specified depth.
    Returns nodes and relationships.
    Handles bidirectional ownership (both directions of OWNS relationships).
    The undirected relationship pattern `-[r:OWNS*1..{depth}]-` captures both directions.
    """
    # Neo4j doesn't allow parameters in variable-length patterns, so we format the depth
    # Limit depth to prevent excessive queries
    depth = min(max(1, depth), 5)

    # Undirected relationship pattern captures both (A)-[:OWNS]->(B) and (B)-[:OWNS]->(A)
    query = f"""
    MATCH (root)
    WHERE root.company_id = $entity_id AND (root:Company OR root:Fund)
    MATCH path = (root)-[r:OWNS*1..{depth}]-(connected)
    WHERE (connected:Company OR connected:Fund)
    WITH root, connected, relationships(path) as rels
    RETURN DISTINCT root, connected, rels, labels(root) as root_labels, labels(connected) as connected_labels
    LIMIT 100
    """

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, entity_id=entity_id)
        nodes = {}
        edges = []
        root_node = None

        for record in result:
            root = dict(record["root"])
            connected = dict(record["connected"])
            root_labels = record["root_labels"]
            connected_labels = record["connected_labels"]
            rels = record["rels"]

            root_id = root.get("company_id", "")
            if not root_node and root_id == entity_id:
                root_node = {
                    "id": root_id,
                    "name": root.get("name", "Unknown"),
                    "node_type": "company" if "Company" in root_labels else "fund",
                }
                nodes[root_id] = root_node

            node_id = connected.get("company_id", "")
            if node_id and node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "name": connected.get("name", "Unknown"),
                    "node_type": "company" if "Company" in connected_labels else "fund",
                }

            # Add edges from relationships
            for rel in rels:
                rel_dict = dict(rel)
                edges.append(
                    {
                        "source": root_id,
                        "target": node_id,
                        "rel_type": rel.type,
                        "ownership_pct": rel_dict.get("share_percentage") or rel_dict.get("ownership_pct"),
                    }
                )

        # Ensure root node is included
        if not root_node:
            # Try to get root node separately
            root_query = """
            MATCH (root)
            WHERE root.company_id = $entity_id AND (root:Company OR root:Fund)
            RETURN root, labels(root) as labels
            """
            root_result = session.run(root_query, entity_id=entity_id)
            root_record = root_result.single()
            if root_record:
                root = dict(root_record["root"])
                root_labels = root_record["labels"]
                root_node = {
                    "id": root.get("company_id", entity_id),
                    "name": root.get("name", "Unknown"),
                    "node_type": "company" if "Company" in root_labels else "fund",
                }
                nodes[entity_id] = root_node

        return {"root_id": entity_id, "nodes": list(nodes.values()), "edges": edges, "depth": depth}


def get_all_relationships() -> List[Dict[str, Any]]:
    """
    Get all OWNS relationships between Funds and Companies.
    Returns a list of dictionaries containing source, target, and ownership percentage.
    """
    query = """
    MATCH (s)-[r:OWNS]->(t)
    WHERE (s:Fund OR s:Company) AND (t:Fund OR t:Company)
    RETURN s.company_id as source, t.company_id as target, 
           coalesce(r.share_percentage, r.ownership_pct, 0) as ownership
    """

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query)
        relationships = []
        for record in result:
            relationships.append(
                {"source": record["source"], "target": record["target"], "ownership": record["ownership"]}
            )
        return relationships
