"""
RAG service — the core pipeline:
  1. Retrieve relevant chunks from ChromaDB
  2. Build a context-aware prompt
  3. Generate an answer using Gemini
  4. Return the answer with source citations
"""
import logging
import json
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from backend.config import get_settings
from backend.models.schemas import ChatResponse, SourceDocument, SummarizeResponse
from backend.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Prompt Templates
# ──────────────────────────────────────────────

MEDICAL_QA_SYSTEM_PROMPT = """You are MedAssist, an expert AI medical information assistant powered by a curated medical knowledge base.

Your role is to:
- Provide accurate, evidence-based medical information.
- Always prioritize and cite information drawn from the retrieved local knowledge base below when it is relevant.
- If the retrieved context does not contain enough information to fully answer the question, you MUST use your own expert medical knowledge to provide a thorough, accurate answer.
- When supplementing or answering from your own knowledge, clearly mention that the information is from general medical knowledge/guidelines rather than the database.
- Always cite which source documents your information comes from when using the retrieved context.
- Clearly distinguish between general information and clinical advice.
- Always recommend consulting a healthcare professional for personal medical decisions.
- Be empathetic, clear, and professional in your responses.

IMPORTANT DISCLAIMER: You provide general medical information only — NOT personalized medical advice, diagnosis, or treatment. Always advise users to consult qualified healthcare providers.

Retrieved Medical Knowledge:
{context}

Answer the user's question thoroughly and accurately. Use the retrieved context above as your primary source. If the context is insufficient, state that it is not fully covered in the database, and then provide a complete answer using your general medical expertise.
"""

MEDICAL_QA_HUMAN_PROMPT = "Medical Question: {question}"

SUMMARIZE_SYSTEM_PROMPT = """You are MedAssist, an expert medical document summarizer.

Analyze the provided medical text and produce a structured summary in the following JSON format:
{{
  "summary": "A concise 2-3 paragraph summary of the medical content",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3", ...],
  "recommendations": ["Recommendation 1", "Recommendation 2", ...]
}}

Be precise, use proper medical terminology, and highlight the most clinically relevant information.
Always recommend professional medical consultation for treatment decisions.
"""

SUMMARIZE_HUMAN_PROMPT = """Medical Text to Summarize:
{text}"""


class RAGService:
    """Core Retrieval-Augmented Generation pipeline for medical Q&A and summarization."""

    def __init__(self):
        settings = get_settings()

        self._llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.TEMPERATURE,
            max_output_tokens=settings.MAX_TOKENS,
        )

        self._qa_prompt = ChatPromptTemplate.from_messages([
            ("system", MEDICAL_QA_SYSTEM_PROMPT),
            ("human", MEDICAL_QA_HUMAN_PROMPT),
        ])

        self._summarize_prompt = ChatPromptTemplate.from_messages([
            ("system", SUMMARIZE_SYSTEM_PROMPT),
            ("human", SUMMARIZE_HUMAN_PROMPT),
        ])

        logger.info(f"RAGService initialized with model: {settings.GEMINI_MODEL}")

    def _get_string_content(self, content) -> str:
        """Helper to extract a plain string from the LLM response content."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
                elif hasattr(part, "text"):
                    text_parts.append(part.text)
                elif hasattr(part, "get") and part.get("text"):
                    text_parts.append(part.get("text"))
            return "".join(text_parts)
        return str(content)

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    async def answer_question(self, question: str, session_id: str | None = None) -> ChatResponse:
        """
        Full RAG pipeline:
          retrieve → format context → generate → return with sources.
        """
        vector_store = get_vector_store_service()

        # 1. Retrieve relevant documents
        retrieved = vector_store.similarity_search_with_scores(question)

        # 2. Build context string
        context_parts = []
        source_docs: List[SourceDocument] = []

        for doc, score in retrieved:
            source = doc.metadata.get("source", "unknown")
            context_parts.append(f"[Source: {source}]\n{doc.page_content}")
            source_docs.append(
                SourceDocument(
                    content=doc.page_content[:400] + ("..." if len(doc.page_content) > 400 else ""),
                    source=source,
                    score=round(score, 4),
                )
            )

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found in the knowledge base."

        # 3. Build and invoke the chain
        messages = self._qa_prompt.format_messages(context=context, question=question)
        response = await self._llm.ainvoke(messages)
        answer = self._get_string_content(response.content)

        return ChatResponse(
            answer=answer,
            sources=source_docs,
            session_id=session_id,
        )

    async def summarize_document(self, text: str) -> SummarizeResponse:
        """
        Summarize a medical document or report text.
        Returns structured summary with key findings and recommendations.
        """
        messages = self._summarize_prompt.format_messages(text=text[:8000])  # Token guard
        response = await self._llm.ainvoke(messages)
        raw = self._get_string_content(response.content)

        # Parse JSON response
        try:
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            parsed = json.loads(cleaned.strip())
            return SummarizeResponse(
                summary=parsed.get("summary", raw),
                key_findings=parsed.get("key_findings", []),
                recommendations=parsed.get("recommendations", []),
            )
        except (json.JSONDecodeError, KeyError):
            logger.warning("Could not parse JSON from summarize response, using raw text.")
            return SummarizeResponse(
                summary=raw,
                key_findings=[],
                recommendations=["Please consult a healthcare professional for personalized advice."],
            )


# Module-level singleton
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
