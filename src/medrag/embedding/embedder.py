"""Embedding engine — converts parsed Markdown into dense vectors.

Architecture decision: Documents are embedded as WHOLE units (no chunking).
Using BGE-small-en-v1.5 (130MB, 384-dim) for fast local inference on Apple Silicon.
For larger context needs, switch to jinaai/jina-embeddings-v5-small (1.3GB, 1024-dim)
via the EMBEDDING_MODEL env var.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from medrag.config import settings


class Embedder:
    """Local embedding engine using sentence-transformers."""

    def __init__(self, model_name: str | None = None, device: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._device = device

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model (first call loads to GPU/CPU)."""
        if self._model is None:
            print(f"[medrag] Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(
                self.model_name,
                device=self._device or ("mps" if _has_mps() else "cpu"),
                trust_remote_code=True,
            )
            # Update dim from actual model if available
            actual_dim = self._model.get_sentence_embedding_dimension()
            print(f"[medrag]   → Model loaded (dim={actual_dim})")
        return self._model

    @property
    def dim(self) -> int:
        """Output embedding dimensionality."""
        return settings.embedding_dim

    def embed(self, text: str, task: str = "retrieval.passage") -> np.ndarray:
        """Embed a single document as a dense vector.

        Args:
            text: Full markdown text of a document.
            task: Embedding task type. Jina v5 supports prompt_name:
                - "retrieval.passage" for indexing documents
                - "retrieval.query" for search queries
                BGE models don't use task types.

        Returns:
            Normalized embedding vector of shape (dim,).
        """
        model = self.model

        kwargs: dict = {}
        # Jina v5 supports task prompts for better retrieval
        if "jina" in self.model_name.lower():
            kwargs["prompt_name"] = task

        vec = model.encode(text, normalize_embeddings=True, **kwargs)
        return vec

    def embed_batch(self, texts: list[str], task: str = "retrieval.passage") -> np.ndarray:
        """Embed multiple documents at once.

        Args:
            texts: List of markdown texts.
            task: Embedding task type (Jina only).

        Returns:
            Array of shape (len(texts), dim).
        """
        model = self.model

        kwargs: dict = {}
        if "jina" in self.model_name.lower():
            kwargs["prompt_name"] = task

        vecs = model.encode(texts, normalize_embeddings=True, batch_size=8, **kwargs)
        return vecs


def _has_mps() -> bool:
    """Check if Apple Metal Performance Shaders are available."""
    try:
        import torch
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except ImportError:
        return False