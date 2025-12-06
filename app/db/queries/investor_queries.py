from app.db.neo4j_client import get_driver
from typing import List, Optional, Dict, Any


def upsert_investor(investor_data: Dict[str, Any]) -> None:
    """
    Upsert a Fund (Investor) node.

    Expected keys in investor_data:
    - company_id (str) - Org No or unique ID
    - name (str)
    - country_code (str)
    - description (str)
    - sectors (List[str])
    - vector (List[float], optional)
    - investment_thesis (str, optional)
    """
    query = """
    MERGE (f:Fund {company_id: $company_id})
    SET f.name = $name,
        f.country_code = $country_code,
        f.description = $description,
        f.sectors = $sectors,
        f.updated_at = datetime(),
        f.investment_thesis = $investment_thesis
    WITH f
    WHERE $vector IS NOT NULL
    SET f.vector = $vector
    WITH f
    SET f.portfolio = COALESCE($portfolio, [])
    """

    params = {
        "company_id": investor_data["company_id"],
        "name": investor_data["name"],
        "country_code": investor_data.get("country_code", "SE"),
        "description": investor_data.get("description", ""),
        "sectors": investor_data.get("sectors", []),
        "vector": investor_data.get("vector"),
        "portfolio": investor_data.get("portfolio"),
        "investment_thesis": investor_data.get("investment_thesis", ""),
    }

    driver = get_driver()
    with driver.session() as session:
        session.run(query, params)


def get_investor(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a Fund node by company_id.
    """
    query = """
    MATCH (f:Fund {company_id: $company_id})
    RETURN f
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, company_id=company_id)
        record = result.single()
        if record:
            return dict(record["f"])
        return None


def convert_company_to_fund(company_id: str) -> None:
    """
    Adds the 'Fund' label to an existing Company node.
    """
    query = """
    MATCH (c)
    WHERE c.company_id = $company_id
    SET c:Fund
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(query, company_id=company_id)


def find_investors_by_sector(sector: str) -> List[Dict[str, Any]]:
    """
    Find investors interested in a specific sector.
    """
    query = """
    MATCH (f:Fund)
    WHERE $sector IN f.sectors
    RETURN f
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, sector=sector)
        return [dict(record["f"]) for record in result]
