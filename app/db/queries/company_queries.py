from app.db.neo4j_client import get_driver
from typing import List, Optional, Dict, Any


def upsert_company(company_data: Dict[str, Any]) -> None:
    """
    Upsert a Company node with full metadata.
    """
    query = """
    MERGE (c:Company {company_id: $company_id})
    SET c.name = $name,
        c.country_code = $country_code,
        c.description = $description,
        c.mission = $mission,
        c.sectors = $sectors,
        c.updated_at = datetime(),
        
        // New fields supported by LLM ingestion
        c.website = $website,
        c.num_employees = $num_employees,
        c.year_founded = $year_founded,
        c.aliases = $aliases,
        c.key_people = $key_people

    WITH c
    WHERE $cluster_id IS NOT NULL
    SET c.cluster_id = $cluster_id
    WITH c
    WHERE $vector IS NOT NULL
    SET c.vector = $vector
    WITH c
    SET c.portfolio = COALESCE($portfolio, [])
    """

    # Prepare params with defaults for safety
    params = {
        "company_id": company_data["company_id"],
        "name": company_data["name"],
        "country_code": company_data.get("country_code", "SE"),
        "description": company_data.get("description", ""),
        "mission": company_data.get("mission", ""),
        "sectors": company_data.get("sectors", []),
        "website": company_data.get("website", ""),
        "num_employees": company_data.get("num_employees"),
        "year_founded": str(company_data.get("year_founded") or ""),
        "aliases": company_data.get("aliases", []),
        "key_people": company_data.get("key_people", []),
        "cluster_id": company_data.get("cluster_id"),
        "vector": company_data.get("vector"),
        "portfolio": company_data.get("portfolio"),
    }

    driver = get_driver()
    with driver.session() as session:
        session.run(query, params)


def get_company(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a Company or Fund node by company_id.
    """
    query = """
    MATCH (n)
    WHERE n.company_id = $company_id AND ('Company' IN labels(n) OR 'Fund' IN labels(n))
    RETURN n
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, company_id=company_id)
        record = result.single()
        if record:
            return dict(record["n"])
        return None


def convert_company_to_fund(company_id: str) -> None:
    """
    Convert a Company node to Fund by adding Fund label.
    Keeps Company label so node can be found by both queries.
    """
    query = """
    MATCH (n {company_id: $company_id})
    WHERE 'Company' IN labels(n)
    SET n:Fund
    """
    driver = get_driver()
    with driver.session() as session:
        session.run(query, company_id=company_id)


def search_similar_companies(
    vector: List[float], limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find similar companies using vector search.
    Assumes a vector index exists on :Company(vector).
    """
    # Note: This query assumes a vector index named 'company_vector_index' exists.
    # If using exact KNN or just cosine similarity on all nodes (slow), the query would be different.
    # For production with 100k nodes, a vector index is required.

    query = """
    CALL db.index.vector.queryNodes('company_vector_index', $limit, $vector)
    YIELD node, score
    RETURN node, score
    """

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, vector=vector, limit=limit)
        return [
            {"company": dict(record["node"]), "score": record["score"]}
            for record in result
        ]


def get_companies_by_cluster(cluster_id: int) -> List[Dict[str, Any]]:
    """
    Get all companies in a specific cluster.
    """
    query = """
    MATCH (c:Company {cluster_id: $cluster_id})
    RETURN c
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, cluster_id=cluster_id)
        return [dict(record["c"]) for record in result]
