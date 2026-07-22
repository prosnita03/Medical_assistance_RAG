"""
ChromaDB vector store wrapper.
Manages the persistent medical knowledge collection.
"""
import logging
from typing import List, Tuple
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from backend.config import get_settings
from backend.services.embeddings_service import get_embeddings_service

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Manages the ChromaDB persistent vector store for medical documents."""

    def __init__(self):
        settings = get_settings()
        self.persist_dir = settings.CHROMA_PERSIST_DIR
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        self.top_k = settings.TOP_K_RESULTS

        embeddings = get_embeddings_service().embeddings

        # Persistent ChromaDB client
        self._client = chromadb.PersistentClient(path=self.persist_dir)

        # LangChain Chroma wrapper for easy document ops
        self._vector_store = Chroma(
            client=self._client,
            collection_name=self.collection_name,
            embedding_function=embeddings,
        )
        logger.info(
            f"VectorStoreService ready. Collection: '{self.collection_name}' "
            f"at '{self.persist_dir}'"
        )

    def add_documents(self, documents: List[Document]) -> int:
        """Add documents to the vector store. Returns count of docs added."""
        if not documents:
            return 0
        self._vector_store.add_documents(documents)
        logger.info(f"Added {len(documents)} chunks to vector store.")
        return len(documents)

    def similarity_search_with_scores(
        self, query: str, k: int | None = None
    ) -> List[Tuple[Document, float]]:
        """Retrieve top-k most relevant documents with relevance scores."""
        k = k or self.top_k
        results = self._vector_store.similarity_search_with_relevance_scores(query, k=k)
        return results

    def get_collection_size(self) -> int:
        """Return total number of chunks in the collection."""
        try:
            col = self._client.get_collection(self.collection_name)
            return col.count()
        except Exception:
            return 0

    def delete_collection(self) -> None:
        """Drop and recreate the collection (used for re-ingestion)."""
        try:
            self._client.delete_collection(self.collection_name)
            logger.warning(f"Deleted collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")

    def as_retriever(self, k: int | None = None):
        """Return a LangChain retriever interface."""
        k = k or self.top_k
        return self._vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )


# Module-level singleton
_vector_store_service: VectorStoreService | None = None


def get_vector_store_service() -> VectorStoreService:
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
