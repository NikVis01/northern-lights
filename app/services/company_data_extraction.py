"""
Company data extraction service that combines FI report data and web search.
Extracts company fields from both sources and merges them.
"""
import logging
import os
from typing import Dict, Any, Optional

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
        logger.warning("TAVILY_API_KEY not set - web search extraction will be limited")
except ImportError:
    TAVILY_AVAILABLE = False
    tavily_client = None
    logger.warning("Tavily not available - web search extraction disabled")

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
        logger.warning("GEMINI_API_KEY not set - Gemini extraction will be disabled")
except ImportError:
    gemini_model = None
    logger.warning("Gemini not available - AI extraction disabled")


def extract_company_data_from_report(report_text: str, company_name: str, organization_id: str) -> Dict[str, Any]:
    """
    Extract company fields from FI annual report text using Gemini.
    
    Args:
        report_text: Text content from the annual report
        company_name: Name of the company
        organization_id: Organization ID
    
    Returns:
        Dict with extracted company fields
    """
    if not gemini_model:
        logger.warning("Gemini not available, skipping report extraction")
        return {}
    
    try:
        prompt = f"""You are analyzing a Swedish annual report for {company_name} (Organization ID: {organization_id}).

Extract the following company information from this report:
- description: Short executive summary (2-3 sentences) about what the company does
- mission: Company mission statement or core purpose
- sectors: List of industry sectors/categories the company operates in
- website: Official company website URL (if mentioned)
- num_employees: Number of employees (if mentioned)
- year_founded: Year the company was founded (if mentioned)
- key_people: List of key executives, founders, or board members (names only)
- aliases: Alternative names, brand names, or abbreviations used for this company

Return a JSON object with these fields. Use null for fields not found in the report.

Report content:
{report_text[:50000]}  # Limit to avoid token limits
"""
        
        response = gemini_model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        import json
        extracted_data = json.loads(response_text)
        logger.info(f"Extracted {len(extracted_data)} fields from report for {company_name}")
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting company data from report for {company_name}: {e}", exc_info=True)
        return {}


def extract_company_data_from_web(company_name: str, organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract company fields from web search using Tavily and Gemini.
    
    Args:
        company_name: Name of the company
        organization_id: Optional organization ID for more specific search
    
    Returns:
        Dict with extracted company fields
    """
    if not tavily_client or not gemini_model:
        logger.warning("Tavily or Gemini not available, skipping web extraction")
        return {}
    
    try:
        # Build search query
        if organization_id:
            search_query = f"{company_name} {organization_id} Sweden"
        else:
            search_query = f"{company_name} Sweden company"
        
        logger.info(f"Searching web for: {search_query}")
        
        response = tavily_client.search(
            query=search_query,
            search_depth="basic",
            max_results=10
        )
        
        # Aggregate search results
        search_context = []
        for result in response.get("results", []):
            url = result.get("url", "")
            content = result.get("content", "")
            search_context.append(f"Source: {url}\nContent: {content[:2000]}")  # Limit content per result
        
        if not search_context:
            logger.warning(f"No web search results for {company_name}")
            return {}
        
        # Use Gemini to extract structured data
        prompt = f"""You are analyzing web search results to extract company information for {company_name}.

Extract the following fields from the search results:
- description: Short executive summary (2-3 sentences) about what the company does
- mission: Company mission statement or core purpose
- sectors: List of industry sectors/categories the company operates in
- website: Official company website URL
- num_employees: Number of employees (as integer, or null if not found)
- year_founded: Year the company was founded (as string, or null if not found)
- key_people: List of key executives, founders, or board members (names only)
- aliases: Alternative names, brand names, or abbreviations used for this company

Return a JSON object with these fields. Use null for fields not found.

Search results:
{chr(10).join(search_context[:5])}  # Use top 5 results
"""
        
        response = gemini_model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        import json
        extracted_data = json.loads(response_text)
        logger.info(f"Extracted {len(extracted_data)} fields from web search for {company_name}")
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting company data from web for {company_name}: {e}", exc_info=True)
        return {}


def normalize_website_url(website: str) -> str:
    """
    Normalize website URL to include https://www. if protocol is missing.
    
    Args:
        website: Website URL string
    
    Returns:
        Normalized website URL
    """
    if not website or not isinstance(website, str):
        return website
    
    website = website.strip()
    if not website:
        return website
    
    # If it already has a protocol, return as is
    if website.startswith(("http://", "https://")):
        return website
    
    # If it starts with www., add https://
    if website.startswith("www."):
        return f"https://{website}"
    
    # Otherwise, add https://www.
    return f"https://www.{website}"


def merge_company_data(report_data: Dict[str, Any], web_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge company data from report and web search, prioritizing report data.
    
    Args:
        report_data: Data extracted from FI report
        web_data: Data extracted from web search
    
    Returns:
        Merged company data dict
    """
    merged = {}
    
    # Fields to merge (report takes priority, web as fallback)
    fields = ["description", "mission", "sectors", "website", "num_employees", 
              "year_founded", "key_people", "aliases"]
    
    for field in fields:
        # Report data takes priority if it exists and is not empty
        if field in report_data and report_data[field] is not None:
            if isinstance(report_data[field], list):
                if report_data[field]:  # Non-empty list
                    merged[field] = report_data[field]
                elif field in web_data and web_data[field]:
                    merged[field] = web_data[field]
            elif isinstance(report_data[field], str):
                if report_data[field].strip():  # Non-empty string
                    merged[field] = report_data[field]
                elif field in web_data and web_data[field]:
                    merged[field] = web_data[field]
            else:
                merged[field] = report_data[field]
        elif field in web_data and web_data[field] is not None:
            merged[field] = web_data[field]
    
    # Normalize website URL if present
    if "website" in merged and merged["website"]:
        merged["website"] = normalize_website_url(merged["website"])
    
    # For sectors and key_people, merge lists from both sources
    if "sectors" in report_data and "sectors" in web_data:
        report_sectors = set(report_data.get("sectors", []) or [])
        web_sectors = set(web_data.get("sectors", []) or [])
        merged["sectors"] = list(report_sectors.union(web_sectors))
    
    if "key_people" in report_data and "key_people" in web_data:
        report_people = set(report_data.get("key_people", []) or [])
        web_people = set(web_data.get("key_people", []) or [])
        merged["key_people"] = list(report_people.union(web_people))
    
    if "aliases" in report_data and "aliases" in web_data:
        report_aliases = set(report_data.get("aliases", []) or [])
        web_aliases = set(web_data.get("aliases", []) or [])
        merged["aliases"] = list(report_aliases.union(web_aliases))
    
    return merged


def extract_company_fields(company_name: str, organization_id: str, report_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Main function to extract company fields from both report and web search.
    
    Args:
        company_name: Name of the company
        organization_id: Organization ID
        report_text: Optional text content from FI annual report
    
    Returns:
        Dict with all extracted company fields
    """
    report_data = {}
    if report_text:
        logger.info(f"Extracting company data from report for {company_name}")
        try:
            report_data = extract_company_data_from_report(report_text, company_name, organization_id)
            logger.info(f"Report extraction returned {len(report_data)} fields: {list(report_data.keys())}")
        except Exception as e:
            logger.error(f"Error extracting from report for {company_name}: {e}", exc_info=True)
            report_data = {}
    
    logger.info(f"Extracting company data from web search for {company_name}")
    web_data = {}
    try:
        web_data = extract_company_data_from_web(company_name, organization_id)
        logger.info(f"Web extraction returned {len(web_data)} fields: {list(web_data.keys())}")
    except Exception as e:
        logger.error(f"Error extracting from web for {company_name}: {e}", exc_info=True)
        web_data = {}
    
    merged_data = merge_company_data(report_data, web_data)
    logger.info(f"Merged company data for {company_name}: {len(merged_data)} fields - {list(merged_data.keys())}")
    
    return merged_data

