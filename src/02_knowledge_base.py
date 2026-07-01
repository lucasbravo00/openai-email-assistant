"""
Knowledge Base: Generates embeddings for the PDF chunks using the OpenAI
API, stores them on disk (JSON, no heavy dependencies like faiss) and
allows searching for the most relevant fragments for a given email.

Since this is a single context PDF (not millions of documents), a
simple in-memory index with cosine similarity is more than enough and
avoids extra dependencies like faiss.
"""

import json
import os
from typing import List, Dict, Optional

import numpy as np
from openai import OpenAI


class KnowledgeBase:
    """Simple semantic index (embeddings + cosine similarity) over a PDF"""

    def __init__(self, client: OpenAI, index_path: str = "data/knowledge_index.json",
                 embedding_model: str = "text-embedding-3-small"):
        """
        Args:
            client: Already-initialized OpenAI client
            index_path: Where to save/load the embeddings index
            embedding_model: Embedding model to use
        """
        self.client = client
        self.index_path = index_path
        self.embedding_model = embedding_model
        self.chunks: List[Dict] = []          # [{"id", "text", "page"}]
        self.embeddings: Optional[np.ndarray] = None  # shape (n_chunks, dim)

    def build_index(self, chunks: List, batch_size: int = 100) -> None:
        """
        Generates embeddings for a list of chunks (see 01_pdf_processor.py)
        and stores them in memory + on disk

        Args:
            chunks: List of Chunk objects (id, text, page)
            batch_size: How many chunks to send per API request
        """
        texts = [c.text for c in chunks]
        all_embeddings = []

        print(f"🔄 Generating embeddings for {len(texts)} chunks...")

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            print(f"   {min(i + batch_size, len(texts))}/{len(texts)} processed")

        self.chunks = [{"id": c.id, "text": c.text, "page": c.page} for c in chunks]
        self.embeddings = np.array(all_embeddings, dtype=np.float32)

        self._save_index()
        print(f"✅ Index built and saved to {self.index_path}")

    def _save_index(self) -> None:
        """Saves chunks + embeddings to a local JSON file"""
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        data = {
            "embedding_model": self.embedding_model,
            "chunks": self.chunks,
            "embeddings": self.embeddings.tolist()
        }
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load_index(self) -> bool:
        """
        Loads an already-built index from disk

        Returns:
            True if it could be loaded, False if it doesn't exist yet
        """
        if not os.path.exists(self.index_path):
            return False

        with open(self.index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.chunks = data["chunks"]
        self.embeddings = np.array(data["embeddings"], dtype=np.float32)
        print(f"✅ Index loaded: {len(self.chunks)} chunks")
        return True

    def _embed_query(self, query: str) -> np.ndarray:
        """Generates the embedding for a query (the incoming email)"""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[query]
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def search(self, query: str, top_k: int = 4) -> List[Dict]:
        """
        Searches for the most relevant chunks for a query

        Args:
            query: Query text (e.g. the incoming email's body)
            top_k: How many chunks to return

        Returns:
            List of chunks sorted by relevance, with their score
        """
        if self.embeddings is None or len(self.chunks) == 0:
            print("❌ The index is empty. Run build_index() first.")
            return []

        query_embedding = self._embed_query(query)

        # Vectorized cosine similarity
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        norms[norms == 0] = 1e-8  # avoid division by zero
        scores = (self.embeddings @ query_embedding) / norms

        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append({
                "text": chunk["text"],
                "page": chunk["page"],
                "score": float(scores[idx])
            })

        return results
