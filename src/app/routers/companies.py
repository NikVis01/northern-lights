from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4

from app.models import (
    CompanyCreate,
    CompanyOut,
    CompanySearch,
    CompanySearchResult,
    CompanyLeads,
)
from app.dependencies import SettingsDep, ApiKeyDep

router = APIRouter()

# Mock data for testing
MOCK_COMPANIES = {
    "5591234567": CompanyOut(
        company_id="5591234567",
        name="Spotify AB",
        country_code="SE",
        description="Music streaming platform",
        mission="Unlock the potential of human creativity",
        sectors=["Technology", "Entertainment"],
        cluster_id=1,
    ),
    "5561234568": CompanyOut(
        company_id="5561234568",
        name="Klarna Bank AB",
        country_code="SE",
        description="Buy now pay later fintech",
        mission="Make paying smoother",
        sectors=["Fintech", "Banking"],
        cluster_id=2,
    ),
    "5569876543": CompanyOut(
        company_id="5569876543",
        name="Northvolt AB",
        country_code="SE",
        description="Battery manufacturing",
        mission="Build the greenest battery in the world",
        sectors=["CleanTech", "Manufacturing"],
        cluster_id=1,
    ),
}


@router.post("/ingest", status_code=202)
async def ingest_company(
    body: CompanyCreate,
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    api_key: ApiKeyDep,
):
    """Trigger async ingestion pipeline. Returns job_id immediately."""
    job_id = str(uuid4())
    # TODO: Push to Pub/Sub
    return {"job_id": job_id, "status": "queued", "name": body.name}


@router.get("/{company_id}", response_model=CompanyOut)
async def get_company(company_id: str, api_key: ApiKeyDep):
    """Get company by Swedish Org. No."""
    if company_id not in MOCK_COMPANIES:
        raise HTTPException(404, f"Company {company_id} not found")
    return MOCK_COMPANIES[company_id]


@router.post("/search", response_model=list[CompanySearchResult])
async def search_companies(body: CompanySearch, api_key: ApiKeyDep):
    """Vector similarity search on company descriptions."""
    # Mock: return all companies with fake scores
    results = []
    for c in MOCK_COMPANIES.values():
        if body.sectors and not any(s in c.sectors for s in body.sectors):
            continue
        results.append(
            CompanySearchResult(**c.model_dump(), score=0.85)
        )
    return results[:body.limit]


@router.get("/{company_id}/leads", response_model=CompanyLeads)
async def get_leads(company_id: str, api_key: ApiKeyDep):
    """Get companies in same Leiden cluster (competitive leads)."""
    if company_id not in MOCK_COMPANIES:
        raise HTTPException(404, f"Company {company_id} not found")
    
    company = MOCK_COMPANIES[company_id]
    # Mock: return companies with same cluster_id
    leads = [
        c for c in MOCK_COMPANIES.values()
        if c.cluster_id == company.cluster_id and c.company_id != company_id
    ]
    return CompanyLeads(
        company_id=company_id,
        cluster_id=company.cluster_id or 0,
        leads=leads,
    )
