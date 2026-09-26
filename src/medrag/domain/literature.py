"""Pure domain models for medical literature chunks and retrieval evidence.

ZERO external dependencies. Standard library only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class DocumentId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("DocumentId cannot be empty or whitespace")


@dataclass(frozen=True)
class MedicalChunk:
    chunk_id: str
    document_id: str
    title: str
    chapter: str
    page_number: int
    text_content: str
    specialty: str
    snomed_codes: List[str] = field(default_factory=list)
    rxnorm_codes: List[str] = field(default_factory=list)
    loinc_codes: List[str] = field(default_factory=list)
    ingested_at: Optional[datetime] = None
    corpus_license_tier: str = "tier1_open"  # tier1_open | tier2_fairuse | tier3_institutional


@dataclass(frozen=True)
class MedicalBook:
    document_id: DocumentId
    title: str
    authors: List[str]
    edition: str
    total_chunks: int


@dataclass(frozen=True)
class RetrievedEvidence:
    chunk: MedicalChunk
    vector_score: float
    bm25_score: float
    rrf_score: float
    reranker_score: Optional[float] = None
