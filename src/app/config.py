from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    neo4j_uri: str = "neo4j+s://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    gcp_project_id: str = ""
    pubsub_topic: str = "northern-lights-ingest"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    api_version: str = "v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
