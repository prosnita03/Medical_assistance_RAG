"""
Embeddings service using Google Gemini text-embedding-004.
"""
import logging
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from backend.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Manages Gemini text embeddings generation."""

    def __init__(self):
        settings = get_settings()
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
        )
        logger.info(f"EmbeddingsService initialized with model: {settings.EMBEDDING_MODEL}")

    @property
    def embeddings(self) -> GoogleGenerativeAIEmbeddings:
        """Return the underlying LangChain embeddings object."""
        return self._embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        return self._embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return self._embeddings.embed_documents(texts)


# Module-level singleton
_embeddings_service: EmbeddingsService | None = None


def get_embeddings_service() -> EmbeddingsService:
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
