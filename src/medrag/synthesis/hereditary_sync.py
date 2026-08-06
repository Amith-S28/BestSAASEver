"""Hereditary data sync — download and parse MedGen/HPO/GeneReviews data.

Downloads bulk files from NIH FTP servers, parses them into HereditaryCondition
records, precomputes embeddings, and saves everything to the local cache.

The system is offline-first: after the initial sync, everything works without
internet. Subsequent syncs only run when the cache is stale (default 7 days).

Data sources:
  - MedGen (NIH): conditions, inheritance modes, definitions
  - HPO (via MedGen mapping): clinical features / phenotype markers
  - GeneReviews FTP: gene symbols per condition
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import time
from collections import defaultdict
from pathlib import Path

import httpx
import numpy as np

from medrag.config import settings
from medrag.synthesis.hereditary_cache import (
    HereditaryCondition,
    save_cache,
    is_cache_stale,
)

# ── MedGen FTP URLs ────────────────────────────────────────────────────────

MEDGEN_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/pub/medgen/"

MEDGEN_FILES = {
    "MGCONSO": f"{MEDGEN_FTP_BASE}MGCONSO.RRF.gz",
    "MGSAT": f"{MEDGEN_FTP_BASE}MGSAT.RRF.gz",
    "MGDEF": f"{MEDGEN_FTP_BASE}MGDEF.RRF.gz",
    "HPO_MAPPING": f"{MEDGEN_FTP_BASE}MedGen_HPO_Mapping.txt.gz",
}

GENEREVIEWS_URL = "https://ftp.ncbi.nih.gov/pub/GeneReviews/GeneReviews_short_names.txt"

# MedGen E-utilities API
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Rate limits
RATE_LIMIT_NO_KEY = 3  # requests per second
RATE_LIMIT_WITH_KEY = 10


# ── Download helpers ───────────────────────────────────────────────────────


def _download_file(url: str, dest: Path, client: httpx.Client) -> Path | None:
    """Download a file to dest. Returns the path on success, None on failure."""
    try:
        print(f"[medrag:sync] Downloading {url.split('/')[-1]}...")
        resp = client.get(url, follow_redirects=True, timeout=120.0)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        print(f"[medrag:sync]   -> {dest.name} ({len(resp.content):,} bytes)")
        return dest
    except httpx.HTTPError as e:
        print(f"[medrag:sync]   ✗ Download failed: {e}")
        return None


def _read_gzip_lines(path: Path) -> list[str]:
    """Read all lines from a gzip file."""
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        return f.readlines()


def _read_text_lines(path: Path) -> list[str]:
    """Read all lines from a plain text file (possibly gzipped)."""
    if path.suffix == ".gz":
        return _read_gzip_lines(path)
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


# ── MedGen CSV Parsers ─────────────────────────────────────────────────────


def parse_mgconso(lines: list[str]) -> dict[str, str]:
    """Parse MGCONSO.RRF → {CUI: preferred_name}.

    MGCONSO is pipe-delimited. We want rows where:
      - STT = "PF" (preferred term)
      - ISPREF = "Y"
    Column 0 = CUI, Column 14 = STR (name), Column 2 = STT, Column 1 = ISPREF
    (These positions are based on MedGen RRf specification.)
    """
    cui_to_name: dict[str, str] = {}
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) < 16:
            continue
        cui = parts[0]
        ispref = parts[1]
        stt = parts[2]
        name = parts[14]
        if stt == "PF" and ispref == "Y" and name:
            cui_to_name[cui] = name
    return cui_to_name


def parse_mgsat_inheritance(lines: list[str]) -> dict[str, list[str]]:
    """Parse MGSAT.RRF → {CUI: [inheritance_mode_names]}.

    MGSAT is pipe-delimited. We want rows where:
      - ATN = "Mode_of_inheritance"
    Column 0 = CUI, Column 8 = ATN (attribute name), Column 9 = ATV (attribute value)
    """
    cui_to_inheritance: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) < 10:
            continue
        cui = parts[0]
        atn = parts[8]
        atv = parts[9]
        if atn == "Mode_of_inheritance" and atv:
            cui_to_inheritance[cui].append(atv)
    return dict(cui_to_inheritance)


def parse_mgdef(lines: list[str]) -> dict[str, str]:
    """Parse MGDEF.RRF → {CUI: definition}.

    MGDEF is pipe-delimited.
    Column 0 = CUI, Column 1 = definition text
    """
    cui_to_def: dict[str, str] = {}
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) < 2:
            continue
        cui = parts[0]
        definition = parts[1]
        if cui and definition:
            cui_to_def[cui] = definition
    return cui_to_def


def parse_hpo_mapping(lines: list[str]) -> dict[str, list[str]]:
    """Parse MedGen_HPO_Mapping.txt → {CUI: [HPO_phenotype_names]}.

    Tab-delimited: CUI, HPO_ID, HPO_Name
    """
    cui_to_hpo: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        parts = line.strip().split("\t")
        if len(parts) < 3:
            continue
        cui = parts[0]
        hpo_name = parts[2]
        if cui and hpo_name:
            cui_to_hpo[cui].append(hpo_name)
    return dict(cui_to_hpo)


def parse_genereviews(lines: list[str]) -> dict[str, list[str]]:
    """Parse GeneReviews_short_names.txt → {CUI: [gene_symbols]}.

    Tab-delimited: ShortName, GeneSymbol, OMIM_ID, MedGen_CUI
    """
    cui_to_genes: dict[str, list[str]] = defaultdict(list)
    for line in lines:
        parts = line.strip().split("\t")
        if len(parts) < 4:
            continue
        gene_symbol = parts[1].strip()
        cui = parts[3].strip()
        if cui and gene_symbol and gene_symbol != "-":
            cui_to_genes[cui].append(gene_symbol)
    return dict(cui_to_genes)


# ── Merge pipeline ─────────────────────────────────────────────────────────


def merge_conditions(
    cui_to_name: dict[str, str],
    cui_to_inheritance: dict[str, list[str]],
    cui_to_def: dict[str, str],
    cui_to_hpo: dict[str, list[str]],
    cui_to_genes: dict[str, list[str]],
) -> list[HereditaryCondition]:
    """Merge all data sources by CUI into HereditaryCondition records.

    Only includes conditions that have BOTH a name and at least one
    inheritance mode — these are the hereditary conditions.
    """
    all_cuis = set(cui_to_inheritance.keys())
    conditions: list[HereditaryCondition] = []

    for cui in sorted(all_cuis):
        name = cui_to_name.get(cui, "")
        if not name:
            continue
        inheritance_modes = tuple(cui_to_inheritance.get(cui, []))
        if not inheritance_modes:
            continue

        definition = cui_to_def.get(cui, "")
        hpo_features = cui_to_hpo.get(cui, [])
        genes = cui_to_genes.get(cui, [])

        # Build sources list
        sources = ["medgen"]
        if hpo_features:
            sources.append("hpo")
        if genes:
            sources.append("genereviews")

        # Normalize inheritance mode names
        normalized = tuple(
            _normalize_inheritance(mode) for mode in inheritance_modes
        )

        conditions.append(HereditaryCondition(
            cui=cui,
            title=name,
            definition=definition[:500] if definition else "",  # truncate long defs
            inheritance_modes=normalized,
            genes=tuple(genes),
            clinical_features=tuple(hpo_features[:30]),  # cap features
            sources=tuple(sources),
            last_updated="",
        ))

    return conditions


def _normalize_inheritance(mode: str) -> str:
    """Normalize inheritance mode strings to canonical short forms."""
    mode = mode.strip()
    # Common MedGen inheritance mode patterns → normalized
    mapping = {
        "Autosomal dominant inheritance": "autosomal dominant",
        "Autosomal recessive inheritance": "autosomal recessive",
        "X-linked dominant inheritance": "X-linked dominant",
        "X-linked recessive inheritance": "X-linked recessive",
        "Mitochondrial inheritance": "mitochondrial",
        "Multifactorial inheritance": "multifactorial",
        "Polygenic inheritance": "polygenic",
        "Somatic mutation": "somatic",
        "Genetic anticipation": "genetic anticipation",
    }
    # Exact match first
    if mode in mapping:
        return mapping[mode]
    # Partial match — find longest matching key
    for key, val in mapping.items():
        if key.lower() in mode.lower():
            return val
    # No match — return as-is, lowercase
    return mode.lower()


# ── ESummary enrichment ────────────────────────────────────────────────────


def enrich_missing_features(
    conditions: list[HereditaryCondition],
    client: httpx.Client,
    api_key: str | None = None,
) -> list[HereditaryCondition]:
    """Call MedGen ESummary API for conditions missing clinical features.

    For each condition with no clinical features, fetch the summary which
    may include ClinicalFeatures and PhenotypicAbnormalities.

    Rate limited to 3 req/s without API key, 10 req/s with.
    """
    rate_limit = RATE_LIMIT_WITH_KEY if api_key else RATE_LIMIT_NO_KEY
    delay = 1.0 / rate_limit

    needs_enrichment = [
        c for c in conditions if not c.clinical_features
    ]

    if not needs_enrichment:
        return conditions

    print(f"[medrag:sync] Enriching {len(needs_enrichment)} conditions via ESummary API...")

    enriched: list[HereditaryCondition] = []
    enriched_map: dict[str, HereditaryCondition] = {}

    for i, cond in enumerate(needs_enrichment):
        if i > 0 and i % rate_limit == 0:
            time.sleep(delay * rate_limit)

        try:
            params: dict = {"db": "medgen", "id": cond.cui, "retmode": "json"}
            if api_key:
                params["api_key"] = api_key

            resp = client.get(ESUMMARY_URL, params=params, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

            result = data.get("result", {})
            uid_data = result.get(cond.cui, {})

            # Extract clinical features from conceptmeta
            features: list[str] = []
            conceptmeta = uid_data.get("conceptmeta", {})

            for feat in conceptmeta.get("ClinicalFeatures", []):
                feat_name = feat.get("name", "")
                if feat_name:
                    features.append(feat_name)

            for feat in conceptmeta.get("PhenotypicAbnormalities", []):
                feat_name = feat.get("name", "")
                if feat_name:
                    features.append(feat_name)

            if features:
                sources = list(cond.sources)
                if "hpo" not in sources:
                    sources.append("medgen_api")

                enriched_cond = HereditaryCondition(
                    cui=cond.cui,
                    title=cond.title,
                    definition=cond.definition,
                    inheritance_modes=cond.inheritance_modes,
                    genes=cond.genes,
                    clinical_features=tuple(features[:30]),
                    sources=tuple(sources),
                    last_updated=cond.last_updated,
                )
                enriched_map[cond.cui] = enriched_cond

        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as e:
            print(f"[medrag:sync]   ✗ ESummary failed for {cond.cui}: {e}")
            continue

    # Replace enriched conditions in the list
    result_conditions: list[HereditaryCondition] = []
    for cond in conditions:
        if cond.cui in enriched_map:
            result_conditions.append(enriched_map[cond.cui])
        else:
            result_conditions.append(cond)

    print(f"[medrag:sync] Enriched {len(enriched_map)} conditions with clinical features")
    return result_conditions


# ── Embedding precomputation ───────────────────────────────────────────────


def precompute_embeddings(
    conditions: list[HereditaryCondition],
) -> np.ndarray:
    """Precompute embeddings for all conditions using the Embedder.

    Each condition is embedded as: "{title} {' '.join(clinical_features[:10])}"
    This allows query-time cosine similarity matching.
    """
    from medrag.embedding.embedder import Embedder

    embedder = Embedder()
    texts: list[str] = []
    for cond in conditions:
        features_str = " ".join(cond.clinical_features[:10])
        texts.append(f"{cond.title} {features_str}" if features_str else cond.title)

    print(f"[medrag:sync] Precomputing embeddings for {len(texts)} conditions...")
    vectors = embedder.embed_batch(texts, task="retrieval.passage")
    print(f"[medrag:sync] Embeddings shape: {vectors.shape}")
    return vectors


# ── Main sync runner ──────────────────────────────────────────────────────


def run_sync(force: bool = False) -> dict:
    """Run the full hereditary data sync pipeline.

    Steps:
      1. Download MedGen bulk CSV files + HPO mapping + GeneReviews
      2. Parse all files
      3. Merge into HereditaryCondition records
      4. Enrich missing features via ESummary API
      5. Precompute embeddings
      6. Save everything to cache

    Args:
        force: If True, run sync even if cache is not stale.

    Returns:
        Dict with sync results: {record_count, enriched, success}
    """
    # Check staleness
    if not force and not is_cache_stale():
        print("[medrag:sync] Cache is up to date. Use --force to sync anyway.")
        return {"success": False, "reason": "cache_not_stale"}

    cache_dir = Path(settings.hereditary_cache_dir)
    raw_dir = cache_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    api_key = settings.ncbi_api_key
    rate_limit = RATE_LIMIT_WITH_KEY if api_key else RATE_LIMIT_NO_KEY

    with httpx.Client(timeout=120.0) as client:
        # Step 1: Download files
        print("[medrag:sync] ═══ Downloading MedGen bulk data ═══")
        downloaded: dict[str, Path] = {}

        for name, url in MEDGEN_FILES.items():
            dest = raw_dir / url.split("/")[-1]
            result = _download_file(url, dest, client)
            if result:
                downloaded[name] = result
            else:
                print(f"[medrag:sync] ⚠ Skipping {name} — download failed")

        # GeneReviews (separate URL)
        gr_dest = raw_dir / "GeneReviews_short_names.txt"
        gr_result = _download_file(GENEREVIEWS_URL, gr_dest, client)
        if gr_result:
            downloaded["GENEREVIEWS"] = gr_result
        else:
            print("[medrag:sync] ⚠ Skipping GeneReviews — download failed")

        # Need at least MGCONSO + MGSAT for conditions + inheritance
        if "MGCONSO" not in downloaded or "MGSAT" not in downloaded:
            print("[medrag:sync] ✗ Cannot proceed without MGCONSO and MGSAT")
            return {"success": False, "reason": "missing_core_files"}

        # Step 2: Parse files
        print("[medrag:sync] ═══ Parsing MedGen data ═══")

        cui_to_name = parse_mgconso(_read_gzip_lines(downloaded["MGCONSO"]))
        print(f"[medrag:sync]   MGCONSO: {len(cui_to_name)} conditions with preferred names")

        cui_to_inheritance = parse_mgsat_inheritance(_read_gzip_lines(downloaded["MGSAT"]))
        print(f"[medrag:sync]   MGSAT: {len(cui_to_inheritance)} conditions with inheritance modes")

        cui_to_def: dict[str, str] = {}
        if "MGDEF" in downloaded:
            cui_to_def = parse_mgdef(_read_gzip_lines(downloaded["MGDEF"]))
            print(f"[medrag:sync]   MGDEF: {len(cui_to_def)} definitions")

        cui_to_hpo: dict[str, list[str]] = {}
        if "HPO_MAPPING" in downloaded:
            cui_to_hpo = parse_hpo_mapping(_read_gzip_lines(downloaded["HPO_MAPPING"]))
            print(f"[medrag:sync]   HPO Mapping: {len(cui_to_hpo)} conditions with phenotypes")

        cui_to_genes: dict[str, list[str]] = {}
        if "GENEREVIEWS" in downloaded:
            cui_to_genes = parse_genereviews(_read_text_lines(downloaded["GENEREVIEWS"]))
            print(f"[medrag:sync]   GeneReviews: {len(cui_to_genes)} conditions with gene symbols")

        # Step 3: Merge
        print("[medrag:sync] ═══ Merging data sources ═══")
        conditions = merge_conditions(
            cui_to_name, cui_to_inheritance, cui_to_def,
            cui_to_hpo, cui_to_genes,
        )
        print(f"[medrag:sync]   {len(conditions)} hereditary conditions after merge")

        # Step 4: Enrich
        print("[medrag:sync] ═══ Enriching missing features ═══")
        conditions = enrich_missing_features(conditions, client, api_key)

        # Step 5: Precompute embeddings
        print("[medrag:sync] ═══ Precomputing embeddings ═══")
        embeddings = precompute_embeddings(conditions)

        # Step 6: Save cache
        print("[medrag:sync] ═══ Saving cache ═══")
        metadata = {
            "sources": list(downloaded.keys()),
            "api_key_used": api_key is not None,
        }
        save_cache(conditions, embeddings, metadata, cache_dir)
        print(f"[medrag:sync] ✓ Cache saved: {len(conditions)} conditions, {embeddings.shape}")

    return {
        "success": True,
        "record_count": len(conditions),
        "embedding_shape": list(embeddings.shape),
    }