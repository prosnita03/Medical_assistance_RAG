"""
Data ingestion script — processes all documents in the ./data directory
and loads them into the ChromaDB vector store.

Run once before starting the server:
    python scripts/ingest_data.py
"""
import sys
import os
import logging

# Ensure project root is on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pathlib import Path
from backend.config import get_settings
from backend.services.document_processor import get_document_processor
from backend.services.vector_store import get_vector_store_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)


def ingest_data(data_dir: str = "./data", clear_existing: bool = True) -> int:
    """
    Ingest all documents from the specified directory.

    Args:
        data_dir: Path to the directory containing medical documents.
        clear_existing: If True, clears the existing collection before ingesting.

    Returns:
        Total number of chunks added to the vector store.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        logger.error(f"❌ Data directory not found: {data_path.resolve()}")
        sys.exit(1)

    settings = get_settings()
    logger.info(f"🔧 Using model: {settings.EMBEDDING_MODEL}")
    logger.info(f"📂 Data directory: {data_path.resolve()}")
    logger.info(f"💾 ChromaDB path: {settings.CHROMA_PERSIST_DIR}")

    # Initialize services
    processor = get_document_processor()
    vector_store = get_vector_store_service()

    if clear_existing:
        logger.info("🗑️  Clearing existing collection...")
        vector_store.delete_collection()
        # Reinitialize after deletion
        from backend.services import vector_store as vs_module
        vs_module._vector_store_service = None
        vector_store = get_vector_store_service()

    # Process all documents
    logger.info("📄 Processing documents...")
    documents = processor.process_directory(data_path)

    if not documents:
        logger.warning("⚠️  No documents found. Check your data directory.")
        return 0

    # Group by source for reporting
    sources = {}
    for doc in documents:
        src = doc.metadata.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    logger.info(f"✅ Processed {len(documents)} chunks from {len(sources)} files:")
    for src, count in sources.items():
        logger.info(f"   • {src}: {count} chunks")

    # Ingest into ChromaDB
    logger.info("🚀 Uploading embeddings to ChromaDB...")
    chunks_added = vector_store.add_documents(documents)

    final_size = vector_store.get_collection_size()
    logger.info(f"✅ Ingestion complete!")
    logger.info(f"   • Chunks added: {chunks_added}")
    logger.info(f"   • Total collection size: {final_size}")

    return chunks_added


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest medical documents into ChromaDB")
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Directory containing medical documents (default: ./data)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear existing collection before ingesting",
    )
    args = parser.parse_args()

    total = ingest_data(data_dir=args.data_dir, clear_existing=not args.no_clear)
    print(f"\n🎉 Successfully ingested {total} chunks into the knowledge base!")
    print("You can now start the server with: uvicorn backend.main:app --reload")
