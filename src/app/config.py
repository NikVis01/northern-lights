from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Neo4j
    neo4j_uri: str = "neo4j+s://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    
    # GCP
    gcp_project_id: str = ""
    pubsub_topic: str = "northern-lights-ingest"
    
    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    
    # API
    api_version: str = "v1"
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
