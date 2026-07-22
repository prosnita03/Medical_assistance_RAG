"""
Application configuration using Pydantic Settings.
Loads values from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import List
import json


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Medical AI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Google Gemini
    GOOGLE_API_KEY: str

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./backend/data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "medical_knowledge"

    # RAG
    TOP_K_RESULTS: int = 5
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100

    # LLM
    GEMINI_MODEL: str = "gemini-1.5-flash"
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.3

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
