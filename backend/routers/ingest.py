"""
Ingest router — handles document ingestion into the vector store.
Supports:
  - File upload (PDF, TXT, MD)
  - Re-ingestion of the default data directory
"""
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from backend.models.schemas import IngestResponse, UrlIngestRequest
from backend.services.document_processor import get_document_processor
from backend.services.vector_store import get_vector_store_service
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = Path("./data")


@router.post("/ingest/file", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_file(file: UploadFile = File(...)):
    """
    Upload and ingest a document (PDF, TXT, or MD) into the knowledge base.
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

        vector_store = get_vector_store_service()
        chunks_added = vector_store.add_documents(documents)
        collection_size = vector_store.get_collection_size()

        logger.info(f"Ingested '{file.filename}': {chunks_added} chunks added.")
        return IngestResponse(
            message=f"Successfully ingested '{file.filename}'",
            documents_processed=1,
            chunks_added=chunks_added,
            collection_size=collection_size,
        )
    except Exception as e:
        logger.exception(f"Error ingesting file '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/refresh", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_data_directory():
    """
    Re-ingest all documents from the default ./data directory.
    Clears the existing collection first.
    """
    if not DATA_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Data directory '{DATA_DIR}' not found.")

    try:
        processor = get_document_processor()
        vector_store = get_vector_store_service()

        # Clear existing data
        vector_store.delete_collection()

        # Reinitialize the store after deletion
        from backend.services import vector_store as vs_module
        vs_module._vector_store_service = None
        vector_store = get_vector_store_service()

        # Process all documents
        documents = processor.process_directory(DATA_DIR)
        if not documents:
            raise HTTPException(status_code=400, detail="No documents found in data directory.")

        chunks_added = vector_store.add_documents(documents)
        collection_size = vector_store.get_collection_size()

        logger.info(f"Refreshed knowledge base: {chunks_added} chunks added.")
        return IngestResponse(
            message="Knowledge base refreshed successfully",
            documents_processed=len(set(d.metadata.get("source", "") for d in documents)),
            chunks_added=chunks_added,
            collection_size=collection_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error refreshing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/url", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_url(request: UrlIngestRequest):
    """
    Fetch and ingest content from a website/URL into the knowledge base.
    """
    if not request.url or not (request.url.startswith("http://") or request.url.startswith("https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL scheme. Must start with http:// or https://",
        )
    
    try:
        processor = get_document_processor()
        documents = await processor.process_url(request.url)
        
        if not documents:
            raise HTTPException(status_code=400, detail="No readable content found at the provided URL.")
            
        vector_store = get_vector_store_service()
        chunks_added = vector_store.add_documents(documents)
        collection_size = vector_store.get_collection_size()
        
        logger.info(f"Ingested URL '{request.url}': {chunks_added} chunks added.")
        return IngestResponse(
            message=f"Successfully ingested website content from '{request.url}'",
            documents_processed=1,
            chunks_added=chunks_added,
            collection_size=collection_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error ingesting URL '{request.url}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest URL: {str(e)}")
