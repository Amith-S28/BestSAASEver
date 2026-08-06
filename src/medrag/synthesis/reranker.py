"""NVIDIA NIM Reranker — reorders retrieved passages by clinical relevance.

Sits between LanceDB hybrid search and LLM synthesis.
Uses the /v1/ranking endpoint (NOT /v1/rerank).
Falls back gracefully if the API is unreachable.
"""

from __future__ import annotations

import time

import httpx

from medrag.config import settings


class NIMReranker:
    """Rerank retrieved documents using NVIDIA NIM ranking API with exponential backoff."""

    def __init__(self) -> None:
        self.base_url = settings.reranker_base_url.rstrip("/")
        self.model = settings.reranker_model
        self.api_key = settings.reranker_api_key

    def rerank(
        self,
        query: str,
        documents: list[tuple[str, str, str]],  # (filename, markdown, folder_id)
        top_n: int = 3,
    ) -> list[tuple[str, str, str]]:
        """Rerank documents by relevance. Returns top_n most relevant.

        On API failure, returns the original list unmodified (graceful degradation).

        Args:
            query: The user's question.
            documents: List of (filename, markdown, folder_id) tuples.
            top_n: Number of top results to return.

        Returns:
            Reranked list of document tuples, truncated to top_n.
        """
        if not documents or not self.api_key or not self.api_key.startswith("nvapi-"):
            return documents[:top_n]

        # Truncate passages to 2000 chars each to stay within API limits
        passages = [{"text": md[:2000]} for _, md, _ in documents]

        for attempt in range(3):
            try:
                response = httpx.post(
                    f"{self.base_url}/ranking",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "query": {"text": query},
                        "passages": passages,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()

                rankings = response.json().get("rankings", [])
                rankings.sort(key=lambda r: r.get("logit", 0), reverse=True)

                reranked = []
                for rank in rankings[:top_n]:
                    idx = rank["index"]
                    if 0 <= idx < len(documents):
                        reranked.append(documents[idx])
                return reranked

            except Exception as e:
                if attempt == 2:
                    print(f"[medrag] NIM Reranker failed after 3 retries ({e}).")
                    print("Falling back to raw results.")
                    return documents[:top_n]
                time.sleep(2 ** attempt)

        return documents[:top_n]
