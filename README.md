# Medical AI Assistant with RAG

🌐 **Live Demo**: [https://medical-assistance-rag.onrender.com](https://medical-assistance-rag.onrender.com)

A production-ready **Retrieval-Augmented Generation (RAG)** medical information assistant built with:

- **LangChain** — RAG pipeline orchestration
- **Google Gemini API** — LLM generation + embeddings
- **ChromaDB** — Persistent vector database
- **FastAPI** — Scalable async REST backend
- **Glassmorphism UI** — Premium dark-theme web frontend

> **Disclaimer**: This system provides general medical information for educational purposes only. It is NOT a substitute for professional medical advice, diagnosis, or treatment.

## Features

| Feature | Description |
|---------|-------------|
| 🤖 **Medical Q&A** | Ask any medical question — get cited, context-aware answers from the knowledge base |
| 📄 **Report Summarizer** | Upload PDF/TXT medical reports and get structured summaries with key findings |
| 📚 **Knowledge Ingestion** | Upload custom medical documents (PDF/TXT/MD) to expand the knowledge base |
| 🔍 **Source Citations** | Every answer shows which source documents were used |
| 📊 **Live Health Stats** | Real-time knowledge base size and system status |

## Architecture

```
Medical_assistance_RAG/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Pydantic settings from .env
│   ├── routers/
│   │   ├── chat.py                # POST /api/chat
│   │   ├── ingest.py              # POST /api/ingest/file, /api/ingest/refresh
│   │   ├── summarize.py           # POST /api/summarize/text, /api/summarize/file
│   │   └── health.py              # GET  /api/health
│   ├── services/
│   │   ├── rag_service.py         # Core RAG pipeline
│   │   ├── embeddings_service.py  # Gemini text-embedding-004
│   │   ├── vector_store.py        # ChromaDB client
│   │   └── document_processor.py # PDF/TXT chunking
│   └── models/schemas.py          # Pydantic request/response models
├── frontend/
│   ├── index.html                 # Premium SPA
│   ├── style.css                  # Glassmorphism dark theme
│   └── app.js                    # Chat, summarize, ingest UI
├── data/                          # Built-in medical knowledge base
│   ├── symptoms_diseases.txt      # Diseases, symptoms, treatments
│   ├── drug_interactions.txt      # Drug interaction reference
│   └── medical_textbook_excerpts.txt  # Lab values, procedures, guidelines
├── scripts/
│   └── ingest_data.py            # One-time data ingestion script
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick Start

### Prerequisites

- Python 3.11+
- A **Google Gemini API key** → [Get one here](https://aistudio.google.com/app/apikey) (free tier available)

### 1. Clone and set up environment

```bash
cd Medical_assistance_RAG

# Create virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
```

Open `.env` and set your Gemini API key:
```env
GOOGLE_API_KEY=your_actual_api_key_here
```

### 3. Ingest the medical knowledge base

```bash
python scripts/ingest_data.py
```

This processes 3 built-in medical reference files into ChromaDB (~few minutes first time).

### 4. Start the server

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open the app

Navigate to **[http://localhost:8000](http://localhost:8000)** 🎉

---

## Docker Deployment

```bash
# 1. Configure .env (required)
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 2. Build and run
docker-compose up --build

# App is available at http://localhost:8000
```

---

## Cloud Deployment

### Render.com (Recommended — Free tier available)

1. Push your project to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set:
   - **Build Command**: `pip install -r requirements.txt && python scripts/ingest_data.py`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**: Add `GOOGLE_API_KEY`

### Railway.app

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Deploy
railway init
railway add
railway up
```

Set `GOOGLE_API_KEY` in Railway's environment variables dashboard.

### Google Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT/medassist

# Deploy
gcloud run deploy medassist \
  --image gcr.io/YOUR_PROJECT/medassist \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=your_key \
  --region us-central1
```

---

## API Reference

### `GET /api/health`
Returns system health, model info, and knowledge base size.

### `POST /api/chat`
```json
{
  "question": "What are the symptoms of Type 2 diabetes?",
  "session_id": "optional-session-uuid"
}
```
Returns answer with source citations.

### `POST /api/ingest/file`
Upload a PDF, TXT, or MD file to add to the knowledge base.
- Form field: `file`

### `POST /api/ingest/refresh`
Re-ingest all documents from the server's `./data` directory.

### `POST /api/summarize/text`
```json
{
  "text": "Patient presents with elevated blood glucose..."
}
```

### `POST /api/summarize/file`
Upload a PDF or TXT medical report for summarization.
- Form field: `file`

Full interactive docs: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## Adding Your Own Medical Documents

You can expand the knowledge base with any medical documents:

**Via the Web UI:**
1. Click **"Upload Documents"** in the sidebar
2. Drag & drop or browse for PDF/TXT files
3. Click **"Upload to Knowledge Base"**

**Via the API:**
```bash
curl -X POST http://localhost:8000/api/ingest/file \
  -F "file=@/path/to/medical_guidelines.pdf"
```

**By placing files in `./data/` and refreshing:**
```bash
# Add files to ./data/ directory, then:
python scripts/ingest_data.py --no-clear  # Add without clearing
# Or via API:
curl -X POST http://localhost:8000/api/ingest/refresh
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | — | **Required.** Your Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model for generation |
| `EMBEDDING_MODEL` | `models/text-embedding-004` | Embedding model |
| `TOP_K_RESULTS` | `5` | Documents retrieved per query |
| `CHUNK_SIZE` | `800` | Document chunk size in tokens |
| `CHUNK_OVERLAP` | `100` | Chunk overlap for context continuity |
| `TEMPERATURE` | `0.3` | LLM temperature (0=deterministic) |
| `CHROMA_PERSIST_DIR` | `./backend/data/chroma_db` | ChromaDB storage path |

---

## Development

```bash
# Run with hot reload
uvicorn backend.main:app --reload

# API docs
open http://localhost:8000/docs

# Re-ingest after adding documents to ./data/
python scripts/ingest_data.py

# Add documents without clearing existing
python scripts/ingest_data.py --no-clear --data-dir ./my_docs
```

---

##  Tech Stack

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Async REST API framework |
| **LangChain** | RAG pipeline, document processing |
| **Google Gemini** | LLM (gemini-1.5-flash) + embeddings (text-embedding-004) |
| **ChromaDB** | Local persistent vector database |
| **PyMuPDF** | PDF text extraction |
| **Pydantic** | Data validation and settings |
| **Uvicorn** | ASGI server |

---

## Important Disclaimer

This application provides **general medical information for educational purposes only**.

- It does **NOT** provide personalized medical advice
- It does **NOT** replace consultation with qualified healthcare professionals  
- It should **NOT** be used for self-diagnosis or treatment decisions
- In case of medical emergency, call your local emergency services immediately

---
