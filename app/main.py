"""
FastAPI application — serves the web UI and exposes REST endpoints
for document upload, querying, and management.
"""

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List

from app.config import UPLOAD_DIR
from app.document_processor import process_document
from app.rag_pipeline import (
    add_documents,
    generate_answer,
    get_document_stats,
    clear_all_documents,
)

app = FastAPI(title="RAG System", version="1.0.0")

# Serve static files
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Pydantic models ---

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    query: str


# --- Routes ---

@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and process one or more documents."""
    ALLOWED_EXTENSIONS = {".txt", ".pdf", ".md", ".markdown"}
    results = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": f"Unsupported file type: {ext}",
            })
            continue

        # Save file to uploads directory
        filepath = os.path.join(UPLOAD_DIR, file.filename)
        try:
            with open(filepath, "wb") as f:
                content = await file.read()
                f.write(content)

            # Process document into chunks
            chunks = process_document(filepath)

            # Add chunks to vector store
            num_added = add_documents(chunks)

            results.append({
                "filename": file.filename,
                "status": "success",
                "chunks": num_added,
                "message": f"Successfully processed {num_added} chunks",
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e),
            })

    return JSONResponse(content={"results": results})


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Ask a question and get an answer based on uploaded documents."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = generate_answer(request.question.strip())
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def document_stats():
    """Get statistics about uploaded documents."""
    try:
        stats = get_document_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents")
async def delete_all_documents():
    """Clear all documents from the vector store and uploads folder."""
    try:
        clear_all_documents()

        # Clear uploads folder
        if os.path.exists(UPLOAD_DIR):
            shutil.rmtree(UPLOAD_DIR)
            os.makedirs(UPLOAD_DIR, exist_ok=True)

        return JSONResponse(content={"message": "All documents cleared successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
