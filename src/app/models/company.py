from pydantic import BaseModel, Field
from typing import Optional


class CompanyBase(BaseModel):
    name: str
    country_code: str = "SE"
    description: Optional[str] = None
    mission: Optional[str] = None
    sectors: list[str] = Field(default_factory=list)


class CompanyCreate(BaseModel):
    """POST /ingest body - minimal input"""
    name: str


class CompanyIngest(CompanyBase):
    """Full entity for ingestion pipeline"""
    company_id: str = Field(..., description="Swedish Org. No.")


class CompanyOut(CompanyBase):
    """GET response"""
    company_id: str
    cluster_id: Optional[int] = None

    class Config:
        from_attributes = True


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
    company_id: str
    cluster_id: int
    leads: list[CompanyOut]
