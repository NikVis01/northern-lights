from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.app.config import get_settings
from src.app.routers import companies, investors, relationships, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


settings = get_settings()

app = FastAPI(
    title="Northern Lights API",
    description="Nordic Fund & Company Transparency Platform",
    version=settings.api_version,
    lifespan=lifespan,
)

app.include_router(companies.router, prefix=f"/{settings.api_version}/companies", tags=["companies"])
app.include_router(investors.router, prefix=f"/{settings.api_version}/investors", tags=["investors"])
app.include_router(relationships.router, prefix=f"/{settings.api_version}/relationships", tags=["relationships"])
app.include_router(search.router, prefix=f"/{settings.api_version}/search", tags=["search"])


@app.get("/health")
async def health():
    return {"status": "ok"}
