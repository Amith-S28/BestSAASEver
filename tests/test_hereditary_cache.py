"""Unit tests for hereditary_cache.py — cache management for MedGen/HPO data."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from medrag.synthesis.hereditary_cache import (
    HereditaryCondition,
    load_cache,
    load_embeddings,
    save_cache,
    is_cache_stale,
    cache_metadata,
)


def _make_condition(cui: str = "C0000001", title: str = "Test Disease") -> HereditaryCondition:
    """Create a test HereditaryCondition."""
    return HereditaryCondition(
        cui=cui,
        title=title,
        definition="A test disease definition",
        inheritance_modes=("autosomal dominant",),
        genes=("GENE1",),
        clinical_features=("fever", "fatigue"),
        sources=("medgen", "hpo"),
        last_updated="2026-01-01",
    )


class TestHereditaryCondition:
    """Tests for the HereditaryCondition dataclass."""

    def test_frozen_dataclass(self) -> None:
        cond = _make_condition()
        with pytest.raises(AttributeError):
            cond.title = "changed"  # type: ignore[misc]

    def test_fields(self) -> None:
        cond = _make_condition(cui="C0020179", title="Huntington disease")
        assert cond.cui == "C0020179"
        assert cond.title == "Huntington disease"
        assert cond.inheritance_modes == ("autosomal dominant",)
        assert cond.genes == ("GENE1",)
        assert cond.clinical_features == ("fever", "fatigue")
        assert cond.sources == ("medgen", "hpo")


class TestSaveAndLoadCache:
    """Tests for save_cache / load_cache round-trip."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        conditions = [
            _make_condition("C0000001", "Disease A"),
            _make_condition("C0000002", "Disease B"),
        ]
        embeddings = np.random.randn(2, 384).astype(np.float32)
        metadata = {"sources": ["medgen", "hpo"]}

        save_cache(conditions, embeddings, metadata, cache_dir=tmp_path)

        # Check files exist
        assert (tmp_path / "conditions.jsonl").exists()
        assert (tmp_path / "embeddings.npy").exists()
        assert (tmp_path / "metadata.json").exists()

        # Load and verify
        loaded = load_cache(cache_dir=tmp_path)
        assert len(loaded) == 2
        assert loaded[0].cui == "C0000001"
        assert loaded[0].title == "Disease A"
        assert loaded[1].cui == "C0000002"

        # Tuples restored correctly
        assert isinstance(loaded[0].inheritance_modes, tuple)
        assert isinstance(loaded[0].genes, tuple)
        assert isinstance(loaded[0].clinical_features, tuple)
        assert isinstance(loaded[0].sources, tuple)

    def test_load_embeddings(self, tmp_path: Path) -> None:
        conditions = [_make_condition()]
        embeddings = np.random.randn(1, 384).astype(np.float32)
        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)

        loaded_emb = load_embeddings(cache_dir=tmp_path)
        assert loaded_emb is not None
        assert loaded_emb.shape == (1, 384)
        np.testing.assert_array_almost_equal(loaded_emb, embeddings)

    def test_load_cache_empty_dir(self, tmp_path: Path) -> None:
        result = load_cache(cache_dir=tmp_path)
        assert result == []

    def test_load_embeddings_missing(self, tmp_path: Path) -> None:
        result = load_embeddings(cache_dir=tmp_path)
        assert result is None

    def test_load_cache_skips_malformed_lines(self, tmp_path: Path) -> None:
        conditions = [_make_condition()]
        embeddings = np.random.randn(1, 384).astype(np.float32)
        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)

        # Append a malformed line
        conditions_file = tmp_path / "conditions.jsonl"
        original = conditions_file.read_text()
        conditions_file.write_text(original + "\n{bad json")

        loaded = load_cache(cache_dir=tmp_path)
        assert len(loaded) == 1  # malformed line skipped


class TestCacheMetadata:
    """Tests for cache_metadata()."""

    def test_metadata_exists(self, tmp_path: Path) -> None:
        conditions = [_make_condition()]
        embeddings = np.random.randn(1, 384).astype(np.float32)
        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)

        meta = cache_metadata(cache_dir=tmp_path)
        assert meta["cache_exists"] is True
        assert meta["total_conditions"] == 1
        assert meta["embedding_dim"] == 384
        assert meta["last_sync"] is not None

    def test_metadata_missing(self, tmp_path: Path) -> None:
        meta = cache_metadata(cache_dir=tmp_path)
        assert meta["cache_exists"] is False
        assert meta["total_conditions"] == 0
        assert meta["last_sync"] is None


class TestIsCacheStale:
    """Tests for is_cache_stale()."""

    def test_stale_when_no_cache(self, tmp_path: Path) -> None:
        assert is_cache_stale(cache_dir=tmp_path) is True

    def test_not_stale_when_fresh(self, tmp_path: Path) -> None:
        conditions = [_make_condition()]
        embeddings = np.random.randn(1, 384).astype(np.float32)
        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)

        # Just saved — should not be stale
        assert is_cache_stale(cache_dir=tmp_path, interval_days=7) is False

    def test_stale_with_zero_interval(self, tmp_path: Path) -> None:
        conditions = [_make_condition()]
        embeddings = np.random.randn(1, 384).astype(np.float32)
        save_cache(conditions, embeddings, {}, cache_dir=tmp_path)

        # interval_days=0 means always stale
        assert is_cache_stale(cache_dir=tmp_path, interval_days=0) is True

    def test_stale_when_metadata_corrupt(self, tmp_path: Path) -> None:
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / "metadata.json").write_text("{bad json")
        assert is_cache_stale(cache_dir=tmp_path) is True