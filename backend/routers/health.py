"""Health check router."""
from fastapi import APIRouter
from backend.models.schemas import HealthResponse
from backend.config import get_settings
from backend.services.vector_store import get_vector_store_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check system health and knowledge base status."""
    settings = get_settings()
    vector_store = get_vector_store_service()
    collection_size = vector_store.get_collection_size()

    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        collection_size=collection_size,
        model=settings.GEMINI_MODEL,
    )
