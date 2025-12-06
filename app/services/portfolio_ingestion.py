"""
Portfolio ingestion service that integrates hack_net.py for FI document extraction.
Recursively processes portfolio companies and creates OWNS relationships.
"""
import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

# Add hack_net.py to path
HACK_NET_PATH = Path(__file__).parent.parent.parent / "data_pipeline" / "illegal"

from app.db.queries import company_queries, relationship_queries, investor_queries
from app.models import EntityRef

logger = logging.getLogger(__name__)

# Try to import Tavily for web search
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    if TAVILY_API_KEY:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    else:
        tavily_client = None
        logger.warning("TAVILY_API_KEY not set - org number lookup will be limited")
except ImportError:
    TAVILY_AVAILABLE = False
    tavily_client = None

# Try to import Gemini for org number extraction
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        try:
            gemini_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        except:
            gemini_model = genai.GenerativeModel("gemini-1.5-pro")
    else:
        gemini_model = None
        logger.warning("GEMINI_API_KEY not set - org number extraction will be limited")
except ImportError:
    gemini_model = None


def is_valid_org_number(org_id: str) -> bool:
    """
    Check if string is a valid Swedish organization number format.
    Format: 10 digits, optionally with dash (e.g., "556043-4200" or "5560434200")
    """
    import re
    # Remove dashes and spaces
    cleaned = re.sub(r'[-\s]', '', org_id)
    # Check if it's exactly 10 digits
    return len(cleaned) == 10 and cleaned.isdigit()


def extract_portfolio_from_fi(organization_id: str) -> List[Dict[str, Any]]:
    """
    Call hack_net.py to extract portfolio companies from FI documents.
    Returns list of {company_name, ownership_percentage}.
    
    Only works with valid Swedish organization numbers (10 digits).
    """
    # Validate organization number format
    if not is_valid_org_number(organization_id):
        logger.warning(f"Skipping FI search for '{organization_id}' - not a valid org number format")
        return []
    
    try:
        # Import hack_net module using sys.path manipulation (cleaner than importlib)
        import sys
        import os
        
        # Add parent directory to path if not already there
        hack_net_dir = str(HACK_NET_PATH)
        if hack_net_dir not in sys.path:
            sys.path.insert(0, hack_net_dir)
        
        # Import the module
        import hack_net
        
        logger.info(f"Searching FI documents for organization {organization_id}")
        # Search for documents
        links = hack_net.search_fi_documents(organization_id)
        if not links:
            logger.warning(f"No FI documents found for {organization_id}")
            return []
        
        logger.info(f"Found {len(links)} document(s), processing first document...")
        # Process first (latest) document
        portfolio = hack_net.process_document(links[0], organization_id)
        logger.info(f"Extracted {len(portfolio)} portfolio company/ies")
        return portfolio
    except ImportError as e:
        logger.error(f"Missing dependencies for hack_net (playwright, etc.): {e}")
        raise  # Re-raise to make it visible
    except Exception as e:
        logger.error(f"Error extracting portfolio from FI for {organization_id}: {e}", exc_info=True)
        raise  # Re-raise to make errors visible instead of silently failing


def lookup_org_number_from_web(company_name: str) -> Optional[str]:
    """
    Search web for company name + "organisationsnummer" and use Gemini to extract org number.
    Returns organization number if found, None otherwise.
    """
    if not tavily_client or not gemini_model:
        logger.debug(f"Tavily or Gemini not available, skipping web lookup for {company_name}")
        return None
    
    try:
        # Search web for company name + organisationsnummer
        search_query = f"{company_name} organisationsnummer"
        logger.info(f"Searching web for: {search_query}")
        
        response = tavily_client.search(
            query=search_query,
            search_depth="basic",
            max_results=5
        )
        
        # Aggregate search results
        search_context = []
        for result in response.get("results", []):
            search_context.append(f"Source: {result.get('url', '')}\nContent: {result.get('content', '')}")
        
        if not search_context:
            logger.warning(f"No web search results for {company_name}")
            return None
        
        # Use Gemini to extract org number
        prompt = f"""You are analyzing web search results to find the Swedish organization number (organisationsnummer) for a company.

Company name: {company_name}

Search results:
{chr(10).join(search_context[:3])}

Extract the Swedish organization number (10 digits, format: XXXXXX-XXXX or XXXXXXXXXX) for this company.
If found, return ONLY the organization number (10 digits with or without dash).
If not found, return "NOT_FOUND".

Organization number:"""
        
        gemini_response = gemini_model.generate_content(prompt)
        org_number = gemini_response.text.strip()
        
        # Clean up response
        if "NOT_FOUND" in org_number.upper() or len(org_number) < 10:
            return None
        
        # Extract just the digits
        import re
        digits = re.sub(r'[^\d]', '', org_number)
        if len(digits) == 10:
            # Format as XXXXXX-XXXX
            formatted = f"{digits[:6]}-{digits[6:]}"
            logger.info(f"Found org number for {company_name}: {formatted}")
            return formatted
        
        return None
    except Exception as e:
        logger.error(f"Error looking up org number for {company_name}: {e}")
        return None


def lookup_or_create_company(company_name: str) -> str:
    """
    Look up company by name in Neo4j, or create with real org number if found via web search.
    Returns organization_id (company_id in DB).
    """
    # First, try to find real org number via web search
    org_number = lookup_org_number_from_web(company_name)
    
    if org_number and is_valid_org_number(org_number):
        # Use real org number
        org_id = org_number
        logger.info(f"Using real org number {org_id} for {company_name}")
    else:
        # Fallback to placeholder
        org_id = company_name.replace(" ", "").replace("AB", "").upper()[:10]
        logger.warning(f"Using placeholder ID {org_id} for {company_name} (no org number found)")
    
    # Try to get existing company
    existing = company_queries.get_company(org_id)
    if existing:
        return existing.get("company_id", org_id)
    
    # Create company node
    company_queries.upsert_company({
        "company_id": org_id,
        "name": company_name,
        "country_code": "SE",
        "description": "",
        "mission": "",
        "sectors": [],
    })
    
    return org_id


def process_portfolio_companies(
    source_org_id: str,
    portfolio_data: List[Dict[str, Any]],
    visited: Set[str] = None
) -> List[EntityRef]:
    """
    Process portfolio companies from hack_net output.
    Creates/updates company nodes and OWNS relationships.
    
    Args:
        source_org_id: Organization ID of the company owning the portfolio
        portfolio_data: List from hack_net.py [{company_name, ownership_percentage}]
        visited: Set of org_ids already processed (for recursion prevention)
    
    Returns:
        List of EntityRef objects for the portfolio field
    """
    if visited is None:
        visited = set()
    
    if source_org_id in visited:
        return []
    
    visited.add(source_org_id)
    
    entity_refs = []
    
    for item in portfolio_data:
        company_name = item.get("company_name", "").strip()
        ownership_pct = item.get("ownership_percentage")
        
        if not company_name:
            continue
        
        # Look up or create company
        target_org_id = lookup_or_create_company(company_name)
        
        # Skip self-ownership
        if source_org_id == target_org_id:
            logger.warning(f"Skipping self-ownership: {company_name} ({target_org_id})")
            continue
        
        # Create OWNS relationship with ownership percentage
        properties = {}
        if ownership_pct is not None:
            properties["share_percentage"] = float(ownership_pct)
        
        relationship_queries.add_ownership(
            owner_id=source_org_id,
            company_id=target_org_id,
            properties=properties
        )
        
        # Create EntityRef
        entity_refs.append(EntityRef(
            entity_id=target_org_id,
            name=company_name,
            entity_type="company",
            ownership_pct=ownership_pct
        ))
        
        # Recursively process this portfolio company
        if target_org_id not in visited:
            portfolio_data_recursive = extract_portfolio_from_fi(target_org_id)
            if portfolio_data_recursive:
                # Process the recursive portfolio
                recursive_entities = process_portfolio_companies(
                    target_org_id,
                    portfolio_data_recursive,
                    visited
                )
                
                # If this company has a portfolio (found in FI docs), convert it to Fund
                # Use portfolio_data_recursive check, not recursive_entities, because
                # recursive_entities might be empty if all items were already visited
                logger.info(f"Company {target_org_id} has portfolio - converting to Fund")
                company_queries.convert_company_to_fund(target_org_id)
                # Update as Fund with portfolio data, preserving all existing fields
                portfolio_data_for_storage = [
                    {
                        "entity_id": e.entity_id,
                        "name": e.name,
                        "entity_type": e.entity_type,
                        "ownership_pct": e.ownership_pct
                    }
                    for e in recursive_entities
                ]
                target_company = company_queries.get_company(target_org_id)
                if target_company:
                    investor_queries.upsert_investor({
                        "company_id": target_org_id,
                        "name": target_company.get("name", company_name),
                        "country_code": target_company.get("country_code", "SE"),
                        "description": target_company.get("description"),
                        "sectors": target_company.get("sectors"),
                        "mission": target_company.get("mission"),
                        "website": target_company.get("website"),
                        "num_employees": target_company.get("num_employees"),
                        "year_founded": target_company.get("year_founded"),
                        "aliases": target_company.get("aliases"),
                        "key_people": target_company.get("key_people"),
                        "portfolio": portfolio_data_for_storage,
                    })
    
    return entity_refs


def ingest_company_with_portfolio(organization_id: str, name: str) -> Dict[str, Any]:
    """
    Main ingestion function: extracts portfolio from FI and recursively processes.
    
    Returns:
        Dict with portfolio EntityRefs and processing stats
    """
    # Ensure source company exists
    existing = company_queries.get_company(organization_id)
    if not existing:
        company_queries.upsert_company({
            "company_id": organization_id,
            "name": name,
            "country_code": "SE",
            "description": "",
            "mission": "",
            "sectors": [],
        })
    
    # Extract portfolio from FI documents
    logger.info(f"Starting portfolio extraction for {organization_id} ({name})")
    portfolio_data = extract_portfolio_from_fi(organization_id)
    
    if not portfolio_data:
        logger.warning(f"No portfolio data extracted for {organization_id}")
        return {
            "organization_id": organization_id,
            "portfolio": [],
            "companies_processed": 0
        }
    
    logger.info(f"Processing {len(portfolio_data)} portfolio companies...")
    
    # Process portfolio companies (recursive)
    visited = set()
    portfolio_entities = process_portfolio_companies(
        organization_id,
        portfolio_data,
        visited
    )
    
    # Update company's portfolio field in Neo4j
    # Convert EntityRef to dict for storage
    portfolio_data_for_storage = [
        {
            "entity_id": e.entity_id,
            "name": e.name,
            "entity_type": e.entity_type,
            "ownership_pct": e.ownership_pct
        }
        for e in portfolio_entities
    ]
    
    # Update company node with portfolio data
    existing = company_queries.get_company(organization_id)
    if existing:
        existing["portfolio"] = portfolio_data_for_storage
        company_queries.upsert_company(existing)
    else:
        # Create new company node
        company_queries.upsert_company({
            "company_id": organization_id,
            "name": name,
            "country_code": "SE",
            "description": "",
            "mission": "",
            "sectors": [],
            "portfolio": portfolio_data_for_storage,
        })
    
    # If portfolio was found, convert Company to Fund (add Fund label)
    if portfolio_entities:
        logger.info(f"Company {organization_id} has portfolio - converting to Fund")
        company_queries.convert_company_to_fund(organization_id)
        # Get existing company data to preserve all fields
        existing_company = company_queries.get_company(organization_id) or {}
        # Update as Fund, preserving all existing fields
        investor_queries.upsert_investor({
            "company_id": organization_id,
            "name": existing_company.get("name", name),
            "country_code": existing_company.get("country_code", "SE"),
            "description": existing_company.get("description"),
            "sectors": existing_company.get("sectors"),
            "mission": existing_company.get("mission"),
            "website": existing_company.get("website"),
            "num_employees": existing_company.get("num_employees"),
            "year_founded": existing_company.get("year_founded"),
            "aliases": existing_company.get("aliases"),
            "key_people": existing_company.get("key_people"),
            "portfolio": portfolio_data_for_storage,
        })
    
    return {
        "organization_id": organization_id,
        "portfolio": portfolio_entities,
        "companies_processed": len(visited) - 1  # Exclude source
    }

