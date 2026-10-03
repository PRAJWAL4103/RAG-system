"""
RAG Pipeline — handles embedding generation, vector storage (NumPy-based),
similarity search, and answer generation via Google Gemini.

Uses a lightweight JSON + NumPy vector store instead of ChromaDB
to avoid C++ build tool requirements on Windows.
"""

import os
import json
import numpy as np
from google import genai
from typing import List, Dict, Optional
from app.config import (
    GEMINI_API_KEY,
    GENERATION_MODEL,
    EMBEDDING_MODEL,
    TOP_K_RESULTS,
    VECTOR_STORE_PATH,
)

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


class VectorStore:
    """
    Lightweight persistent vector store using NumPy for cosine similarity
    and JSON for metadata persistence. No external DB or build tools needed.
    """

    def __init__(self, store_path: str):
        self.store_path = store_path
        self.embeddings: List[List[float]] = []
        self.documents: List[str] = []
        self.metadatas: List[Dict] = []
        self._load()

    def _load(self):
        """Load existing store from disk."""
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.embeddings = data.get("embeddings", [])
                self.documents = data.get("documents", [])
                self.metadatas = data.get("metadatas", [])
            except (json.JSONDecodeError, KeyError):
                self._reset()
        else:
            self._reset()

    def _save(self):
        """Persist store to disk."""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump({
                "embeddings": self.embeddings,
                "documents": self.documents,
                "metadatas": self.metadatas,
            }, f)

    def _reset(self):
        self.embeddings = []
        self.documents = []
        self.metadatas = []

    def add(self, embeddings: List[List[float]], documents: List[str], metadatas: List[Dict]):
        """Add documents with their embeddings and metadata."""
        self.embeddings.extend(embeddings)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self._save()

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """Find the top-k most similar documents using cosine similarity."""
        if not self.embeddings:
            return []

        # Compute cosine similarities
        query_vec = np.array(query_embedding)
        store_matrix = np.array(self.embeddings)

        # Normalize
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        store_norms = store_matrix / (np.linalg.norm(store_matrix, axis=1, keepdims=True) + 1e-10)

        similarities = store_norms @ query_norm
        top_k = min(top_k, len(similarities))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                "text": self.documents[idx],
                "metadata": self.metadatas[idx],
                "similarity": float(similarities[idx]),
            })

        return results

    def count(self) -> int:
        return len(self.documents)

    def get_all_metadatas(self) -> List[Dict]:
        return self.metadatas

    def clear(self):
        """Clear all stored data."""
        self._reset()
        self._save()


# Initialize the vector store
vector_store = VectorStore(VECTOR_STORE_PATH)


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts using Gemini Embedding API."""
    if not texts:
        return []

    embeddings = []
    # Process in batches of 100 (API limit)
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
        )
        for embedding in result.embeddings:
            embeddings.append(embedding.values)

    return embeddings


def add_documents(chunks: List[Dict]) -> int:
    """
    Add document chunks to the vector store.
    Returns the number of chunks added.
    """
    if not chunks:
        return 0

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Generate embeddings
    embeddings = generate_embeddings(texts)

    # Add to vector store
    vector_store.add(
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return len(texts)


def search_similar(query: str, top_k: int = TOP_K_RESULTS) -> List[Dict]:
    """
    Search for the most similar chunks to the query.
    Returns a list of dicts with text, metadata, and similarity score.
    """
    if vector_store.count() == 0:
        return []

    # Generate query embedding
    query_embedding = generate_embeddings([query])[0]

    # Search vector store
    results = vector_store.query(
        query_embedding=query_embedding,
        top_k=top_k,
    )

    return results


def generate_answer(query: str, context_chunks: Optional[List[Dict]] = None) -> Dict:
    """
    Generate an answer using Gemini, grounded in the retrieved context.
    Returns a dict with the answer and source information.
    """
    if context_chunks is None:
        context_chunks = search_similar(query)

    if not context_chunks:
        return {
            "answer": "I don't have any documents to search through yet. Please upload some documents first!",
            "sources": [],
            "query": query,
        }

    # Build context string
    context_parts = []
    for i, chunk in enumerate(context_chunks):
        source = chunk["metadata"].get("source", "Unknown")
        context_parts.append(f"[Source: {source}, Chunk {chunk['metadata'].get('chunk_index', i)}]\n{chunk['text']}")

    context_str = "\n\n---\n\n".join(context_parts)

    # Build prompt
    prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided context.
If the answer cannot be found in the context, say "I couldn't find information about that in the uploaded documents."
Always cite which source document(s) your answer comes from.

CONTEXT:
{context_str}

QUESTION: {query}

ANSWER:"""

    # Generate response
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
    )

    # Collect unique sources
    sources = []
    seen = set()
    for chunk in context_chunks:
        source = chunk["metadata"].get("source", "Unknown")
        if source not in seen:
            seen.add(source)
            sources.append({
                "filename": source,
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
                "relevance": round(chunk.get("similarity", 0), 3),
            })

    return {
        "answer": response.text,
        "sources": sources,
        "query": query,
    }


def get_document_stats() -> Dict:
    """Get statistics about the stored documents."""
    count = vector_store.count()

    if count == 0:
        return {
            "total_chunks": 0,
            "documents": [],
        }

    # Find unique documents
    doc_names = set()
    for meta in vector_store.get_all_metadatas():
        doc_names.add(meta.get("source", "Unknown"))

    return {
        "total_chunks": count,
        "documents": sorted(list(doc_names)),
    }


def clear_all_documents():
    """Clear all documents from the vector store."""
    vector_store.clear()
