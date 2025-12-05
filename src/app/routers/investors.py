from fastapi import APIRouter, HTTPException

from app.models import InvestorOut, InvestorCreate, InvestorPortfolio, HoldingOut, InvestorType
from app.dependencies import ApiKeyDep

router = APIRouter()

# Mock data
MOCK_INVESTORS = {
    "INV001": InvestorOut(
        investor_id="INV001",
        organization_id="5561111111",
        name="Sequoia Capital",
        investor_type=InvestorType.FUND,
        country_code="SE",
        description="Global VC fund",
        cluster_id=1,
    ),
    "INV002": InvestorOut(
        investor_id="INV002",
        organization_id="5562222222",
        name="EQT Partners",
        investor_type=InvestorType.FUND,
        country_code="SE",
        description="Nordic private equity",
        cluster_id=2,
    ),
}

MOCK_HOLDINGS = {
    "INV001": [
        HoldingOut(company_id="5591234567", company_name="Spotify AB", ownership_pct=5.2),
        HoldingOut(company_id="5561234568", company_name="Klarna Bank AB", ownership_pct=3.1),
    ],
    "INV002": [
        HoldingOut(company_id="5569876543", company_name="Northvolt AB", ownership_pct=12.5),
    ],
}


@router.get("/{investor_id}", response_model=InvestorOut)
async def get_investor(investor_id: str, api_key: ApiKeyDep):
    if investor_id not in MOCK_INVESTORS:
        raise HTTPException(404, f"Investor {investor_id} not found")
    return MOCK_INVESTORS[investor_id]


@router.get("/{investor_id}/portfolio", response_model=InvestorPortfolio)
async def get_portfolio(investor_id: str, api_key: ApiKeyDep):
    """Get investor's portfolio holdings."""
    if investor_id not in MOCK_INVESTORS:
        raise HTTPException(404, f"Investor {investor_id} not found")
    
    investor = MOCK_INVESTORS[investor_id]
    holdings = MOCK_HOLDINGS.get(investor_id, [])
    return InvestorPortfolio(
        investor_id=investor_id,
        name=investor.name,
        holdings=holdings,
    )


@router.post("/", response_model=InvestorOut, status_code=201)
async def create_investor(body: InvestorCreate, api_key: ApiKeyDep):
    """Create a new investor."""
    investor_id = f"INV{len(MOCK_INVESTORS) + 1:03d}"
    investor = InvestorOut(
        investor_id=investor_id,
        organization_id=body.organization_id,
        name=body.name,
        investor_type=body.investor_type,
        country_code="SE",
    )
    MOCK_INVESTORS[investor_id] = investor
    return investor
