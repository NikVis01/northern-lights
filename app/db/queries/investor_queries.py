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
    
    Validates that company_id is a valid Swedish organization number before upserting.
    """
    company_id = investor_data.get("company_id", "")
    
    # Validate organization number format (10 digits)
    import re
    cleaned = re.sub(r'[-\s]', '', str(company_id))
    if not (len(cleaned) == 10 and cleaned.isdigit()):
        raise ValueError(f"Invalid organization number format: '{company_id}'. Must be 10 digits (format: XXXXXX-XXXX)")
    
    query = """
    MERGE (f:Fund {company_id: $company_id})
    REMOVE f:Company
    SET f.name = $name,
        f.country_code = $country_code,
        f.description = COALESCE($description, f.description, ""),
        f.sectors = COALESCE($sectors, f.sectors, []),
        f.mission = COALESCE($mission, f.mission, ""),
        f.website = COALESCE($website, f.website, ""),
        f.num_employees = COALESCE($num_employees, f.num_employees),
        f.year_founded = COALESCE($year_founded, f.year_founded, ""),
        f.aliases = COALESCE($aliases, f.aliases, []),
        f.key_people = COALESCE($key_people, f.key_people, []),
        f.updated_at = datetime(),
        f.investment_thesis = COALESCE($investment_thesis, f.investment_thesis, "")
    WITH f
    WHERE $vector IS NOT NULL
    SET f.vector = $vector
    WITH f
    SET f.portfolio = COALESCE($portfolio, f.portfolio, [])
    """

    params = {
        "company_id": investor_data["company_id"],
        "name": investor_data["name"],
        "country_code": investor_data.get("country_code", "SE"),
        "description": investor_data.get("description"),
        "sectors": investor_data.get("sectors"),
        "mission": investor_data.get("mission"),
        "website": investor_data.get("website"),
        "num_employees": investor_data.get("num_employees"),
        "year_founded": investor_data.get("year_founded"),
        "aliases": investor_data.get("aliases"),
        "key_people": investor_data.get("key_people"),
        "vector": investor_data.get("vector"),
        "portfolio": investor_data.get("portfolio"),
        "investment_thesis": investor_data.get("investment_thesis"),
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
    Converts a Company node to Fund by removing Company label and adding Fund label.
    """
    query = """
    MATCH (c)
    WHERE c.company_id = $company_id AND 'Company' IN labels(c)
    REMOVE c:Company
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


def get_all_investors() -> List[Dict[str, Any]]:
    """
    Retrieve all Fund nodes.
    """
    query = """
    MATCH (f:Fund)
    RETURN f
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query)
        return [dict(record["f"]) for record in result]


def get_all_companies() -> List[Dict[str, Any]]:
    """
    Retrieve all Company nodes.
    """
    query = """
    MATCH (c:Company)
    RETURN c
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query)
        return [dict(record["c"]) for record in result]
