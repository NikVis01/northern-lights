"""
LangChain agent service for company queries with database search and validation.

Main flow:
1. Validate input (company name ≤5 words or org ID format)
2. Search database for company
3. If found → Query Neo4j agent for details
4. If not found → Trigger ingestion (with web lookup for company names)
"""

import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.db.queries import company_queries
from app.services.portfolio_ingestion import ingest_company_with_portfolio

logger = logging.getLogger(__name__)

NEO_AGENT_URL = os.getenv("NEO_AGENT_INVOKE")
AURA_CLIENT_ID = os.getenv("AURA_CLIENT_ID")
AURA_CLIENT_SECRET = os.getenv("AURA_CLIENT_SECRET")


class InputValidator:
    """Validates user input for company queries"""

    # Organization ID pattern: UUID format OR Swedish org number (10 digits with optional dash)
    # UUID: 8-4-4-4-12 hex digits (e.g., "0818261f-2208-5ebc-9946-2797cc0d74d5")
    # Swedish org: 10 digits with optional dash (e.g., "556043-4200" or "5560434200")
    UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    SWEDISH_ORG_PATTERN = re.compile(r"^\d{6}-?\d{4}$")

    # Company name pattern: 1-5 words separated by spaces
    COMPANY_NAME_PATTERN = re.compile(r"^[A-Za-zÅÄÖåäö0-9\s&\-\.]{1,100}$")

    @classmethod
    def validate_input(cls, query: str) -> dict[str, any]:
        """
        Validate user input and determine query type.

        Returns:
            dict with keys: valid (bool), type (str), cleaned (str), error (str)
        """
        query = query.strip()

        if not query:
            return {"valid": False, "type": None, "cleaned": None, "error": "Empty query"}

        # Check if it's a UUID
        if cls.UUID_PATTERN.match(query):
            return {"valid": True, "type": "org_id", "cleaned": query.lower(), "error": None}

        # Check if it's a Swedish organization number
        cleaned_org_id = re.sub(r"[-\s]", "", query)
        if cls.SWEDISH_ORG_PATTERN.match(query) or (len(cleaned_org_id) == 10 and cleaned_org_id.isdigit()):
            # Format as XXXXXX-XXXX
            formatted = f"{cleaned_org_id[:6]}-{cleaned_org_id[6:]}"
            return {"valid": True, "type": "org_id", "cleaned": formatted, "error": None}

        # Check if it's a company name (1-5 words)
        words = query.split()
        if len(words) > 5:
            return {
                "valid": False,
                "type": None,
                "cleaned": None,
                "error": (
                    f"Company name too long ({len(words)} words). "
                    "Please use 5 words or less, or provide an organization number."
                ),
            }

        if cls.COMPANY_NAME_PATTERN.match(query):
            return {"valid": True, "type": "company_name", "cleaned": query, "error": None}

        return {
            "valid": False,
            "type": None,
            "cleaned": None,
            "error": (
                "Invalid input format. Please provide a company name (1-5 words) "
                "or organization ID (UUID or Swedish org number)."
            ),
        }


class CompanyAgentTools:
    """Tools for the LangChain agent"""

    def __init__(self):
        self.neo_agent_url = NEO_AGENT_URL

    def _convert_neo4j_to_json(self, obj):
        """Convert Neo4j objects to JSON-serializable format"""
        from neo4j.time import DateTime

        if isinstance(obj, DateTime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._convert_neo4j_to_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_neo4j_to_json(item) for item in obj]
        return obj

    async def search_database(self, query: str) -> str:
        """
        Search database for company by name or organization ID.

        Args:
            query: Company name or organization ID

        Returns:
            JSON string with search results
        """
        import json

        # Validate input
        validation = InputValidator.validate_input(query)
        if not validation["valid"]:
            return json.dumps({"found": False, "error": validation["error"]})

        query_type = validation["type"]
        cleaned_query = validation["cleaned"]

        try:
            if query_type == "org_id":
                # Search by organization ID
                company = company_queries.get_company(cleaned_query)
                if company:
                    # Convert Neo4j objects to JSON-serializable format
                    company_json = self._convert_neo4j_to_json(company)
                    return json.dumps({"found": True, "data": company_json, "query_type": "org_id"})
                else:
                    return json.dumps({"found": False, "query": cleaned_query, "query_type": "org_id"})

            elif query_type == "company_name":
                # Search by company name in Neo4j
                from app.db.neo4j_client import get_driver

                driver = get_driver()
                with driver.session() as session:
                    result = session.run(
                        """
                        MATCH (c)
                        WHERE (c:Company OR c:Fund)
                          AND toLower(c.name) = toLower($name)
                        RETURN c
                        LIMIT 1
                        """,
                        name=cleaned_query,
                    )

                    record = result.single()
                    if record:
                        company_node = record["c"]
                        # Convert node to dictionary
                        company_dict = dict(company_node.items())
                        # Convert Neo4j objects to JSON-serializable format
                        company_json = self._convert_neo4j_to_json(company_dict)
                        return json.dumps({"found": True, "data": company_json, "query_type": "company_name"})
                    else:
                        return json.dumps({"found": False, "query": cleaned_query, "query_type": "company_name"})

        except Exception as e:
            logger.error(f"Error searching database: {e}")
            return json.dumps({"found": False, "error": f"Database search error: {str(e)}"})

    async def _get_neo4j_token(self) -> str | None:
        """
        Fetch Neo4j OAuth access token using client credentials.

        Returns:
            Access token or None if credentials not configured
        """
        if not AURA_CLIENT_ID or not AURA_CLIENT_SECRET:
            logger.warning("AURA_CLIENT_ID or AURA_CLIENT_SECRET not configured")
            return None

        try:
            token_url = "https://api.neo4j.io/oauth/token"

            data = {
                "grant_type": "client_credentials",
                "client_id": AURA_CLIENT_ID,
                "client_secret": AURA_CLIENT_SECRET,
                "audience": "neo4j://api.neo4j.io",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                return token_data.get("access_token")

        except Exception as e:
            logger.error(f"Error fetching Neo4j OAuth token: {e}")
            return None

    async def query_neo4j_agent(self, company_data: str) -> str:
        """
        Query Neo4j agent for detailed company information.

        Args:
            company_data: JSON string with company data from database

        Returns:
            JSON string with Neo4j agent response
        """
        import json

        if not self.neo_agent_url:
            return json.dumps({"error": "NEO_AGENT_INVOKE not configured"})

        # Fetch OAuth token
        token = await self._get_neo4j_token()
        if not token:
            error_msg = "Failed to obtain Neo4j OAuth token. Check AURA_CLIENT_ID and AURA_CLIENT_SECRET."
            return json.dumps({"error": error_msg})

        try:
            data = json.loads(company_data)
            company_id = data.get("company_id") or data.get("organization_id")

            # Prepare request with Bearer token
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            payload = {
                "messages": [{"role": "user", "content": f"Find information about company with ID: {company_id}"}]
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.neo_agent_url, json=payload, headers=headers)
                response.raise_for_status()
                return json.dumps(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(f"Neo4j agent HTTP error: {e}")
            return json.dumps({"error": f"Neo4j agent authentication failed: {e.response.status_code}"})
        except Exception as e:
            logger.error(f"Error querying Neo4j agent: {e}")
            return json.dumps({"error": f"Neo4j agent query failed: {str(e)}"})

    async def trigger_ingestion(self, query: str) -> str:
        """
        Trigger ingestion pipeline for a company.

        If company name provided, uses web lookup to find organization number.

        Args:
            query: Organization ID or company name

        Returns:
            JSON string with ingestion results
        """
        # Validate input
        validation = InputValidator.validate_input(query)
        if not validation["valid"]:
            return f'{{"status": "error", "error": "{validation["error"]}"}}'

        query_type = validation["type"]
        cleaned_query = validation["cleaned"]

        organization_id = None

        # If company name, look up organization number from web
        if query_type == "company_name":
            logger.info(f"Looking up organization number for company name: {cleaned_query}")

            try:
                import json

                from app.services.portfolio_ingestion import (
                    gemini_model,
                    lookup_org_number_from_web,
                    tavily_client,
                )

                # Check if Tavily and Gemini are available
                if not tavily_client or not gemini_model:
                    logger.warning("Tavily or Gemini not available - cannot lookup org number")
                    return json.dumps(
                        {
                            "status": "error",
                            "error": (
                                f"Company '{cleaned_query}' not found -- "
                                "Agent ingest is not possible, try again later. (Tavily/Gemini API not configured)"
                            ),
                        }
                    )

                # Use web lookup to find org number
                organization_id = lookup_org_number_from_web(cleaned_query)

                if not organization_id:
                    error_msg = (
                        f"Could not find organization number for company '{cleaned_query}'. "
                        "Please provide the Swedish organization number (format: XXXXXX-XXXX) manually."
                    )
                    return f'{{"status": "error", "error": "{error_msg}"}}'

                logger.info(f"Found organization number {organization_id} for {cleaned_query}")

            except Exception as e:
                logger.error(f"Error looking up organization number: {e}")
                return json.dumps(
                    {
                        "status": "error",
                        "error": (
                            f"Company '{cleaned_query}' not found -- "
                            f"Agent ingest is not possible, try again later. (Error: {str(e)})"
                        ),
                    }
                )
        else:
            # Already have org ID
            organization_id = cleaned_query

        try:
            # Log progress
            logger.info(f"Starting ingestion for {organization_id} ({cleaned_query})")

            # Run ingestion in thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor, ingest_company_with_portfolio, organization_id, cleaned_query
                )

            logger.info(
                f"Ingestion completed for {organization_id}: {len(result['portfolio'])} portfolio companies found"
            )

            import json

            return json.dumps(
                {
                    "status": "completed",
                    "organization_id": result["organization_id"],
                    "portfolio_companies_found": len(result["portfolio"]),
                    "companies_processed": result["companies_processed"],
                }
            )

        except Exception as e:
            logger.error(f"Error during ingestion for {organization_id}: {e}")
            import json

            return json.dumps({"status": "error", "error": str(e), "organization_id": organization_id})


class AgentResponse:
    """Response from the agent"""

    def __init__(
        self,
        message: str,
        company_found: bool = False,
        company_data: dict[str, any] | None = None,
        ingestion_triggered: bool = False,
        ingestion_result: dict[str, any] | None = None,
        error: str | None = None,
    ):
        self.message = message
        self.company_found = company_found
        self.company_data = company_data
        self.ingestion_triggered = ingestion_triggered
        self.ingestion_result = ingestion_result
        self.error = error

    def to_dict(self) -> dict[str, any]:
        return {
            "message": self.message,
            "company_found": self.company_found,
            "company_data": self.company_data,
            "ingestion_triggered": self.ingestion_triggered,
            "ingestion_result": self.ingestion_result,
            "error": self.error,
        }


async def process_query(query: str) -> AgentResponse:
    """
    Process user query using LangChain agent.

    Flow:
    1. Validate input
    2. Search database
    3. If found → Query Neo4j agent
    4. If not found → Trigger ingestion (if org ID provided)

    Args:
        query: User query (company name or organization ID)

    Returns:
        AgentResponse with results
    """
    logger.info(f"Processing query: {query}")

    # Step 1: Validate input
    validation = InputValidator.validate_input(query)
    if not validation["valid"]:
        return AgentResponse(message=validation["error"], company_found=False, error=validation["error"])

    query_type = validation["type"]
    cleaned_query = validation["cleaned"]

    # Step 2: Search database
    tools = CompanyAgentTools()

    try:
        # Search database
        search_result_str = await tools.search_database(cleaned_query)
        import json

        search_result = json.loads(search_result_str)

        # Step 3: If found, query Neo4j agent
        if search_result.get("found"):
            company_data = search_result.get("data")
            company_name = company_data.get("name", "Unknown")
            company_id = company_data.get("company_id") or company_data.get("organization_id", "N/A")

            # Build detailed company info in markdown
            company_details = f"## ✓ Company Found: **{company_name}**\n\n"

            # Add organization ID
            company_details += f"**Organization ID:** `{company_id}`\n\n"

            # Add description if available
            if company_data.get("description"):
                company_details += f"**Description:**\n{company_data['description']}\n\n"

            # Add sectors if available
            if company_data.get("sectors") and len(company_data["sectors"]) > 0:
                sectors = company_data["sectors"]
                if isinstance(sectors, list):
                    company_details += f"**Sectors:** {', '.join(sectors)}\n\n"
                else:
                    company_details += f"**Sectors:** {sectors}\n\n"

            # Add other details
            details_added = False
            if company_data.get("website"):
                company_details += f"**Website:** [{company_data['website']}]({company_data['website']})\n"
                details_added = True
            if company_data.get("year_founded"):
                company_details += f"**Founded:** {company_data['year_founded']}\n"
                details_added = True
            if company_data.get("num_employees"):
                company_details += f"**Employees:** {company_data['num_employees']}\n"
                details_added = True
            if company_data.get("country_code"):
                company_details += f"**Country:** {company_data['country_code']}\n"
                details_added = True

            if details_added:
                company_details += "\n"

            # Query Neo4j agent for additional information
            neo4j_result_str = await tools.query_neo4j_agent(json.dumps(company_data))
            neo4j_result = json.loads(neo4j_result_str)

            if neo4j_result.get("error"):
                # Fallback to database data if Neo4j agent fails
                company_details += "*Showing information from our database.*"
                return AgentResponse(
                    message=company_details,
                    company_found=True,
                    company_data=company_data,
                )

            # Return Neo4j agent response with company details
            company_details += "*Additional insights from our knowledge graph...*"
            return AgentResponse(
                message=company_details,
                company_found=True,
                company_data=neo4j_result.get("data", company_data),
            )

        # Step 4: Not found - trigger ingestion
        # Now supports both org ID and company name (via web lookup)
        logger.info(f"Company not found with query '{cleaned_query}' - triggering ingestion")

        ingestion_result_str = await tools.trigger_ingestion(cleaned_query)
        ingestion_result = json.loads(ingestion_result_str)

        if ingestion_result.get("status") == "completed":
            portfolio_count = ingestion_result.get("portfolio_companies_found", 0)
            org_id = ingestion_result.get("organization_id")
            companies_processed = ingestion_result.get("companies_processed", 0)

            # Build progress message with markdown
            if query_type == "company_name":
                message = (
                    f"## Company Not Found: *{cleaned_query}*\n\n"
                    f"### 🔍 Looking up organization number...\n"
                    f"✓ Found organization number: `{org_id}`\n\n"
                    f"### 📥 Ingesting company data...\n"
                    f"✓ **Ingestion complete!**\n"
                    f"- Portfolio companies found: **{portfolio_count}**\n"
                    f"- Total companies processed: **{companies_processed}**"
                )
            else:
                message = (
                    f"## Company Not Found\n\n"
                    f"Organization ID: `{org_id}`\n\n"
                    f"### 📥 Ingesting new company...\n"
                    f"✓ **Ingestion complete!**\n"
                    f"- Portfolio companies found: **{portfolio_count}**\n"
                    f"- Total companies processed: **{companies_processed}**"
                )

            return AgentResponse(
                message=message,
                company_found=False,
                ingestion_triggered=True,
                ingestion_result=ingestion_result,
            )
        else:
            error_msg = ingestion_result.get("error", "Unknown error")

            # Check if it's a Tavily/API configuration error - show simplified message
            if "Agent ingest is not possible" in error_msg:
                # Show user-friendly message without technical details
                message = (
                    f"## ❌ Company Not Found\n\n**{cleaned_query}**\n\nAgent ingest is not possible, try again later."
                )
            elif query_type == "company_name":
                message = (
                    f"## ❌ Company Not Found\n\n"
                    f"**{cleaned_query}**\n\n"
                    f"Failed to ingest company:\n```\n{error_msg}\n```"
                )
            else:
                message = (
                    f"## ❌ Company Not Found\n\n"
                    f"Organization ID: `{cleaned_query}`\n\n"
                    f"Attempted ingestion but encountered an error:\n```\n{error_msg}\n```"
                )

            return AgentResponse(
                message=message,
                company_found=False,
                ingestion_triggered=True,
                ingestion_result=ingestion_result,
                error=error_msg,
            )

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return AgentResponse(
            message=f"## ⚠️ Error\n\nAn error occurred while processing your query:\n```\n{str(e)}\n```",
            company_found=False,
            error=str(e),
        )
