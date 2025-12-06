import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import companies, investors, relationships, search, chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Northern Lights API...")
    try:
        settings = get_settings()
        logger.info(f"API version: {settings.api_version}")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down Northern Lights API...")
        # Clean up GDS session if it was created
        try:
            from app.db.neo4j_client import close_gds_session

            close_gds_session()
        except Exception as e:
            logger.warning(f"Error closing GDS session: {e}")


try:
    settings = get_settings()
except Exception as e:
    logger.error(f"Failed to load settings: {e}", exc_info=True)
    raise

app = FastAPI(
    title="Northern Lights API",
    description="Nordic Fund & Company Transparency Platform",
    version=settings.api_version,
    lifespan=lifespan,
)

# CORS Middleware - Must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.include_router(companies.router, prefix=f"/api/{settings.api_version}/companies", tags=["companies"])
    app.include_router(investors.router, prefix=f"/api/{settings.api_version}/investors", tags=["investors"])
    app.include_router(relationships.router, prefix=f"/api/{settings.api_version}/relationships", tags=["relationships"])
    app.include_router(search.router, prefix=f"/api/{settings.api_version}/search", tags=["search"])
    app.include_router(chat.router, prefix=f"/api/{settings.api_version}/chat", tags=["chat"])
    logger.info("All routers registered successfully")
except Exception as e:
    logger.error(f"Failed to register routers: {e}", exc_info=True)
    raise


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.api_version, "cors": "enabled"}
