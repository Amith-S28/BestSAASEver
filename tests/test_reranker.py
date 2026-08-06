"""Unit tests for NVIDIA NIM Reranker fallback, validation & passage slicing."""

from unittest.mock import MagicMock, patch

from medrag.synthesis.reranker import NIMReranker


def test_reranker_missing_key_fallback():
    """When API key is None, reranker returns original docs truncated to top_n."""
    reranker = NIMReranker()
    reranker.api_key = None
    docs = [("doc1.pdf", "text1", "default"), ("doc2.pdf", "text2", "default")]
    res = reranker.rerank("query", docs, top_n=1)
    assert len(res) == 1
    assert res[0] == docs[0]


def test_reranker_non_nvapi_key_fallback():
    """Non-NVIDIA keys (e.g., OpenRouter sk-or prefix) are rejected — no API call made."""
    reranker = NIMReranker()
    reranker.api_key = "sk-or-v1-somekey"
    docs = [("doc1.pdf", "text1", "default"), ("doc2.pdf", "text2", "default")]
    res = reranker.rerank("query", docs, top_n=2)
    assert res == docs[:2]


def test_reranker_empty_docs():
    """Empty document list returns empty."""
    reranker = NIMReranker()
    reranker.api_key = "nvapi-validkey"
    res = reranker.rerank("query", [], top_n=3)
    assert res == []


def test_reranker_top_n_slicing():
    """Reranker correctly maps API rankings back to documents and limits to top_n."""
    reranker = NIMReranker()
    reranker.api_key = "nvapi-validkey"
    docs = [("doc0.pdf", "alpha", "d0"), ("doc1.pdf", "beta", "d1"),
            ("doc2.pdf", "gamma", "d2"), ("doc3.pdf", "delta", "d3")]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "rankings": [
            {"index": 2, "logit": 0.95},
            {"index": 0, "logit": 0.87},
            {"index": 3, "logit": 0.42},
            {"index": 1, "logit": 0.10},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("medrag.synthesis.reranker.httpx.post", return_value=mock_response):
        res = reranker.rerank("query", docs, top_n=2)
    assert len(res) == 2
    assert res[0] == docs[2]  # index 2 had highest logit
    assert res[1] == docs[0]  # index 0 had second highest


def test_reranker_passage_truncation():
    """Passages are truncated to 2000 chars before sending to API."""
    reranker = NIMReranker()
    reranker.api_key = "nvapi-validkey"
    long_text = "A" * 5000
    docs = [("doc1.pdf", long_text, "default")]

    mock_response = MagicMock()
    mock_response.json.return_value = {"rankings": [{"index": 0, "logit": 0.9}]}
    mock_response.raise_for_status = MagicMock()

    with patch("medrag.synthesis.reranker.httpx.post", return_value=mock_response) as mock_post:
        reranker.rerank("query", docs, top_n=1)
        call_kwargs = mock_post.call_args
        json_payload = call_kwargs.kwargs["json"]
        assert len(json_payload["passages"][0]["text"]) == 2000


def test_reranker_http_failure_graceful():
    """On HTTP error, reranker retries 3x then falls back to raw results."""
    reranker = NIMReranker()
    reranker.api_key = "nvapi-validkey"
    docs = [("doc1.pdf", "text1", "default"), ("doc2.pdf", "text2", "default")]

    with patch("medrag.synthesis.reranker.httpx.post", side_effect=Exception("API down")):
        res = reranker.rerank("query", docs, top_n=2)
    assert len(res) == 2
    assert res == docs[:2]
