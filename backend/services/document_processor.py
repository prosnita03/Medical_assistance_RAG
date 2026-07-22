"""
Document processor: parses text/PDF files, splits into chunks, and
prepares LangChain Document objects for ingestion into the vector store.
"""
import logging
import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.config import get_settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles loading, parsing, and chunking of documents."""

    def __init__(self):
        settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        logger.info(
            f"DocumentProcessor initialized — "
            f"chunk_size={settings.CHUNK_SIZE}, overlap={settings.CHUNK_OVERLAP}"
        )


    # Public API
  

    def process_text(self, text: str, source: str = "user_input") -> List[Document]:
        """Chunk raw text and return a list of LangChain Documents."""
        chunks = self._splitter.split_text(text)
        documents = [
            Document(
                page_content=chunk,
                metadata={"source": source, "chunk_index": i},
            )
            for i, chunk in enumerate(chunks)
        ]
        logger.info(f"Processed text from '{source}' → {len(documents)} chunks")
        return documents

    def process_file(self, file_path: str | Path) -> List[Document]:
        """Load and process a file (txt or pdf). Returns chunked Documents."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._process_pdf(path)
        elif suffix in (".txt", ".md", ".text"):
            return self._process_text_file(path)
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Supported: .txt, .md, .pdf")

    def process_bytes(self, content: bytes, filename: str) -> List[Document]:
        """Process raw bytes (e.g. from an uploaded file)."""
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return self._process_pdf_bytes(content, filename)
        else:
            text = content.decode("utf-8", errors="replace")
            return self.process_text(text, source=filename)

    def process_directory(self, directory: str | Path) -> List[Document]:
        """Recursively process all supported files in a directory."""
        directory = Path(directory)
        all_docs: List[Document] = []
        for file_path in directory.rglob("*"):
            if file_path.suffix.lower() in (".txt", ".md", ".pdf"):
                try:
                    docs = self.process_file(file_path)
                    all_docs.extend(docs)
                    logger.info(f"Processed '{file_path.name}' → {len(docs)} chunks")
                except Exception as e:
                    logger.warning(f"Skipping '{file_path}': {e}")
        return all_docs

    async def process_url(self, url: str) -> List[Document]:
        """Fetch content from a URL, clean HTML, and chunk the text."""
        import httpx
        from bs4 import BeautifulSoup

        logger.info(f"Fetching URL content: {url}")
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
        
        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script, style and navigation elements
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.decompose()
            
        # Get raw text
        raw_text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        lines = (line.strip() for line in raw_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Chunk text
        return self.process_text(clean_text, source=url)

   
    # Private helpers


    def _process_text_file(self, path: Path) -> List[Document]:
        text = path.read_text(encoding="utf-8", errors="replace")
        return self.process_text(text, source=path.name)

    def _process_pdf(self, path: Path) -> List[Document]:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
        except ImportError:
            # Fallback to pypdf
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        return self.process_text(text, source=path.name)

    def _process_pdf_bytes(self, content: bytes, filename: str) -> List[Document]:
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()
        except ImportError:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        return self.process_text(text, source=filename)


# Module-level singleton
_processor: DocumentProcessor | None = None


def get_document_processor() -> DocumentProcessor:
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
