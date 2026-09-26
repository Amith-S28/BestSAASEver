"""Port protocol for cross-encoder relevance re-ranking."""

from typing import List, Protocol, Tuple


class IReranker(Protocol):
    """Abstract interface for candidate evidence re-ranking."""

    async def rerank(
        self, query: str, candidates: List[str], top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """Rerank candidates by clinical relevance. Returns list of (original_index, score)."""
        ...
