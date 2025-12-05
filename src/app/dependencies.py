from typing import Annotated
from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings


SettingsDep = Annotated[Settings, Depends(get_settings)]


async def verify_api_key(x_api_key: str = Header(None)) -> str:
    """Placeholder for Cloud Endpoints API key validation"""
    # In production, Cloud Endpoints handles this
    if x_api_key is None:
        # Allow requests without key for dev
        return "dev"
    return x_api_key


ApiKeyDep = Annotated[str, Depends(verify_api_key)]
