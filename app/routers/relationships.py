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
from app.db.queries import relationship_queries

router = APIRouter()


@router.post("/", response_model=RelationshipOut, status_code=201)
async def create_relationship(body: RelationshipCreate, api_key: ApiKeyDep):
    """Create ownership/investment relationship."""
    properties = {}
    if body.ownership_pct is not None:
        properties["share_percentage"] = body.ownership_pct
    if body.amount is not None:
        properties["amount"] = body.amount
    
    relationship_queries.add_ownership(
        owner_id=body.source_id,
        company_id=body.target_id,
        properties=properties
    )
    
    return RelationshipOut(
        **body.model_dump(),
        created_at="2024-01-15"  # TODO: Get actual timestamp
    )


@router.get("/network/{entity_id}", response_model=NetworkGraph)
async def get_network(entity_id: str, depth: int = 2, api_key: ApiKeyDep = None):
    """Get ownership network graph around an entity."""
    graph_data = relationship_queries.get_network_graph(entity_id, depth=depth)
    
    # Convert to response model
    nodes = [
        NetworkNode(
            id=node["id"],
            name=node["name"],
            node_type=node["node_type"]
        )
        for node in graph_data["nodes"]
    ]
    
    edges = [
        NetworkEdge(
            source=edge["source"],
            target=edge["target"],
            rel_type=RelationType.INVESTED_IN,  # Default, could map from DB
            ownership_pct=edge.get("ownership_pct")
        )
        for edge in graph_data["edges"]
    ]
    
    return NetworkGraph(
        root_id=graph_data["root_id"],
        nodes=nodes,
        edges=edges,
        depth=graph_data["depth"],
    )
