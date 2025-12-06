from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import ApiKeyDep

from app.db.queries import investor_queries, relationship_queries


router = APIRouter()


class UnifiedSearchQuery(BaseModel):
    query: str
    entity_types: list[str] = ["company", "investor"]
    limit: int = 20


class UnifiedSearchResult(BaseModel):
    id: str
    name: str
    entity_type: str
    score: float
    snippet: str | None = None


@router.post("/", response_model=list[UnifiedSearchResult])
async def unified_search(body: UnifiedSearchQuery, api_key: ApiKeyDep):
    """Unified vector search across companies and investors."""
    # Mock results
    results = []

    if "company" in body.entity_types:
        results.extend(
            [
                UnifiedSearchResult(
                    id="5591234567",
                    name="Spotify AB",
                    entity_type="company",
                    score=0.92,
                    snippet="Music streaming platform...",
                ),
                UnifiedSearchResult(
                    id="5569876543",
                    name="Northvolt AB",
                    entity_type="company",
                    score=0.78,
                    snippet="Battery manufacturing...",
                ),
            ]
        )

    if "investor" in body.entity_types:
        results.append(
            UnifiedSearchResult(
                id="INV001",
                name="Sequoia Capital",
                entity_type="investor",
                score=0.65,
                snippet="Global VC fund...",
            )
        )

    return sorted(results, key=lambda x: x.score, reverse=True)[: body.limit]


# Get all companies and investors for the frontend graph functionality
@router.get("/all")
async def get_all_entities(api_key: ApiKeyDep):
    """Get all companies and investors for the frontend graph functionality."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Fetch nodes
        companies = investor_queries.get_all_companies()
        investors = investor_queries.get_all_investors()

        nodes = []

        # Process companies
        for c in companies:
            try:
                nodes.append(
                    {
                        "id": c["company_id"],
                        "name": c.get("name", "Unknown Company"),
                        "type": "company",
                        "orgNumber": c.get("company_id", ""),
                        "sector": c.get("sectors", ["Unknown"])[0] if c.get("sectors") else "Unknown",
                        "country": c.get("country_code", "SE"),
                        "cluster": 1,
                        "val": 10,
                        "website": c.get("website"),
                    }
                )
            except Exception as e:
                logger.error(f"Error processing company {c}: {e}")
                continue

        # Process investors
        for inv in investors:
            try:
                nodes.append(
                    {
                        "id": inv["company_id"],
                        "name": inv.get("name", "Unknown Investor"),
                        "type": "fund",
                        "orgNumber": inv.get("company_id", ""),
                        "sector": inv.get("sectors", ["Unknown"])[0] if inv.get("sectors") else "Unknown",
                        "country": inv.get("country_code", "SE"),
                        "cluster": 1,
                        "val": 15,
                        "website": inv.get("website"),
                    }
                )
            except Exception as e:
                logger.error(f"Error processing investor {inv}: {e}")
                continue

        # 2. Fetch edges
        rels = relationship_queries.get_all_relationships()

        links = []
        for r in rels:
            try:
                links.append({"source": r["source"], "target": r["target"], "ownership": r["ownership"]})
            except Exception as e:
                logger.error(f"Error processing relationship {r}: {e}")
                continue

        logger.info(f"Returning {len(nodes)} nodes and {len(links)} links")
        return {"nodes": nodes, "links": links}
    
    except Exception as e:
        logger.error(f"Error in get_all_entities: {e}", exc_info=True)
        # Re-raise the exception to return proper HTTP error response
        raise
