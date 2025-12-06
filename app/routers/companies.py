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
from app.db.queries import company_queries
from app.services.graph_service import GraphService

router = APIRouter()


def _db_to_company_out(db_data: dict) -> CompanyOut:
    """Convert DB dict to CompanyOut model, mapping company_id -> organization_id"""
    if not db_data:
        return None
    
    # Map company_id to organization_id
    data = db_data.copy()
    if "company_id" in data:
        data["organization_id"] = data.pop("company_id")
    
    # Ensure list fields are lists
    for field in ["aliases", "sectors", "portfolio", "shareholders", "customers", "key_people"]:
        if field not in data or data[field] is None:
            data[field] = []
    
    # Extract cluster_id if present
    cluster_id = data.pop("cluster_id", None)
    
    try:
        company = CompanyOut(**data, cluster_id=cluster_id)
        return company
    except Exception as e:
        raise ValueError(f"Failed to convert DB data to CompanyOut: {e}")


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
    db_data = company_queries.get_company(organization_id)
    if not db_data:
        raise HTTPException(404, f"Company {organization_id} not found")
    
    return _db_to_company_out(db_data)


@router.post("/search", response_model=list[CompanySearchResult])
async def search_companies(body: CompanySearch, api_key: ApiKeyDep):
    """Vector similarity search on company descriptions."""
    # Generate vector from query text
    graph_service = GraphService()
    query_vector = graph_service.model.encode(body.query).tolist()
    
    # Search similar companies
    results = company_queries.search_similar_companies(query_vector, limit=body.limit)
    
    # Convert to response model
    search_results = []
    for result in results:
        company_data = result["company"]
        score = result["score"]
        
        # Filter by sectors if specified
        if body.sectors:
            company_sectors = company_data.get("sectors", [])
            if not any(s in company_sectors for s in body.sectors):
                continue
        
        company_out = _db_to_company_out(company_data)
        if company_out:
            search_results.append(CompanySearchResult(**company_out.model_dump(), score=float(score)))
    
    return search_results[:body.limit]


@router.get("/{organization_id}/leads", response_model=CompanyLeads)
async def get_leads(organization_id: str, api_key: ApiKeyDep):
    """Get companies in same Leiden cluster (competitive leads)."""
    # Get company to find its cluster_id
    db_data = company_queries.get_company(organization_id)
    if not db_data:
        raise HTTPException(404, f"Company {organization_id} not found")
    
    cluster_id = db_data.get("cluster_id")
    if not cluster_id:
        return CompanyLeads(
            organization_id=organization_id,
            cluster_id=0,
            leads=[],
        )
    
    # Get all companies in same cluster
    cluster_companies = company_queries.get_companies_by_cluster(cluster_id)
    
    # Convert to CompanyOut and exclude the original company
    leads = []
    for company_data in cluster_companies:
        if company_data.get("company_id") == organization_id:
            continue
        company_out = _db_to_company_out(company_data)
        if company_out:
            leads.append(company_out)
    
    return CompanyLeads(
        organization_id=organization_id,
        cluster_id=cluster_id,
        leads=leads,
    )
