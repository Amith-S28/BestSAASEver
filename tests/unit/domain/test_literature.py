"""Unit tests for medical literature domain models."""

from datetime import datetime
import pytest

from medrag.domain.literature import (
    DocumentId,
    MedicalBook,
    MedicalChunk,
    RetrievedEvidence,
)


def test_document_id_validation():
    """DocumentId enforces non-empty invariant."""
    doc_id = DocumentId("doc-harrisons-21")
    assert doc_id.value == "doc-harrisons-21"

    with pytest.raises(ValueError):
        DocumentId("")

    with pytest.raises(ValueError):
        DocumentId("   ")


def test_medical_chunk_creation():
    """MedicalChunk initializes with license tier and ontology codes."""
    chunk = MedicalChunk(
        chunk_id="chk-001",
        document_id="doc-harrisons",
        title="Harrison's Internal Medicine",
        chapter="Chapter 308: Acute Kidney Injury",
        page_number=2112,
        text_content="Creatinine elevation defines acute kidney injury.",
        specialty="Nephrology",
        snomed_codes=["14669001"],
        rxnorm_codes=[],
        loinc_codes=["2160-0"],
        ingested_at=datetime(2025, 1, 1),
        corpus_license_tier="tier1_open",
    )
    assert chunk.specialty == "Nephrology"
    assert chunk.corpus_license_tier == "tier1_open"
    assert "14669001" in chunk.snomed_codes


def test_retrieved_evidence_scoring():
    """RetrievedEvidence maintains composite ranking scores."""
    chunk = MedicalChunk(
        chunk_id="chk-002",
        document_id="doc-guyton",
        title="Guyton Medical Physiology",
        chapter="Chapter 26",
        page_number=341,
        text_content="Renal blood flow regulation.",
        specialty="Physiology",
    )
    evidence = RetrievedEvidence(
        chunk=chunk,
        vector_score=0.88,
        bm25_score=14.5,
        rrf_score=0.032,
        reranker_score=0.95,
    )
    assert evidence.vector_score == 0.88
    assert evidence.reranker_score == 0.95
