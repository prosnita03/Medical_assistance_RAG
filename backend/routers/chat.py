"""Chat router — handles medical Q&A via the RAG pipeline."""
import logging
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse, tags=["RAG"])
async def chat(request: ChatRequest):
    """
    Answer a medical question using the RAG pipeline.

    - Retrieves relevant chunks from the ChromaDB knowledge base
    - Generates a Gemini-powered answer with source citations
    """
    try:
        rag = get_rag_service()
        response = await rag.answer_question(
            question=request.question,
            session_id=request.session_id,
        )
        return response
    except Exception as e:
        logger.exception(f"Error in /api/chat: {e}")
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")
