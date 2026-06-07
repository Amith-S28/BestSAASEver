"""Hereditary condition cache — offline-first storage for MedGen/HPO data.

Stores precomputed condition records and their embeddings locally so the
system works fully offline after an initial sync. Cache is refreshed from
NIH MedGen, HPO, and GeneReviews on a configurable interval.

Cache layout:
    data/cache/hereditary/
    ├── conditions.jsonl   — one HereditaryCondition per line
    ├── embeddings.npy     — precomputed condition embeddings (float32, [N, dim])
    ├── metadata.json      — sync metadata (last_sync, record_count, etc.)
    └── raw/               — downloaded MedGen CSV files
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from medrag.config import settings


@dataclass(frozen=True)
class HereditaryCondition:
    """A single hereditary condition from MedGen/HPO/GeneReviews."""

    cui: str  # MedGen CUI (e.g., "C0020179")
    title: str  # Preferred name (e.g., "Huntington disease")
    definition: str  # Brief definition from MGDEF
    inheritance_modes: tuple[str, ...]  # ("autosomal dominant",)
    genes: tuple[str, ...]  # Gene symbols from GeneReviews/MedGen
    clinical_features: tuple[str, ...]  # HPO phenotypes + MedGen clinical features
    sources: tuple[str, ...]  # ("medgen", "hpo", "genereviews") for attribution
    last_updated: str  # ISO date from MedGen


def _cache_dir() -> Path:
    """Resolve the hereditary cache directory."""
    return Path(settings.hereditary_cache_dir)


def load_cache(cache_dir: str | Path | None = None) -> list[HereditaryCondition]:
    """Load all cached conditions from conditions.jsonl.

    Returns an empty list if the cache does not exist or is unreadable.
    """
    path = Path(cache_dir) if cache_dir else _cache_dir()
    conditions_file = path / "conditions.jsonl"
    if not conditions_file.exists():
        return []

    conditions: list[HereditaryCondition] = []
    for line in conditions_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            # Convert lists to tuples for frozen dataclass
            raw["inheritance_modes"] = tuple(raw.get("inheritance_modes", []))
            raw["genes"] = tuple(raw.get("genes", []))
            raw["clinical_features"] = tuple(raw.get("clinical_features", []))
            raw["sources"] = tuple(raw.get("sources", []))
            conditions.append(HereditaryCondition(**raw))
        except (json.JSONDecodeError, TypeError):
            continue  # skip malformed lines

    return conditions


def load_embeddings(cache_dir: str | Path | None = None) -> np.ndarray | None:
    """Load precomputed condition embeddings from embeddings.npy.

    Returns None if the file does not exist.
    """
    path = Path(cache_dir) if cache_dir else _cache_dir()
    emb_file = path / "embeddings.npy"
    if not emb_file.exists():
        return None
    return np.load(str(emb_file))


def save_cache(
    conditions: list[HereditaryCondition],
    embeddings: np.ndarray,
    metadata: dict,
    cache_dir: str | Path | None = None,
) -> None:
    """Write conditions, embeddings, and metadata to the cache directory."""
    path = Path(cache_dir) if cache_dir else _cache_dir()
    path.mkdir(parents=True, exist_ok=True)

    # Write conditions as JSONL
    conditions_file = path / "conditions.jsonl"
    lines: list[str] = []
    for cond in conditions:
        d = asdict(cond)
        # Convert tuples back to lists for JSON serialization
        d["inheritance_modes"] = list(d["inheritance_modes"])
        d["genes"] = list(d["genes"])
        d["clinical_features"] = list(d["clinical_features"])
        d["sources"] = list(d["sources"])
        lines.append(json.dumps(d, ensure_ascii=False))
    conditions_file.write_text("\n".join(lines))

    # Write embeddings
    np.save(str(path / "embeddings.npy"), embeddings.astype(np.float32))

    # Write metadata
    meta = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "record_count": len(conditions),
        "embedding_dim": embeddings.shape[1] if embeddings.ndim == 2 else 0,
        "embedding_count": embeddings.shape[0] if embeddings.ndim == 2 else 0,
        **metadata,
    }
    (path / "metadata.json").write_text(json.dumps(meta, indent=2))


def is_cache_stale(
    cache_dir: str | Path | None = None,
    interval_days: int | None = None,
) -> bool:
    """Check if the cache needs refreshing.

    Returns True if:
      - Cache does not exist
      - Cache metadata is missing/unreadable
      - Last sync was more than interval_days ago
    """
    path = Path(cache_dir) if cache_dir else _cache_dir()
    interval = interval_days if interval_days is not None else settings.hereditary_sync_interval_days

    meta_file = path / "metadata.json"
    if not meta_file.exists():
        return True

    try:
        meta = json.loads(meta_file.read_text())
        last_sync_str = meta.get("last_sync", "")
        if not last_sync_str:
            return True
        last_sync = datetime.fromisoformat(last_sync_str)
        if last_sync.tzinfo is None:
            last_sync = last_sync.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age_days = (now - last_sync).days
        return age_days >= interval
    except (json.JSONDecodeError, ValueError, TypeError):
        return True


def cache_metadata(cache_dir: str | Path | None = None) -> dict:
    """Return cache status metadata.

    Returns a dict with keys: cache_exists, last_sync, total_conditions, embedding_dim.
    """
    path = Path(cache_dir) if cache_dir else _cache_dir()
    meta_file = path / "metadata.json"
    conditions_file = path / "conditions.jsonl"

    if not meta_file.exists() or not conditions_file.exists():
        return {
            "cache_exists": False,
            "last_sync": None,
            "total_conditions": 0,
            "embedding_dim": 0,
        }

    try:
        meta = json.loads(meta_file.read_text())
        return {
            "cache_exists": True,
            "last_sync": meta.get("last_sync"),
            "total_conditions": meta.get("record_count", 0),
            "embedding_dim": meta.get("embedding_dim", 0),
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "cache_exists": False,
            "last_sync": None,
            "total_conditions": 0,
            "embedding_dim": 0,
        }