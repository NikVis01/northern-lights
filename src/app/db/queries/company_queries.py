from app.db.neo4j_client import get_driver
from typing import List, Optional, Dict, Any


def upsert_company(company_data: Dict[str, Any]) -> None:
    """
    Upsert a Company node.

    Expected keys in company_data:
    - company_id (str)
    - name (str)
    - country_code (str)
    - description (str)
    - mission (str)
    - sectors (List[str])
    - cluster_id (int, optional)
    - vector (List[float], optional)
    """
    query = """
    MERGE (c:Company {company_id: $company_id})
    SET c.name = $name,
        c.country_code = $country_code,
        c.description = $description,
        c.mission = $mission,
        c.sectors = $sectors,
        c.updated_at = datetime()
    WITH c
    WHERE $cluster_id IS NOT NULL
    SET c.cluster_id = $cluster_id
    WITH c
    WHERE $vector IS NOT NULL
    SET c.vector = $vector
    """

    # Ensure optional fields are present in params or handled
    params = {
        "company_id": company_data["company_id"],
        "name": company_data["name"],
        "country_code": company_data.get("country_code", "SE"),
        "description": company_data.get("description", ""),
        "mission": company_data.get("mission", ""),
        "sectors": company_data.get("sectors", []),
        "cluster_id": company_data.get("cluster_id"),
        "vector": company_data.get("vector"),
    }

    driver = get_driver()
    with driver.session() as session:
        session.run(query, params)


def get_company(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a Company node by company_id.
    """
    query = """
    MATCH (c:Company {company_id: $company_id})
    RETURN c
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, company_id=company_id)
        record = result.single()
        if record:
            return dict(record["c"])
        return None


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
