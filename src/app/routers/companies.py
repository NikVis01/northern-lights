from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4

from src.app.models import (
    CompanyCreate,
    CompanyOut,
    CompanySearch,
    CompanySearchResult,
    CompanyLeads,
)
from src.app.dependencies import SettingsDep, ApiKeyDep

router = APIRouter()

# Mock data for testing
MOCK_COMPANIES = {
    "5591234567": CompanyOut(
        organization_id="5591234567",
        name="Spotify AB",
        aliases=["Spotify"],
        year_founded="2006",
        sectors=["Technology", "Entertainment"],
        description="Music streaming platform",
        num_employees=8000,
        mission="Unlock the potential of human creativity",
        key_people=["Daniel Ek", "Martin Lorentzon"],
        website="https://spotify.com",
        cluster_id=1,
    ),
    "5561234568": CompanyOut(
        organization_id="5561234568",
        name="Klarna Bank AB",
        aliases=["Klarna"],
        year_founded="2005",
        sectors=["Fintech", "Banking"],
        description="Buy now pay later fintech",
        num_employees=5000,
        mission="Make paying smoother",
        key_people=["Sebastian Siemiatkowski"],
        website="https://klarna.com",
        cluster_id=2,
    ),
    "5569876543": CompanyOut(
        organization_id="5569876543",
        name="Northvolt AB",
        aliases=["Northvolt"],
        year_founded="2016",
        sectors=["CleanTech", "Manufacturing"],
        description="Battery manufacturing",
        num_employees=3000,
        mission="Build the greenest battery in the world",
        key_people=["Peter Carlsson"],
        website="https://northvolt.com",
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


@router.get("/{organization_id}", response_model=CompanyOut)
async def get_company(organization_id: str, api_key: ApiKeyDep):
    """Get company by Swedish Org. No."""
    if organization_id not in MOCK_COMPANIES:
        raise HTTPException(404, f"Company {organization_id} not found")
    return MOCK_COMPANIES[organization_id]


@router.post("/search", response_model=list[CompanySearchResult])
async def search_companies(body: CompanySearch, api_key: ApiKeyDep):
    """Vector similarity search on company descriptions."""
    # Mock: return all companies with fake scores
    results = []
    for c in MOCK_COMPANIES.values():
        if body.sectors and not any(s in c.sectors for s in body.sectors):
            continue
        results.append(CompanySearchResult(**c.model_dump(), score=0.85))
    return results[: body.limit]


@router.get("/{organization_id}/leads", response_model=CompanyLeads)
async def get_leads(organization_id: str, api_key: ApiKeyDep):
    """Get companies in same Leiden cluster (competitive leads)."""
    if organization_id not in MOCK_COMPANIES:
        raise HTTPException(404, f"Company {organization_id} not found")

    company = MOCK_COMPANIES[organization_id]
    # Mock: return companies with same cluster_id
    leads = [
        c
        for c in MOCK_COMPANIES.values()
        if c.cluster_id == company.cluster_id and c.organization_id != organization_id
    ]
    return CompanyLeads(
        organization_id=organization_id,
        cluster_id=company.cluster_id or 0,
        leads=leads,
    )
