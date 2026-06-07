"""Dependency injection — singleton pipeline instance."""

from __future__ import annotations

from functools import lru_cache

from medrag.pipeline import MedRAGPipeline


@lru_cache(maxsize=1)
def get_pipeline() -> MedRAGPipeline:
    """Return the singleton MedRAGPipeline instance."""
    return MedRAGPipeline()