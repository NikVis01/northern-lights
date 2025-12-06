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
from app.services.company_data_extraction import extract_company_fields

logger = logging.getLogger(__name__)

# Try to import investor discovery (may fail if dependencies missing)
try:
    from app.services.investor_discovery import discover_and_link_investors

    INVESTOR_DISCOVERY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Investor discovery not available: {e}")
    INVESTOR_DISCOVERY_AVAILABLE = False
    discover_and_link_investors = None


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
    cleaned = re.sub(r"[-\s]", "", org_id)
    # Check if it's exactly 10 digits
    return len(cleaned) == 10 and cleaned.isdigit()


def extract_portfolio_from_fi(organization_id: str) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Call hack_net.py to extract portfolio companies from FI documents.

    CRITICAL FIX: Wraps the sync Playwright execution in a separate thread
    to avoid 'Sync API inside asyncio loop' errors.
    """
    # Validate organization number format
    if not is_valid_org_number(organization_id):
        logger.warning(f"Skipping FI search for '{organization_id}' - not a valid org number format")
        return [], None

    # --- Worker Function to run in separate thread ---
    def _hack_net_worker(org_id: str):
        try:
            # Import hack_net module using sys.path manipulation
            import sys
            import os
            import tempfile
            from pathlib import Path

            # Add parent directory to path if not already there
            hack_net_dir = str(HACK_NET_PATH)
            if hack_net_dir not in sys.path:
                sys.path.insert(0, hack_net_dir)

            # Import the module inside the thread
            import hack_net

            logger.info(f"Searching FI documents for organization {org_id}")
            # Search for documents
            links = hack_net.search_fi_documents(org_id)
            if not links:
                logger.warning(f"No FI documents found for {org_id}")
                return [], None

            logger.info(f"Found {len(links)} document(s), processing first document...")

            # Process first (latest) document to get portfolio
            portfolio = hack_net.process_document(links[0], org_id)
            logger.info(f"Extracted {len(portfolio)} portfolio company/ies")

            # Also extract report text for company field extraction
            report_text = None
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    file_path = hack_net.download_file(links[0], temp_path)
                    extracted_files = hack_net.unzip_if_needed(file_path)

                    # Find PDF or HTML file
                    pdf_files = [f for f in extracted_files if f.suffix.lower() == ".pdf" and f.is_file()]
                    html_files = [
                        f for f in extracted_files if f.suffix.lower() in [".html", ".xhtml", ".htm"] and f.is_file()
                    ]

                    if pdf_files:
                        # Extract text from first 20 pages of PDF
                        report_text = hack_net.extract_text_from_pdf(pdf_files[0], debug=False)
                        if not report_text or len(report_text) < 1000:
                            # Try extracting more pages via pypdf if hack_net method yielded little text
                            try:
                                from pypdf import PdfReader

                                reader = PdfReader(str(pdf_files[0]))
                                text_parts = []
                                for i in range(min(20, len(reader.pages))):
                                    page = reader.pages[i]
                                    text = page.extract_text()
                                    if text and text.strip():
                                        text_parts.append(text)
                                if text_parts:
                                    report_text = "\n".join(text_parts)
                            except ImportError:
                                pass  # pypdf might not be installed
                    elif html_files:
                        report_text = hack_net.extract_text_from_html(html_files[0], debug=False)

                    if report_text:
                        logger.info(f"Extracted {len(report_text)} characters from report")
            except Exception as e:
                logger.warning(f"Could not extract report text: {e}")
                report_text = None

            return portfolio, report_text

        except ImportError as e:
            logger.error(f"Missing dependencies for hack_net: {e}")
            raise
        except Exception as e:
            # Log here so we see the error from the thread
            logger.error(f"Error inside hack_net worker for {org_id}: {e}", exc_info=True)
            raise

    # --- Execution via ThreadPool ---
    import concurrent.futures

    try:
        # Use a ThreadPoolExecutor to isolate the sync Playwright call from the AsyncIO loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_hack_net_worker, organization_id)
            return future.result()

    except Exception as e:
        logger.error(f"Error extracting portfolio from FI for {organization_id}: {e}")
        # Re-raise or return empty based on preference; here we log and return empty to keep flow alive
        return [], None


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

        response = tavily_client.search(query=search_query, search_depth="basic", max_results=5)

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

        digits = re.sub(r"[^\d]", "", org_number)
        if len(digits) == 10:
            # Format as XXXXXX-XXXX
            formatted = f"{digits[:6]}-{digits[6:]}"
            logger.info(f"Found org number for {company_name}: {formatted}")
            return formatted

        return None
    except Exception as e:
        logger.error(f"Error looking up org number for {company_name}: {e}")
        return None


def lookup_or_create_company(company_name: str) -> Optional[str]:
    """
    Look up company by name in Neo4j, reuse if found, or create with real org number if found via web search.
    Enriches existing companies with new data if available.

    Returns organization_id (company_id in DB) or None if no valid org number found.

    IMPORTANT: Only creates companies with valid Swedish organization numbers.
    Does NOT create placeholder companies with invalid IDs.
    """
    # First, try to find existing company by name (to avoid duplicates)
    existing_by_name = company_queries.find_company_by_name(company_name)
    if existing_by_name:
        existing_org_id = existing_by_name.get("company_id")
        logger.info(f"Found existing company '{company_name}' with org_id {existing_org_id}, reusing and enriching")

        # Enrich existing company with new data from web search
        logger.info(f"Enriching existing company {existing_org_id} ({company_name}) with new data")
        extracted_fields = extract_company_fields(company_name, existing_org_id, report_text=None)

        if extracted_fields:
            # Smart merge: only update fields where new data is better (non-empty) or existing is empty
            for key, new_value in extracted_fields.items():
                if key in ["_labels", "company_id"]:  # Skip internal fields
                    continue
                existing_value = existing_by_name.get(key)

                # Update if: new value is non-empty AND (existing is empty/missing OR new value is more complete)
                if new_value is not None:
                    if isinstance(new_value, str) and new_value.strip():
                        # For strings: update if existing is empty or new is longer (more complete)
                        if not existing_value or (
                            isinstance(existing_value, str) and len(new_value) > len(existing_value)
                        ):
                            existing_by_name[key] = new_value
                    elif isinstance(new_value, list) and new_value:
                        # For lists: merge and deduplicate
                        existing_list = existing_by_name.get(key, []) or []
                        merged_list = list(set(existing_list + new_value))
                        existing_by_name[key] = merged_list
                    elif not existing_value:  # For other types, update if existing is missing
                        existing_by_name[key] = new_value

            existing_by_name["company_id"] = existing_org_id
            existing_by_name["name"] = company_name  # Ensure name is up to date
            if "country_code" not in existing_by_name or not existing_by_name["country_code"]:
                existing_by_name["country_code"] = "SE"

            # Check if it's a Fund or Company
            labels = existing_by_name.get("_labels", [])
            if "Fund" in labels:
                investor_queries.upsert_investor(existing_by_name)
            else:
                company_queries.upsert_company(existing_by_name)
            logger.info(f"Enriched company {existing_org_id} with fields: {list(extracted_fields.keys())}")

        return existing_org_id

    # No existing company found by name, try to find org number via web search
    org_number = lookup_org_number_from_web(company_name)

    if not org_number or not is_valid_org_number(org_number):
        logger.warning(f"Could not find valid organization number for '{company_name}'. Skipping company creation.")
        return None

    # Validate the org number before proceeding
    org_id = org_number
    logger.info(f"Using real org number {org_id} for {company_name}")

    # Check if company already exists by org_id (in case name didn't match but org_id does)
    existing = company_queries.get_company(org_id)
    if existing:
        logger.info(f"Found existing company with org_id {org_id}, reusing and enriching")
        # Enrich with new data (smart merge)
        extracted_fields = extract_company_fields(company_name, org_id, report_text=None)
        if extracted_fields:
            # Smart merge: only update fields where new data is better
            for key, new_value in extracted_fields.items():
                if key in ["_labels", "company_id"]:
                    continue
                existing_value = existing.get(key)

                if new_value is not None:
                    if isinstance(new_value, str) and new_value.strip():
                        if not existing_value or (
                            isinstance(existing_value, str) and len(new_value) > len(existing_value)
                        ):
                            existing[key] = new_value
                    elif isinstance(new_value, list) and new_value:
                        existing_list = existing.get(key, []) or []
                        existing[key] = list(set(existing_list + new_value))
                    elif not existing_value:
                        existing[key] = new_value

            existing["company_id"] = org_id
            existing["name"] = company_name
            if "country_code" not in existing or not existing["country_code"]:
                existing["country_code"] = "SE"

            labels = existing.get("_labels", [])
            if "Fund" in labels:
                investor_queries.upsert_investor(existing)
            else:
                company_queries.upsert_company(existing)
        return org_id

    # Extract company fields from web search before creating
    logger.info(f"Creating new company {company_name} ({org_id})")
    extracted_fields = extract_company_fields(company_name, org_id, report_text=None)

    # Create company node with real org number and extracted fields
    company_data = {
        "company_id": org_id,
        "name": company_name,
        "country_code": "SE",
        "description": "",
        "mission": "",
        "sectors": [],
    }
    company_data.update(extracted_fields)  # Merge extracted fields
    company_queries.upsert_company(company_data)

    return org_id


def process_portfolio_companies(
    source_org_id: str, portfolio_data: List[Dict[str, Any]], visited: Set[str] = None
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

        # Look up or create company (only with valid org number)
        target_org_id = lookup_or_create_company(company_name)

        # Skip if no valid org number found
        if not target_org_id:
            logger.warning(f"Skipping company '{company_name}' - no valid organization number found")
            continue

        # Skip self-ownership
        if source_org_id == target_org_id:
            logger.warning(f"Skipping self-ownership: {company_name} ({target_org_id})")
            continue

        # Create OWNS relationship with ownership percentage
        properties = {}
        if ownership_pct is not None:
            properties["share_percentage"] = float(ownership_pct)

        relationship_queries.add_ownership(owner_id=source_org_id, company_id=target_org_id, properties=properties)

        # Extract company fields from report and web for this portfolio company (daughter company)
        # This should happen for ALL portfolio companies, not just those with their own portfolios
        logger.info(f"Extracting company fields for portfolio company {target_org_id} ({company_name})")

        # Try to get report text for this portfolio company
        portfolio_data_recursive, report_text_recursive = extract_portfolio_from_fi(target_org_id)

        # Extract fields from both report and web search
        extracted_fields = extract_company_fields(company_name, target_org_id, report_text_recursive)

        # Update the company node with extracted fields
        if extracted_fields:
            target_company = company_queries.get_company(target_org_id) or {}
            target_company.update(extracted_fields)
            target_company["company_id"] = target_org_id
            target_company["name"] = company_name
            if "country_code" not in target_company or not target_company["country_code"]:
                target_company["country_code"] = "SE"
            company_queries.upsert_company(target_company)
            logger.info(
                f"Updated portfolio company {target_org_id} with extracted fields: {list(extracted_fields.keys())}"
            )

        # Create EntityRef
        entity_refs.append(
            EntityRef(entity_id=target_org_id, name=company_name, entity_type="company", ownership_pct=ownership_pct)
        )

        # Recursively process this portfolio company if it has its own portfolio
        if target_org_id not in visited and portfolio_data_recursive:
            # Process the recursive portfolio
            recursive_entities = process_portfolio_companies(target_org_id, portfolio_data_recursive, visited)

            # If this company has a portfolio (found in FI docs), convert it to Fund
            # Use portfolio_data_recursive check, not recursive_entities, because
            # recursive_entities might be empty if all items were already visited
            logger.info(f"Company {target_org_id} has portfolio - converting to Fund")
            company_queries.convert_company_to_fund(target_org_id)
            # Update as Fund with portfolio data and extracted fields, preserving all existing fields
            portfolio_data_for_storage = [
                {
                    "entity_id": e.entity_id,
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "ownership_pct": e.ownership_pct,
                }
                for e in recursive_entities
            ]
            target_company = company_queries.get_company(target_org_id) or {}
            # Merge extracted fields (already extracted above, but ensure they're included)
            target_company.update(extracted_fields)
            target_company["company_id"] = target_org_id
            target_company["name"] = company_name
            target_company["portfolio"] = portfolio_data_for_storage
            if "country_code" not in target_company or not target_company["country_code"]:
                target_company["country_code"] = "SE"
            investor_queries.upsert_investor(target_company)

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
        company_queries.upsert_company(
            {
                "company_id": organization_id,
                "name": name,
                "country_code": "SE",
                "description": "",
                "mission": "",
                "sectors": [],
            }
        )

    # Extract portfolio from FI documents and report text
    logger.info(f"Starting portfolio extraction for {organization_id} ({name})")
    portfolio_data, report_text = extract_portfolio_from_fi(organization_id)

    if not portfolio_data:
        logger.warning(f"No portfolio data extracted for {organization_id}")
        # Still try to extract company fields from report/web even if no portfolio
        logger.info(f"Extracting company fields from report and web for {organization_id}")
        extracted_fields = extract_company_fields(name, organization_id, report_text)

        # Always upsert the company, even if no portfolio found
        # If being ingested via /ingest endpoint, it's likely a Fund, so check existing data
        existing = company_queries.get_company(organization_id) or {}

        # Merge extracted fields
        if extracted_fields:
            existing.update(extracted_fields)

        existing["company_id"] = organization_id
        existing["name"] = name
        if "country_code" not in existing or not existing["country_code"]:
            existing["country_code"] = "SE"

        # Check if this should be a Fund (if it already is, or if it has portfolio field set)
        labels = existing.get("_labels", [])
        is_fund = "Fund" in labels or existing.get("portfolio")

        try:
            if is_fund:
                # Convert to Fund if not already, and upsert as Fund
                if "Fund" not in labels:
                    logger.info(f"Converting {organization_id} to Fund (has portfolio or is being ingested as fund)")
                    company_queries.convert_company_to_fund(organization_id)
                logger.info(f"Upserting Fund {organization_id} with data: {list(existing.keys())}")
                investor_queries.upsert_investor(existing)
                logger.info(
                    f"Successfully upserted Fund {organization_id} with extracted fields: {list(extracted_fields.keys()) if extracted_fields else 'no new fields'}"
                )
            else:
                logger.info(f"Upserting company {organization_id} with data: {list(existing.keys())}")
                company_queries.upsert_company(existing)
                logger.info(
                    f"Successfully upserted company {organization_id} with extracted fields: {list(extracted_fields.keys()) if extracted_fields else 'no new fields'}"
                )
        except Exception as e:
            logger.error(f"Failed to upsert company/Fund {organization_id}: {e}", exc_info=True)
            raise

        # Discover and link investors even if no portfolio found
        investor_results = None
        if INVESTOR_DISCOVERY_AVAILABLE and discover_and_link_investors:
            logger.info(f"Discovering investors for {organization_id} ({name})")
            try:
                investor_results = discover_and_link_investors(name, organization_id)
                logger.info(
                    f"Investor discovery complete: {investor_results.get('investors_linked', 0)} investors linked"
                )
            except Exception as e:
                logger.warning(f"Investor discovery failed for {organization_id}: {e}", exc_info=True)
                # Don't fail the entire ingestion if investor discovery fails
        else:
            logger.debug(f"Investor discovery not available, skipping for {organization_id}")

        return {
            "organization_id": organization_id,
            "portfolio": [],
            "companies_processed": 0,
            "investors_discovered": investor_results.get("investors_discovered", 0) if investor_results else 0,
            "investors_linked": investor_results.get("investors_linked", 0) if investor_results else 0,
        }

    # Extract company fields from report and web search
    logger.info(f"Extracting company fields from report and web for {organization_id}")
    extracted_fields = extract_company_fields(name, organization_id, report_text)

    logger.info(f"Processing {len(portfolio_data)} portfolio companies...")

    # Process portfolio companies (recursive)
    visited = set()
    portfolio_entities = process_portfolio_companies(organization_id, portfolio_data, visited)

    # Update company's portfolio field in Neo4j
    # Convert EntityRef to dict for storage
    portfolio_data_for_storage = [
        {"entity_id": e.entity_id, "name": e.name, "entity_type": e.entity_type, "ownership_pct": e.ownership_pct}
        for e in portfolio_entities
    ]

    # Update company node with portfolio data and extracted fields
    existing = company_queries.get_company(organization_id) or {}
    # Merge extracted fields with existing data
    existing.update(extracted_fields)
    existing["company_id"] = organization_id
    existing["name"] = name
    existing["portfolio"] = portfolio_data_for_storage
    # Ensure required fields have defaults
    if "country_code" not in existing or not existing["country_code"]:
        existing["country_code"] = "SE"
    try:
        logger.info(f"Upserting company {organization_id} with portfolio and extracted fields: {list(existing.keys())}")
        company_queries.upsert_company(existing)
        logger.info(
            f"Successfully upserted company {organization_id} with {len(portfolio_data_for_storage)} portfolio items"
        )
    except Exception as e:
        logger.error(f"Failed to upsert company {organization_id}: {e}", exc_info=True)
        raise

    # If portfolio was found, convert Company to Fund (add Fund label)
    if portfolio_entities:
        logger.info(f"Company {organization_id} has portfolio - converting to Fund")
        company_queries.convert_company_to_fund(organization_id)
        # Get existing company data to preserve all fields
        existing_company = company_queries.get_company(organization_id) or {}
        # Update as Fund, preserving all existing fields
        investor_queries.upsert_investor(
            {
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
            }
        )

    # Discover and link investors (who owns this company)
    investor_results = None
    if INVESTOR_DISCOVERY_AVAILABLE and discover_and_link_investors:
        logger.info(f"Discovering investors for {organization_id} ({name})")
        try:
            investor_results = discover_and_link_investors(name, organization_id)
            logger.info(f"Investor discovery complete: {investor_results.get('investors_linked', 0)} investors linked")
        except Exception as e:
            logger.warning(f"Investor discovery failed for {organization_id}: {e}", exc_info=True)
            # Don't fail the entire ingestion if investor discovery fails
    else:
        logger.debug(f"Investor discovery not available, skipping for {organization_id}")

    return {
        "organization_id": organization_id,
        "portfolio": portfolio_entities,
        "companies_processed": len(visited) - 1,  # Exclude source
        "investors_discovered": investor_results.get("investors_discovered", 0) if investor_results else 0,
        "investors_linked": investor_results.get("investors_linked", 0) if investor_results else 0,
    }
