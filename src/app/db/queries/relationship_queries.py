from app.db.neo4j_client import get_driver
from typing import List, Dict, Any


def add_ownership(
    owner_id: str, company_id: str, properties: Dict[str, Any] = None
) -> None:
    """
    Create an OWNS relationship from an owner (Fund or Company) to a Company.

    owner_id: company_id of the owner (Fund or Company)
    company_id: company_id of the target Company
    properties: Additional properties for the relationship (e.g., share_percentage)
    """
    # Try to match owner as Fund first, then Company if not found?
    # Or just match node with company_id regardless of label?
    # Spec says company_id is unique identifier.
    # Let's assume we match on company_id for both source and target.
    # Source can be :Fund or :Company. Target is :Company.

    query = """
    MATCH (owner {company_id: $owner_id})
    WHERE 'Fund' IN labels(owner) OR 'Company' IN labels(owner)
    MATCH (target:Company {company_id: $company_id})
    MERGE (owner)-[r:OWNS]->(target)
    SET r += $properties, r.updated_at = datetime()
    """

    if properties is None:
        properties = {}

    driver = get_driver()
    with driver.session() as session:
        session.run(
            query, owner_id=owner_id, company_id=company_id, properties=properties
        )


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
    Get all companies owned by a specific entity (Fund or Company).
    """
    query = """
    MATCH (owner {company_id: $owner_id})-[r:OWNS]->(target:Company)
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
