from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RelationType(str, Enum):
    OWNS = "OWNS"
    INVESTED_IN = "INVESTED_IN"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"


class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    rel_type: RelationType
    ownership_pct: Optional[float] = Field(None, ge=0, le=100)
    amount: Optional[float] = None  # Investment amount in SEK


class RelationshipOut(RelationshipCreate):
    model_config = {"from_attributes": True}
    created_at: Optional[str] = None


class NetworkNode(BaseModel):
    """Node in ownership graph"""
    id: str
    name: str
    node_type: str  # "company" | "investor"


class NetworkEdge(BaseModel):
    """Edge in ownership graph"""
    source: str
    target: str
    rel_type: RelationType
    ownership_pct: Optional[float] = None


class NetworkGraph(BaseModel):
    """GET /companies/{id}/network response"""
    root_id: str
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    depth: int
