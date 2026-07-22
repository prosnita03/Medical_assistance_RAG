"""
FastAPI application entry point.

Routes:
  GET  /api/health              — System health check
  POST /api/chat                — Medical Q&A (RAG pipeline)
  POST /api/ingest/file         — Upload & ingest a document
  POST /api/ingest/refresh      — Re-ingest the data directory
  POST /api/summarize/text      — Summarize raw medical text
  POST /api/summarize/file      — Summarize an uploaded document
  GET  /                        — Serves the frontend SPA
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import get_settings
from backend.routers import health, chat, ingest, summarize

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Lifespan: warm up singletons on startup
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Medical AI Assistant...")
    settings = get_settings()

    # Pre-initialize singletons so first request isn't slow
    from backend.services.embeddings_service import get_embeddings_service
    from backend.services.vector_store import get_vector_store_service
    from backend.services.rag_service import get_rag_service

    get_embeddings_service()
    vs = get_vector_store_service()
    get_rag_service()

    count = vs.get_collection_size()
    logger.info(f"✅ Ready — Knowledge base: {count} chunks | Model: {settings.GEMINI_MODEL}")
    yield
    logger.info("🛑 Shutting down Medical AI Assistant...")


# ──────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="RAG-powered medical information assistant using LangChain, Gemini, and ChromaDB.",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS + ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(health.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(ingest.router, prefix="/api")
    app.include_router(summarize.router, prefix="/api")

    # Serve frontend static files
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if os.path.isdir(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_frontend():
            return FileResponse(os.path.join(frontend_dir, "index.html"))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
