from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class InvestorType(str, Enum):
    FUND = "fund"
    INDIVIDUAL = "individual"
    INSTITUTION = "institution"


class InvestorBase(BaseModel):
    name: str
    organization_id: str
    investor_type: InvestorType = InvestorType.FUND
    country_code: str = "SE"
    description: Optional[str] = None


class InvestorCreate(BaseModel):
    name: str
    organization_id: str
    investor_type: InvestorType = InvestorType.FUND


class InvestorOut(InvestorBase):
    model_config = {"from_attributes": True}
    investor_id: str
    cluster_id: Optional[int] = None


class InvestorPortfolio(BaseModel):
    """GET /investors/{id}/portfolio"""

    investor_id: str
    name: str
    holdings: list["HoldingOut"]


class HoldingOut(BaseModel):
    company_id: str
    company_name: str
    ownership_pct: Optional[float] = None
    invested_at: Optional[str] = None


InvestorPortfolio.model_rebuild()
