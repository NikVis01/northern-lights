from fastapi import APIRouter, HTTPException

from app.models import (
    RelationshipCreate,
    RelationshipOut,
    NetworkGraph,
    NetworkNode,
    NetworkEdge,
    RelationType,
)
from app.dependencies import ApiKeyDep

router = APIRouter()


@router.post("/", response_model=RelationshipOut, status_code=201)
async def create_relationship(body: RelationshipCreate, api_key: ApiKeyDep):
    """Create ownership/investment relationship."""
    return RelationshipOut(**body.model_dump(), created_at="2024-01-15")


@router.get("/network/{entity_id}", response_model=NetworkGraph)
async def get_network(entity_id: str, depth: int = 2, api_key: ApiKeyDep = None):
    """Get ownership network graph around an entity."""
    # Mock network for Spotify
    if entity_id == "5591234567":
        return NetworkGraph(
            root_id=entity_id,
            depth=depth,
            nodes=[
                NetworkNode(id="5591234567", name="Spotify AB", node_type="company"),
                NetworkNode(id="INV001", name="Sequoia Capital", node_type="investor"),
                NetworkNode(id="5561234568", name="Klarna Bank AB", node_type="company"),
            ],
            edges=[
                NetworkEdge(
                    source="INV001",
                    target="5591234567",
                    rel_type=RelationType.INVESTED_IN,
                    ownership_pct=5.2,
                ),
                NetworkEdge(
                    source="INV001",
                    target="5561234568",
                    rel_type=RelationType.INVESTED_IN,
                    ownership_pct=3.1,
                ),
            ],
        )

    # Default empty graph
    return NetworkGraph(
        root_id=entity_id,
        depth=depth,
        nodes=[NetworkNode(id=entity_id, name="Unknown", node_type="company")],
        edges=[],
    )
