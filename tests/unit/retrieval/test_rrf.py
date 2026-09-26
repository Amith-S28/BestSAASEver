"""Unit tests for Reciprocal Rank Fusion (RRF) math."""

from medrag.infrastructure.retrieval.rrf import compute_rrf_scores


def test_compute_rrf_scores_basic():
    """RRF correctly fuses dense and sparse candidate rankings."""
    dense = ["docA", "docB", "docC"]
    sparse = ["docB", "docD", "docA"]

    scores = compute_rrf_scores(dense, sparse, k=60)
    score_dict = dict(scores)

    # docB is rank 2 in dense and rank 1 in sparse:
    # 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.03252
    expected_docB = (1.0 / 62.0) + (1.0 / 61.0)
    assert abs(score_dict["docB"] - expected_docB) < 1e-5

    # docA is rank 1 in dense and rank 3 in sparse:
    # 1/(60+1) + 1/(60+3) = 1/61 + 1/63 = 0.016393 + 0.015873 = 0.03226
    expected_docA = (1.0 / 61.0) + (1.0 / 63.0)
    assert abs(score_dict["docA"] - expected_docA) < 1e-5

    # Top candidate must be docB
    assert scores[0][0] == "docB"
    assert scores[1][0] == "docA"


def test_compute_rrf_scores_empty():
    """Empty rankings return empty list."""
    assert compute_rrf_scores([], [], k=60) == []
