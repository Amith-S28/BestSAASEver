"""Corpus Licensing and Compliance Verification Tool."""

from typing import Any, Dict, List
from medrag.domain.literature import MedicalChunk

VALID_LICENSES = {"tier1_open", "tier2_institutional", "tier3_commercial"}


def audit_chunks_licensing(chunks: List[MedicalChunk]) -> Dict[str, Any]:
    """Audit chunks to ensure every passage carries valid institutional copyright license tier."""
    invalid_count = 0
    tier_counts = {t: 0 for t in VALID_LICENSES}

    for c in chunks:
        if c.corpus_license_tier not in VALID_LICENSES:
            invalid_count += 1
        else:
            tier_counts[c.corpus_license_tier] += 1

    return {
        "total_chunks_scanned": len(chunks),
        "valid_compliance": invalid_count == 0,
        "invalid_license_count": invalid_count,
        "tier_distribution": tier_counts,
    }


if __name__ == "__main__":
    test_chunks = [
        MedicalChunk(
            chunk_id="chk-1",
            document_id="doc-1",
            title="Harrison's Principles",
            chapter="Ch. 12",
            page_number=100,
            text_content="...",
            specialty="Internal Medicine",
            corpus_license_tier="tier1_open",
        ),
        MedicalChunk(
            chunk_id="chk-2",
            document_id="doc-2",
            title="Robbins Pathology",
            chapter="Ch. 5",
            page_number=200,
            text_content="...",
            specialty="Pathology",
            corpus_license_tier="tier2_institutional",
        ),
    ]
    report = audit_chunks_licensing(test_chunks)
    print("Corpus Licensing Audit Report:", report)
