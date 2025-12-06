from fastapi import APIRouter, HTTPException

from app.models import InvestorOut, InvestorCreate, InvestorPortfolio, HoldingOut, InvestorType
from app.dependencies import ApiKeyDep
from app.db.queries import investor_queries, relationship_queries

router = APIRouter()


def _db_to_investor_out(db_data: dict, investor_id: str = None) -> InvestorOut:
    """Convert DB dict to InvestorOut model"""
    if not db_data:
        return None
    
    data = db_data.copy()
    # Map company_id to organization_id
    if "company_id" in data:
        data["organization_id"] = data.pop("company_id")
    
    # Use provided investor_id or generate from organization_id
    if not investor_id:
        investor_id = data.get("organization_id", "UNKNOWN")
    
    # Extract cluster_id
    cluster_id = data.pop("cluster_id", None)
    
    # Ensure list fields
    if "sectors" not in data or data["sectors"] is None:
        data["sectors"] = []
    
    try:
        investor = InvestorOut(
            investor_id=investor_id,
            cluster_id=cluster_id,
            **{k: v for k, v in data.items() if k in InvestorOut.model_fields}
        )
        return investor
    except Exception as e:
        raise ValueError(f"Failed to convert DB data to InvestorOut: {e}")


@router.get("/{investor_id}", response_model=InvestorOut)
async def get_investor(investor_id: str, api_key: ApiKeyDep):
    """Get investor by ID (uses organization_id/company_id in DB)"""
    # In DB, investors are stored with company_id = organization_id
    db_data = investor_queries.get_investor(investor_id)
    if not db_data:
        raise HTTPException(404, f"Investor {investor_id} not found")
    
    return _db_to_investor_out(db_data, investor_id=investor_id)


@router.get("/{investor_id}/portfolio", response_model=InvestorPortfolio)
async def get_portfolio(investor_id: str, api_key: ApiKeyDep):
    """Get investor's portfolio holdings."""
    # Check investor exists
    investor_data = investor_queries.get_investor(investor_id)
    if not investor_data:
        raise HTTPException(404, f"Investor {investor_id} not found")
    
    # Get portfolio from relationships
    portfolio_data = relationship_queries.get_portfolio(investor_id)
    
    # Convert to HoldingOut
    holdings = []
    for item in portfolio_data:
        company_data = item if "_relationship" not in item else {k: v for k, v in item.items() if k != "_relationship"}
        rel_data = item.get("_relationship", {})
        
        holdings.append(HoldingOut(
            company_id=company_data.get("company_id", ""),
            company_name=company_data.get("name", "Unknown"),
            ownership_pct=rel_data.get("share_percentage") or rel_data.get("ownership_pct"),
            invested_at=rel_data.get("created_at") or rel_data.get("invested_at"),
        ))
    
    return InvestorPortfolio(
        investor_id=investor_id,
        name=investor_data.get("name", "Unknown"),
        holdings=holdings,
    )


@router.post("/", response_model=InvestorOut, status_code=201)
async def create_investor(body: InvestorCreate, api_key: ApiKeyDep):
    """Create a new investor."""
    # Use organization_id as investor_id for now
    investor_id = body.organization_id
    
    # Upsert to DB
    investor_data = {
        "company_id": body.organization_id,
        "name": body.name,
        "investor_type": body.investor_type.value,
        "country_code": "SE",
    }
    investor_queries.upsert_investor(investor_data)
    
    # Fetch back to return
    db_data = investor_queries.get_investor(body.organization_id)
    return _db_to_investor_out(db_data, investor_id=investor_id)
