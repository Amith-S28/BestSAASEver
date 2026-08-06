"""Embedding engine — converts parsed Markdown into dense vectors.

Uses jinaai/jina-embeddings-v5-small (1024-dim, 32k token context) for full
document embeddings without truncation. Runs on AMD GPU via DirectML with
graceful fallback to CPU.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from medrag.config import settings


def _detect_best_device() -> str | object:
    """Auto-detect the best available compute device.

    Priority: user override > CUDA > DirectML (AMD) > MPS (Apple) > CPU.
    Maps string "dml" -> torch_directml.device().
    """
    target = settings.compute_device.lower()

    if target == "dml":
        try:
            import torch_directml
            return torch_directml.device()
        except ImportError:
            print("[medrag] DirectML requested but torch-directml not installed.")
            print("Falling back to CPU.")
            return "cpu"

    if target in ("cuda", "mps", "cpu"):
        return target

    # Auto detection
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass

    try:
        import torch_directml
        return torch_directml.device()
    except ImportError:
        pass

    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass

    return "cpu"


class Embedder:
    """Local embedding engine using sentence-transformers."""

    def __init__(self, model_name: str | None = None, device: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._device = device

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model (first call loads to GPU/CPU).

        Includes graceful fallback: if DirectML initialization fails,
        retries on CPU without crashing.
        """
        if self._model is None:
            print(f"[medrag] Loading embedding model: {self.model_name}")
            device = self._device or _detect_best_device()
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=device,
                    trust_remote_code=True,
                )
            except Exception as e:
                print(f"[medrag] Device load failed ({e}). Falling back to CPU...")
                self._model = SentenceTransformer(
                    self.model_name,
                    device="cpu",
                    trust_remote_code=True,
                )

            # Update dim from actual model if available
            actual_dim = self._model.get_sentence_embedding_dimension()
            print(f"[medrag]   -> Model loaded (dim={actual_dim}, device={device})")
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

        # Reduced batch size to 4 to prevent VRAM spikes on 8GB GPUs
        vecs = model.encode(texts, normalize_embeddings=True, batch_size=4, **kwargs)
        return vecs


def _has_mps() -> bool:
    """Check if Apple Metal Performance Shaders are available.

    Deprecated: use _detect_best_device() instead for full device support.
    """
    try:
        import torch
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    except ImportError:
        return False
