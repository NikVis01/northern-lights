"""
Investor discovery service - finds who owns/invests in a given company.
Uses web search and Gemini to discover investment relationships.
"""
import logging
import os
import re
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote, urljoin

logger = logging.getLogger(__name__)

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup4 not available - Allabolag scraping will be limited")

# Try to import Tavily for web search
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    if TAVILY_API_KEY:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    else:
        tavily_client = None
        logger.warning("TAVILY_API_KEY not set - investor discovery will be limited")
except ImportError:
    TAVILY_AVAILABLE = False
    tavily_client = None

# Try to import Gemini
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
        logger.warning("GEMINI_API_KEY not set - investor discovery will be disabled")
except ImportError:
    gemini_model = None

from app.db.queries import company_queries, relationship_queries, investor_queries


def is_valid_org_number(org_id: str) -> bool:
    """Validate Swedish organization number format (10 digits)."""
    cleaned = re.sub(r'[-\s]', '', str(org_id))
    return len(cleaned) == 10 and cleaned.isdigit()


def extract_org_number_from_text(text: str) -> Optional[str]:
    """Extract Swedish organization number from text."""
    # Pattern: 6 digits, optional dash, 4 digits
    pattern = r'\b(\d{6}[-]?\d{4})\b'
    matches = re.findall(pattern, text)
    if matches:
        org_num = matches[0].replace('-', '')
        if len(org_num) == 10:
            return f"{org_num[:6]}-{org_num[6:]}"
    return None


def scrape_allabolag_page(company_name: str, organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Scrape Allabolag.se page for company information, org number, and subsidiaries.
    
    Args:
        company_name: Name of the company to search for
        organization_id: Optional organization ID to construct direct URL
    
    Returns:
        Dict with company info, org_number, and subsidiaries list
    """
    result = {
        "org_number": None,
        "subsidiaries": [],
        "company_info": {}
    }
    
    if not BS4_AVAILABLE:
        logger.warning("BeautifulSoup4 not available, skipping Allabolag scraping")
        return result
    
    try:
        # Try to construct URL or search
        url = None
        if organization_id:
            # Try direct URL pattern (may not always work)
            # Format: https://www.allabolag.se/organisation/{slug}/{location}/{category}/{id}
            # We'll search instead
            pass
        
        # Search Allabolag.se
        search_url = f"https://www.allabolag.se/sok?q={quote(company_name)}"
        logger.info(f"Searching Allabolag.se for: {company_name}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find first result link
        result_link = None
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "/organisation/" in href and company_name.lower() in link.get_text().lower():
                result_link = href
                break
        
        if not result_link:
            logger.warning(f"No Allabolag.se result found for {company_name}")
            return result
        
        # Make absolute URL
        if not result_link.startswith("http"):
            result_link = urljoin("https://www.allabolag.se", result_link)
        
        # Scrape the company page
        logger.info(f"Scraping Allabolag.se page: {result_link}")
        page_response = requests.get(result_link, headers=headers, timeout=10)
        page_response.raise_for_status()
        
        page_soup = BeautifulSoup(page_response.content, "html.parser")
        
        # Extract organization number
        org_text = page_soup.get_text()
        org_number = extract_org_number_from_text(org_text)
        if org_number:
            result["org_number"] = org_number
            logger.info(f"Found org number on Allabolag.se: {org_number}")
        
        # Try to find org number in specific elements
        if not org_number:
            for elem in page_soup.find_all(["span", "div", "p", "td"]):
                text = elem.get_text()
                if "Org.nr" in text or "Organisationsnummer" in text:
                    org_number = extract_org_number_from_text(text)
                    if org_number:
                        result["org_number"] = org_number
                        break
        
        # Extract company info
        company_info = {}
        # Look for key information sections
        for section in page_soup.find_all(["div", "section"], class_=re.compile(r"info|detail|overview", re.I)):
            text = section.get_text()
            if "Telefon" in text:
                phone_match = re.search(r'Telefon[:\s]+([\d\s\-]+)', text)
                if phone_match:
                    company_info["phone"] = phone_match.group(1).strip()
            if "Adress" in text:
                address_match = re.search(r'Adress[:\s]+(.+)', text, re.DOTALL)
                if address_match:
                    company_info["address"] = address_match.group(1).strip().split("\n")[0]
        
        result["company_info"] = company_info
        
        # Try to find subsidiaries in Organisation tab
        subsidiaries = []
        
        # Look for sections mentioning "dotterbolag", "subsidiaries", "Organisation"
        page_text = page_soup.get_text()
        
        # Look for "dotterbolag" section
        if "dotterbolag" in page_text.lower() or "31 dotterbolag" in page_text.lower():
            # Try to find links to subsidiary companies
            for link in page_soup.find_all("a", href=True):
                href = link.get("href", "")
                link_text = link.get_text().strip()
                
                # Check if link goes to another company page
                if "/organisation/" in href and link_text:
                    # Extract company name from link
                    # Skip if it's the same company or navigation links
                    if link_text and len(link_text) > 2 and link_text != company_name:
                        # Check if it looks like a company name (not navigation text)
                        if not any(skip in link_text.lower() for skip in ["mer", "se", "visa", "alla", "översikt"]):
                            subsidiaries.append(link_text)
            
            # Also try to extract from structured data/tables
            for table in page_soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        # First cell might be company name
                        company_cell = cells[0].get_text().strip()
                        if company_cell and len(company_cell) > 2:
                            # Check if it contains org number (indicates it's a company)
                            org_in_cell = extract_org_number_from_text(cells[0].get_text())
                            if org_in_cell or any(keyword in company_cell.lower() for keyword in ["ab", "ab publ", "ltd", "inc"]):
                                subsidiaries.append(company_cell)
        
        # Deduplicate subsidiaries
        subsidiaries = list(dict.fromkeys(subsidiaries))  # Preserve order, remove duplicates
        
        if subsidiaries:
            result["subsidiaries"] = subsidiaries[:20]  # Limit to first 20
            logger.info(f"Found {len(subsidiaries)} subsidiaries on Allabolag.se for {company_name}")
        
        return result
        
    except Exception as e:
        logger.warning(f"Error scraping Allabolag.se for {company_name}: {e}", exc_info=True)
        return result


def search_allabolag_for_company(company_name: str) -> Optional[str]:
    """
    Search Allabolag.se for a company and return its organization number.
    
    Args:
        company_name: Name of the company to search for
    
    Returns:
        Organization number if found, None otherwise
    """
    result = scrape_allabolag_page(company_name)
    return result.get("org_number")


def discover_investors(company_name: str, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Discover who owns/invests in a given company using web search.
    
    Args:
        company_name: Name of the company to find investors for
        organization_id: Optional organization ID for more specific search
    
    Returns:
        List of investors with ownership info: [{"investor_name": str, "ownership_percentage": float, "organization_id": str}, ...]
    """
    if not tavily_client or not gemini_model:
        logger.warning("Tavily or Gemini not available, skipping investor discovery")
        return []
    
    try:
        # Try Allabolag.se first for organization number and basic info
        allabolag_data = None
        if not organization_id:
            logger.info(f"Searching Allabolag.se for {company_name} to find organization number")
            allabolag_org_id = search_allabolag_for_company(company_name)
            if allabolag_org_id:
                organization_id = allabolag_org_id
                logger.info(f"Found organization number from Allabolag.se: {organization_id}")
                allabolag_data = scrape_allabolag_page(company_name, organization_id)
        
        # Build search queries - try multiple approaches including VC/startup investors
        search_queries = [
            f"{company_name} site:allabolag.se",
            f"{company_name} venture capital VC investor funding",
            f"{company_name} riskkapital investerare finansiering",
            f"{company_name} startup investor seed series A B",
            f"{company_name} ägare ägarebolag investerare",
            f"{company_name} major shareholders owners Sweden",
            f"{company_name} största ägare innehav",
            f"{company_name} investment fund owns",
            f"{company_name} backer investor angel",
        ]
        
        if organization_id:
            search_queries.insert(0, f"{company_name} {organization_id} ägare investerare VC")
            search_queries.insert(1, f"{company_name} {organization_id} site:allabolag.se")
        
        # Aggregate search results from all queries
        all_search_context = []
        for query in search_queries[:3]:  # Use top 3 queries
            try:
                logger.info(f"Searching for investors: {query}")
                response = tavily_client.search(
                    query=query,
                    search_depth="advanced",  # Use advanced for better results
                    max_results=10
                )
                
                for result in response.get("results", []):
                    url = result.get("url", "")
                    content = result.get("content", "")
                    title = result.get("title", "")
                    # Prioritize Swedish financial sites
                    if any(domain in url.lower() for domain in ["fi.se", "bolagsverket", "stockholmsborsen", "di.se", "svd.se"]):
                        all_search_context.insert(0, f"Source: {title} ({url})\nContent: {content[:3000]}")
                    else:
                        all_search_context.append(f"Source: {title} ({url})\nContent: {content[:3000]}")
            except Exception as e:
                logger.warning(f"Error searching with query '{query}': {e}")
                continue
        
        # Add Allabolag.se data to context if available
        if allabolag_data and allabolag_data.get("org_number"):
            allabolag_context = f"Source: Allabolag.se\nOrganization Number: {allabolag_data['org_number']}\n"
            if allabolag_data.get("company_info"):
                info = allabolag_data["company_info"]
                if info.get("phone"):
                    allabolag_context += f"Phone: {info['phone']}\n"
                if info.get("address"):
                    allabolag_context += f"Address: {info['address']}\n"
            if allabolag_data.get("subsidiaries"):
                allabolag_context += f"Subsidiaries: {', '.join(allabolag_data['subsidiaries'])}\n"
            all_search_context.insert(0, allabolag_context)
        
        if not all_search_context:
            logger.warning(f"No search results found for investors in {company_name}")
            return []
        
        # Use Gemini to extract investor information
        prompt = f"""You are analyzing web search results to find who owns or invests in a Swedish company.

Company name: {company_name}
Organization ID: {organization_id or "Not provided"}

Search results:
{chr(10).join(all_search_context[:10])}  # Use top 10 results

Extract ALL investors, owners, or funds that own shares in this company. Look for:
- Venture capital (VC) funds and firms (e.g., "Creandum", "EQT Ventures", "Northzone", "Atomico")
- Investment funds (e.g., "Investor AB", "Kinnevik AB", "EQT")
- Private equity firms
- Angel investors and angel groups
- Holding companies
- Major shareholders
- Parent companies
- Investment firms
- Startup accelerators and incubators (if they have equity)
- Corporate venture capital (CVC) arms

IMPORTANT FOR STARTUPS/TECH COMPANIES:
- Look for funding rounds (Seed, Series A, Series B, etc.) and extract the investors mentioned
- Look for press releases about funding, investments, or acquisitions
- Extract VC firms, angel investors, and other backers mentioned in funding announcements
- Even if ownership percentage is not mentioned, include investors if they're clearly listed as investors/backers

Return a JSON array where each object contains:
- "investor_name": Full legal name of the investor/owner (e.g., "Investor AB", "Creandum", "EQT Ventures")
- "ownership_percentage": Percentage owned (as a number, e.g., 22.5 for 22.5%), or null if not mentioned
- "organization_id": Swedish organization number (10 digits, format XXXXXX-XXXX) if found, or null

CRITICAL RULES:
- Extract ALL investors mentioned, including VC funds, angels, and corporate investors
- Look for terms like: "investor", "backer", "funding", "venture capital", "VC", "ägare", "investerare", "finansiering", "riskkapital"
- For startups, look for funding round announcements and extract all investors listed
- Company names often end with "AB", "AB publ", "AB (publ)", etc., but VC funds may have different formats
- If organization number is mentioned in the text, extract it (format: XXXXXX-XXXX or 10 digits)
- If ownership percentage is not mentioned, still include the investor if they're clearly identified as an investor/backer

IT IS PERFECTLY OKAY IF NO INVESTORS ARE FOUND:
- If no investors are found, return an empty array []
- Do not make up or guess investors
- Only extract investors that are clearly and explicitly mentioned in the search results

Return JSON array:"""

        response = gemini_model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        import json
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Gemini JSON response: {e}. Response: {response_text[:500]}")
            # Try to extract JSON from the response if it's embedded in text
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except:
                    logger.error(f"Could not parse JSON from response, returning empty list")
                    return []
            else:
                return []
        
        # Ensure it's a list
        if isinstance(result, dict):
            investors = result.get("investors") or result.get("owners") or result.get("shareholders") or result.get("backers") or []
            if not isinstance(investors, list):
                # If it's a single investor object, wrap it
                if "investor_name" in result or "owner" in result:
                    investors = [result]
                else:
                    investors = []
        elif isinstance(result, list):
            investors = result
        else:
            investors = []
        
        # Validate and enrich investor data
        validated_investors = []
        for investor in investors:
            if isinstance(investor, dict) and "investor_name" in investor:
                investor_name = investor.get("investor_name", "").strip()
                if not investor_name:
                    continue
                
                # Try to extract/find organization ID
                org_id = investor.get("organization_id")
                if not org_id or not is_valid_org_number(org_id):
                    # Try to find org number from search context
                    for context in all_search_context:
                        if investor_name.lower() in context.lower():
                            extracted = extract_org_number_from_text(context)
                            if extracted and is_valid_org_number(extracted):
                                org_id = extracted
                                break
                
                validated_investors.append({
                    "investor_name": investor_name,
                    "ownership_percentage": investor.get("ownership_percentage"),
                    "organization_id": org_id if is_valid_org_number(org_id) else None
                })
        
        logger.info(f"Discovered {len(validated_investors)} investors for {company_name}")
        return validated_investors
        
    except Exception as e:
        logger.error(f"Error discovering investors for {company_name}: {e}", exc_info=True)
        return []


def lookup_or_create_investor(investor_name: str, organization_id: Optional[str] = None) -> Optional[str]:
    """
    Look up investor by name or create if not found.
    Investors are always created as Fund nodes (not Company nodes).
    Returns organization_id if successful, None otherwise.
    """
    # Try to find existing investor by name (could be Fund or Company)
    existing = company_queries.find_company_by_name(investor_name)
    if existing:
        existing_org_id = existing.get("company_id")
        existing_labels = existing.get("_labels", [])
        
        # If it exists but is only a Company, convert to Fund
        if "Fund" not in existing_labels:
            logger.info(f"Found existing node '{investor_name}' as Company, converting to Fund")
            investor_queries.convert_company_to_fund(existing_org_id)
            # Update as Fund to ensure it's properly labeled
            existing.update({
                "company_id": existing_org_id,
                "name": investor_name,
            })
            investor_queries.upsert_investor(existing)
        
        logger.info(f"Found existing investor by name '{investor_name}': {existing_org_id}")
        return existing_org_id
    
    # If we have an org_id, check if it exists
    if organization_id and is_valid_org_number(organization_id):
        existing = company_queries.get_company(organization_id)
        if existing:
            existing_labels = existing.get("_labels", [])
            # If it exists but is only a Company, convert to Fund
            if "Fund" not in existing_labels:
                logger.info(f"Found existing node {organization_id} as Company, converting to Fund")
                investor_queries.convert_company_to_fund(organization_id)
                existing.update({
                    "company_id": organization_id,
                    "name": investor_name,
                })
                investor_queries.upsert_investor(existing)
            logger.info(f"Found existing investor by org_id {organization_id}")
            return organization_id
        
        # Create new investor as Fund
        investor_data = {
            "company_id": organization_id,
            "name": investor_name,
            "country_code": "SE",
            "description": "",
            "mission": "",
            "sectors": [],
        }
        try:
            logger.info(f"Creating new investor (Fund) {organization_id} ({investor_name})")
            investor_queries.upsert_investor(investor_data)
            logger.info(f"Successfully created investor {organization_id}")
            return organization_id
        except Exception as e:
            logger.error(f"Failed to create investor {organization_id}: {e}", exc_info=True)
            return None
    
    # No valid org_id, try web search
    from app.services.portfolio_ingestion import lookup_org_number_from_web
    org_id = lookup_org_number_from_web(investor_name)
    
    if org_id and is_valid_org_number(org_id):
        # Check if exists by this org_id
        existing = company_queries.get_company(org_id)
        if existing:
            existing_labels = existing.get("_labels", [])
            # If it exists but is only a Company, convert to Fund
            if "Fund" not in existing_labels:
                logger.info(f"Found existing node {org_id} as Company, converting to Fund")
                investor_queries.convert_company_to_fund(org_id)
                existing.update({
                    "company_id": org_id,
                    "name": investor_name,
                })
                investor_queries.upsert_investor(existing)
            return org_id
        
        # Create new investor as Fund
        investor_data = {
            "company_id": org_id,
            "name": investor_name,
            "country_code": "SE",
            "description": "",
            "mission": "",
            "sectors": [],
        }
        try:
            logger.info(f"Creating new investor (Fund) {org_id} ({investor_name})")
            investor_queries.upsert_investor(investor_data)
            return org_id
        except Exception as e:
            logger.error(f"Failed to create investor {org_id}: {e}", exc_info=True)
            return None
    
    logger.warning(f"Could not find or create organization ID for investor '{investor_name}'")
    return None


def process_discovered_investors(
    target_company_id: str,
    target_company_name: str,
    investors: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Process discovered investors and create OWNS relationships.
    
    Args:
        target_company_id: Organization ID of the company being invested in
        target_company_name: Name of the company being invested in
        investors: List of discovered investors
    
    Returns:
        List of processed investors with relationship info
    """
    processed = []
    
    for investor in investors:
        investor_name = investor.get("investor_name", "").strip()
        if not investor_name:
            continue
        
        # Look up or create investor
        investor_org_id = lookup_or_create_investor(
            investor_name,
            investor.get("organization_id")
        )
        
        if not investor_org_id:
            logger.warning(f"Skipping investor '{investor_name}' - no valid organization ID")
            continue
        
        # Prevent self-ownership
        if investor_org_id == target_company_id:
            logger.warning(f"Skipping self-ownership: {investor_name} ({investor_org_id})")
            continue
        
        # Create OWNS relationship
        properties = {}
        ownership_pct = investor.get("ownership_percentage")
        if ownership_pct is not None:
            properties["share_percentage"] = float(ownership_pct)
        
        try:
            relationship_queries.add_ownership(
                owner_id=investor_org_id,
                company_id=target_company_id,
                properties=properties
            )
            logger.info(f"Created OWNS relationship: {investor_name} ({investor_org_id}) -> {target_company_name} ({target_company_id})")
            
            processed.append({
                "investor_name": investor_name,
                "investor_id": investor_org_id,
                "ownership_percentage": ownership_pct
            })
        except Exception as e:
            logger.error(f"Failed to create relationship for investor '{investor_name}': {e}", exc_info=True)
            continue
    
    return processed


def discover_and_link_investors(company_name: str, organization_id: str) -> Dict[str, Any]:
    """
    Main function: discover investors in a company and link them in Neo4j.
    
    Args:
        company_name: Name of the company
        organization_id: Organization ID of the company
    
    Returns:
        Dict with discovery results and stats
    """
    logger.info(f"Starting investor discovery for {company_name} ({organization_id})")
    
    # Discover investors via web search
    investors = discover_investors(company_name, organization_id)
    
    if not investors:
        logger.warning(f"No investors discovered for {company_name}")
        return {
            "company_id": organization_id,
            "company_name": company_name,
            "investors_discovered": 0,
            "investors_linked": 0,
            "investors": []
        }
    
    # Process and link investors
    processed = process_discovered_investors(organization_id, company_name, investors)
    
    logger.info(f"Investor discovery complete for {company_name}: {len(processed)} investors linked")
    
    return {
        "company_id": organization_id,
        "company_name": company_name,
        "investors_discovered": len(investors),
        "investors_linked": len(processed),
        "investors": processed
    }

