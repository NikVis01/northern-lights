"""
Chat router for the thin agent.
Handles user queries and returns agent responses.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.agent_service import process_query

router = APIRouter()


class ChatMessage(BaseModel):
    """User message to the agent"""

    message: str


class ChatResponse(BaseModel):
    """Agent response"""

    message: str
    company_found: bool = False
    company_data: dict | None = None
    ingestion_triggered: bool = False
    ingestion_result: dict | None = None
    error: str | None = None


async def process_chat(body: ChatMessage) -> ChatResponse:
    """Process chat message through agent"""
    agent_response = await process_query(body.message)

    return ChatResponse(
        message=agent_response.message,
        company_found=agent_response.company_found,
        company_data=agent_response.company_data,
        ingestion_triggered=agent_response.ingestion_triggered,
        ingestion_result=agent_response.ingestion_result,
        error=agent_response.error,
    )


@router.post("/", response_model=ChatResponse)
async def chat_with_slash(body: ChatMessage):
    """
    Process user query through the thin agent.

    The agent will:
    1. Validate input (company name or org ID)
    2. Search database for company
    3. If found -> Query Neo4j agent for details
    4. If not found -> Trigger ingestion (with web lookup for company names)

    Returns:
        ChatResponse with agent message and optional company data
    """
    return await process_chat(body)


@router.post("", response_model=ChatResponse)
async def chat_without_slash(body: ChatMessage):
    """Chat endpoint without trailing slash"""
    return await process_chat(body)
