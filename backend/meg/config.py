"""Application configuration and ranking constants."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings are environment-driven so no deployment secrets enter the repo."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    falkordb_host: str = "localhost"
    falkordb_port: int = Field(default=6379, ge=1, le=65535)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings_enabled: bool = True
    api_port: int = Field(default=8000, ge=1, le=65535)
    default_tenant: str = "demo"


SIMILARITY_WEIGHT = 0.55
SUCCESS_RATE_WEIGHT = 0.20
RECENCY_WEIGHT = 0.15
PATH_OVERLAP_WEIGHT = 0.10
EMBEDDING_DIMENSION = 384
