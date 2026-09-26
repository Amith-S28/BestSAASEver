"""Port protocol for dense embedding models."""

from typing import List, Protocol


class IEmbedder(Protocol):
    """Abstract interface for dense text vectorization."""

    async def embed_passage(self, text: str) -> List[float]:
        """Embed a document passage (asymmetric passage mode)."""
        ...

    async def embed_query(self, query: str) -> List[float]:
        """Embed a search query (asymmetric query mode)."""
        ...

    async def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Batch embed with memory-aware chunking."""
        ...

    def dimension(self) -> int:
        """Return embedding vector dimensionality (e.g. 1024 for BGE-Large)."""
        ...
