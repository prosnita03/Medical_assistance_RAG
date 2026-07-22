"""
Pydantic schemas for request/response models.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────────────
# Chat Models
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="The medical question to answer")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation history")

    model_config = {
        "json_schema_extra": {
            "example": {"question": "What are the symptoms of Type 2 diabetes?"}
        }
    }


class SourceDocument(BaseModel):
    content: str = Field(..., description="Relevant chunk of source text")
    source: str = Field(..., description="Source document name/path")
    score: Optional[float] = Field(None, description="Relevance score (0-1)")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI-generated answer")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents used")
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Ingest Models
# ──────────────────────────────────────────────

class UrlIngestRequest(BaseModel):
    url: str = Field(..., description="The website URL to ingest")

class IngestResponse(BaseModel):
    message: str
    documents_processed: int
    chunks_added: int
    collection_size: int


# ──────────────────────────────────────────────
# Summarize Models
# ──────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    text: Optional[str] = Field(None, description="Raw text to summarize")

    model_config = {
        "json_schema_extra": {
            "example": {"text": "Patient presents with elevated blood glucose levels..."}
        }
    }


class SummarizeResponse(BaseModel):
    summary: str = Field(..., description="Structured medical summary")
    key_findings: List[str] = Field(default_factory=list, description="Key medical findings")
    recommendations: List[str] = Field(default_factory=list, description="Medical recommendations")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────────
# Health Models
# ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    collection_size: int
    model: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
