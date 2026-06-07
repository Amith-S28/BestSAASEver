"""Hereditary relevance matcher — selects the most relevant conditions for a query.

At query time, the user's query embedding is compared against precomputed
condition embeddings. The top-N most relevant conditions are formatted into
a reference string with source attribution and medical disclaimers.

If no cache exists (e.g., first run before sync), falls back to the hardcoded
FALLBACK_CONDITIONS list with FDA-compliant language.
"""

from __future__ import annotations

import numpy as np

from medrag.config import settings
from medrag.synthesis.hereditary_cache import (
    HereditaryCondition,
    load_cache,
    load_embeddings,
    cache_metadata,
)

# ── Disclaimer text ───────────────────────────────────────────────────────

MEDICAL_DISCLAIMER = """\
IMPORTANT MEDICAL DISCLAIMERS:
- This tool provides general educational information about hereditary conditions, NOT personalized medical advice, diagnosis, or risk assessment.
- Risk figures cited are population-level estimates from medical databases and do NOT represent any individual's actual risk. Individual risk depends on specific genetic variants, family history details, environmental factors, and other variables only a qualified healthcare provider can evaluate.
- Under GINA (Genetic Information Nondiscrimination Act), genetic information cannot be used for health insurance or employment discrimination in the US. Other protections vary by jurisdiction.
- This is an AI-generated summary and may contain errors. Always consult a qualified healthcare professional or genetic counselor before making medical decisions.
- Data sourced from NIH MedGen, HPO (JAX), and GeneReviews. These databases are curated but not exhaustive and may not reflect the latest research."""

RISK_COMMUNICATION_RULES = """\
RISK COMMUNICATION RULES:
1. NEVER state that a specific person "has X% chance" of a condition. Always frame as population-level or genetic mechanism information.
2. For autosomal dominant conditions, say: "In autosomal dominant inheritance, each child of an affected parent has a 50% probability of inheriting the pathogenic variant." Do NOT say: "You have a 50% chance of getting this disease."
3. For relative risk figures, say: "Population studies show first-degree relatives have approximately X-fold increased relative risk compared to the general population."
4. Always include: "Individual risk depends on specific genetic variants, environmental factors, and family history details. Consult a genetic counselor for personal assessment."
5. When in doubt, err toward educational rather than predictive language."""

HEREDITARY_SEARCH_DISCLAIMER = (
    "This information is for educational purposes only and does not constitute "
    "medical advice, diagnosis, or individual risk assessment. Consult a qualified "
    "healthcare professional or genetic counselor for personal medical guidance."
)


# ── Cosine similarity ─────────────────────────────────────────────────────


def _cosine_similarity(query_vec: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a query vector and a matrix of embeddings.

    Args:
        query_vec: Shape (dim,)
        embeddings: Shape (n, dim)

    Returns:
        Shape (n,) similarity scores
    """
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    emb_norms = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
    return emb_norms @ query_norm


# ── Reference string formatting ────────────────────────────────────────────


def _format_condition_entry(cond: HereditaryCondition) -> str:
    """Format a single condition into a reference string line."""
    inheritance_str = ", ".join(cond.inheritance_modes)
    features_str = ", ".join(cond.clinical_features[:15]) if cond.clinical_features else "see definition"
    sources_str = ", ".join(cond.sources)

    # Build inheritance description based on mode
    inheritance_desc = _build_inheritance_description(cond.inheritance_modes)

    line = f"- {cond.title} ({inheritance_str}) [MedGen:{cond.cui}]: Look for [{features_str}]."
    if inheritance_desc:
        line += f" {inheritance_desc}"
    line += f" Sources: {sources_str}."
    return line


def _build_inheritance_description(modes: tuple[str, ...]) -> str:
    """Build an FDA-compliant educational description of the inheritance pattern."""
    parts: list[str] = []
    for mode in modes:
        if mode == "autosomal dominant":
            parts.append(
                "In autosomal dominant inheritance, each child of an affected "
                "individual has a 50% probability of inheriting the pathogenic variant."
            )
        elif mode == "autosomal recessive":
            parts.append(
                "In autosomal recessive inheritance, when both parents are carriers, "
                "each child has a 25% probability of being affected."
            )
        elif mode == "X-linked dominant":
            parts.append(
                "In X-linked dominant inheritance, an affected parent can pass the "
                "variant to children with different probabilities depending on the "
                "sex of the parent and child."
            )
        elif mode == "X-linked recessive":
            parts.append(
                "In X-linked recessive inheritance, carrier females have a 50% "
                "probability of passing the variant to each son."
            )
        elif mode == "mitochondrial":
            parts.append(
                "Mitochondrial inheritance is maternally transmitted — all children "
                "of an affected mother may inherit the variant."
            )
        elif mode in ("multifactorial", "polygenic"):
            parts.append(
                "This condition has multifactorial inheritance — risk is influenced "
                "by multiple genetic and environmental factors."
            )
    return " ".join(parts)


def _format_header(
    total_conditions: int,
    shown_count: int,
    last_sync: str | None,
) -> str:
    """Format the reference header with source attribution."""
    last_sync_display = last_sync[:10] if last_sync else "unknown"
    return (
        f"Hereditary Conditions Reference (data from NIH MedGen, HPO, GeneReviews): "
        f"Last updated: {last_sync_display} | "
        f"Conditions in database: {total_conditions} | "
        f"Showing {shown_count} most relevant to your query."
    )


# ── Main entry point ──────────────────────────────────────────────────────


def build_relevant_reference(
    query_vector: np.ndarray | None = None,
    query_text: str = "",
    max_conditions: int | None = None,
) -> str:
    """Build a hereditary conditions reference string filtered by query relevance.

    Loads the cached conditions and embeddings, computes cosine similarity
    with the query vector, and returns a formatted reference string with
    the top-N most relevant conditions plus disclaimers.

    If no cache exists, falls back to build_fallback_reference().

    Args:
        query_vector: Already-computed query embedding (dim,). None if unavailable.
        query_text: Original query text (used as fallback signal).
        max_conditions: Max conditions to include (default from settings).

    Returns:
        Formatted reference string for injection into the LLM system prompt.
    """
    max_n = max_conditions or settings.hereditary_max_conditions_in_prompt

    # Load cache
    conditions = load_cache()
    embeddings = load_embeddings()

    if not conditions or embeddings is None:
        # No cache — use hardcoded fallback
        print("[medrag:matcher] No cached hereditary data, using fallback conditions")
        return build_fallback_reference()

    # Ensure embeddings and conditions align
    if len(conditions) != embeddings.shape[0]:
        print(
            f"[medrag:matcher] Mismatch: {len(conditions)} conditions vs "
            f"{embeddings.shape[0]} embeddings. Using fallback."
        )
        return build_fallback_reference()

    # Filter by relevance if query vector is available
    if query_vector is not None and query_vector.shape[0] == embeddings.shape[1]:
        similarities = _cosine_similarity(query_vector, embeddings)
        # Get top-N indices
        top_indices = np.argsort(similarities)[::-1][:max_n]
        selected = [conditions[i] for i in top_indices]
    else:
        # No query vector or dimension mismatch — take first N conditions
        selected = conditions[:max_n]

    # Format output
    meta = cache_metadata()
    lines = [_format_header(
        total_conditions=len(conditions),
        shown_count=len(selected),
        last_sync=meta.get("last_sync"),
    )]

    for cond in selected:
        lines.append(_format_condition_entry(cond))

    # Append disclaimers
    lines.append("")
    lines.append(MEDICAL_DISCLAIMER)
    lines.append("")
    lines.append(RISK_COMMUNICATION_RULES)

    return "\n".join(lines)


def build_fallback_reference() -> str:
    """Build a reference string from the hardcoded FALLBACK_CONDITIONS.

    Used when no cache exists (before first sync) or if cache is corrupted.
    All language has been reframed for FDA compliance.
    """
    from medrag.synthesis.hereditary import FALLBACK_CONDITIONS

    lines = [
        "Hereditary Conditions Reference (fallback — hardcoded data, not from medical database):",
        f"Showing {len(FALLBACK_CONDITIONS)} conditions.",
        "Run 'medrag sync-hereditary' to load real data from NIH MedGen.",
        "",
    ]

    for entry in FALLBACK_CONDITIONS:
        markers_str = ", ".join(entry["markers"])
        inheritance_desc = entry.get("inheritance_description", entry["inheritance"])
        risk_note = entry.get("risk_note_educational", entry.get("risk_note", ""))
        lines.append(
            f"- {entry['condition']} ({entry['inheritance']}): "
            f"Look for [{markers_str}]. {inheritance_desc} {risk_note}"
        )

    # Append disclaimers
    lines.append("")
    lines.append(MEDICAL_DISCLAIMER)
    lines.append("")
    lines.append(RISK_COMMUNICATION_RULES)

    return "\n".join(lines)