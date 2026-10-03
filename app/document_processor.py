"""
Document Processor — parses TXT, PDF, and Markdown files into text chunks
with metadata for downstream embedding and retrieval.
"""

import os
import re
from typing import List, Dict
from PyPDF2 import PdfReader
import markdown
from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_text(filepath: str) -> str:
    """Extract raw text from a file based on its extension."""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == ".pdf":
        reader = PdfReader(filepath)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    elif ext in (".md", ".markdown"):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            md_text = f.read()
        # Convert to HTML then strip tags to get clean text
        html = markdown.markdown(md_text)
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    Uses sentence-aware splitting to avoid breaking mid-sentence.
    """
    if not text.strip():
        return []

    # Split into sentences (rough heuristic)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= chunk_size:
            current_chunk += (" " + sentence) if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Start new chunk with overlap from previous
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk = sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Handle case where text has no sentence endings
    if not chunks and text.strip():
        # Fall back to character-based splitting
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())

    return chunks


def process_document(filepath: str) -> List[Dict]:
    """
    Process a document file into a list of chunk dictionaries.
    Each dict contains: text, metadata (filename, chunk_index).
    """
    filename = os.path.basename(filepath)
    text = extract_text(filepath)
    chunks = chunk_text(text)

    results = []
    for i, chunk in enumerate(chunks):
        results.append({
            "text": chunk,
            "metadata": {
                "source": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
        })

    return results
