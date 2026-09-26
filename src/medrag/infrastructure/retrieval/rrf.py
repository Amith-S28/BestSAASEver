"""Reciprocal Rank Fusion (RRF) algorithm for hybrid search."""

from typing import Dict, List, Tuple


def compute_rrf_scores(
    dense_chunk_ids: List[str],
    sparse_chunk_ids: List[str],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Compute Reciprocal Rank Fusion (RRF) scores combining dense and sparse rankings.

    Formula:
        RRF_Score(d) = sum(1 / (k + rank_i(d))) for each retrieval system i.
    Where rank is 1-based (rank 1 is top candidate).
    """
    scores: Dict[str, float] = {}

    # Accumulate dense ranks
    for rank, chunk_id in enumerate(dense_chunk_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    # Accumulate sparse ranks
    for rank, chunk_id in enumerate(sparse_chunk_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    # Sort descending by fused score
    sorted_candidates = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_candidates
