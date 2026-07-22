"""
Summarize router — handles medical document/report summarization.
Accepts plain text or uploaded files.
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.models.schemas import SummarizeRequest, SummarizeResponse
from backend.services.rag_service import get_rag_service
from backend.services.document_processor import get_document_processor
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/summarize/text", response_model=SummarizeResponse, tags=["Summarization"])
async def summarize_text(request: SummarizeRequest):
    """
    Summarize a medical text/report provided as raw text.
    Returns structured summary, key findings, and recommendations.
    """
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text too short. Please provide at least 50 characters of medical content.",
        )
    try:
        rag = get_rag_service()
        return await rag.summarize_document(request.text)
    except Exception as e:
        logger.exception(f"Error in /api/summarize/text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize/file", response_model=SummarizeResponse, tags=["Summarization"])
async def summarize_file(file: UploadFile = File(...)):
    """
    Upload a medical document (PDF or TXT) and get a structured summary.
    """
    allowed_types = {".pdf", ".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {allowed_types}",
        )
    try:
        content = await file.read()
        processor = get_document_processor()
        documents = processor.process_bytes(content, file.filename)

        # Combine all chunks for summarization
        full_text = "\n\n".join(doc.page_content for doc in documents)
        if len(full_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Document appears to be empty or unreadable.")

        rag = get_rag_service()
        return await rag.summarize_document(full_text)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error summarizing file '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
