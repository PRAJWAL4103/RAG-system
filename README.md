# RAG System — AI Document Q&A

A Retrieval-Augmented Generation (RAG) system that lets you upload documents and ask natural-language questions, with answers grounded in your document content.

## Features

- **Multi-format Support** — Upload TXT, PDF, and Markdown files
- **Smart Chunking** — Sentence-aware, overlapping text splitting for optimal retrieval
- **Semantic Search** — Embedding-based similarity search via ChromaDB
- **AI Answers** — Google Gemini generates context-grounded answers
- **Source Attribution** — See exactly which documents informed each answer
- **Beautiful Web UI** — Dark mode, glassmorphism, drag-and-drop, animations

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python + FastAPI |
| Frontend | HTML + CSS + JavaScript |
| LLM | Google Gemini (gemini-2.0-flash) |
| Embeddings | Google text-embedding-004 |
| Vector Store | NumPy + JSON (local, no build tools needed) |

## Quick Start

### 1. Get a Gemini API Key

Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and create a free API key.

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and paste your API key
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Open the UI

Navigate to [http://localhost:8000](http://localhost:8000)

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serve the web UI |
| `POST` | `/api/upload` | Upload documents (multipart form) |
| `POST` | `/api/query` | Ask a question (`{ "question": "..." }`) |
| `GET` | `/api/stats` | Get document statistics |
| `DELETE` | `/api/documents` | Clear all documents |

## How It Works

1. **Upload** — Documents are parsed (TXT/PDF/MD) and split into overlapping chunks
2. **Embed** — Each chunk is converted to a vector embedding via Gemini
3. **Store** — Embeddings are stored in a local ChromaDB vector database
4. **Query** — Your question is embedded and matched against stored chunks
5. **Generate** — The top matching chunks are sent as context to Gemini to generate a grounded answer

## Project Structure

```
RAG/
├── app/
│   ├── main.py              # FastAPI application & routes
│   ├── rag_pipeline.py       # Embedding, retrieval & generation
│   ├── document_processor.py # File parsing & chunking
│   └── config.py             # Configuration & env vars
├── static/
│   ├── index.html            # Web UI
│   ├── style.css             # Styling
│   └── script.js             # Frontend logic
├── uploads/                  # Uploaded documents (auto-created)
├── vector_store/             # Vector database JSON (auto-created)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```
