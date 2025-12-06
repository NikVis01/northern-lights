from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class EntityRef(BaseModel):
    """Reference to another company/fund"""

    entity_id: str
    name: str
    entity_type: str = "company"  # company | fund


class CompanyBase(BaseModel):
    name: str
    organization_id: str
    aliases: list[str] = Field(default_factory=list)
    year_founded: Optional[str] = None
    sectors: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    num_employees: Optional[int] = None
    num_shares: Optional[int] = None
    mission: Optional[str] = None
    portfolio: list[EntityRef] = Field(default_factory=list)
    shareholders: list[EntityRef] = Field(default_factory=list)
    customers: list[EntityRef] = Field(default_factory=list)
    key_people: list[str] = Field(default_factory=list)
    website: Optional[str] = None
    country_code: str = "SE"


class CompanyCreate(BaseModel):
    """POST /ingest body - minimal input"""

    name: str
    organization_id: str


class CompanyIngest(CompanyBase):
    """Full entity for ingestion pipeline"""
    pass


class CompanyOut(CompanyBase):
    """GET response"""

    model_config = {"from_attributes": True}
    cluster_id: Optional[int] = None


class CompanySearch(BaseModel):
    """POST /search body"""

    query: str
    limit: int = Field(default=10, le=50)
    sectors: Optional[list[str]] = None


class CompanySearchResult(CompanyOut):
    """Search result with similarity score"""

    score: float


class CompanyLeads(BaseModel):
    """GET /leads response"""

    organization_id: str
    cluster_id: int
    leads: list[CompanyOut]
