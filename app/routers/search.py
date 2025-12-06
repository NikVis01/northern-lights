from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import ApiKeyDep

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
