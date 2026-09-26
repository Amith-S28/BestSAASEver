"""Pure domain models for clinical queries, synthesis requests, and streaming chunks.

ZERO external dependencies. Standard library only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class ClinicalQuery:
    query_id: str
    tenant_id: str
    clinic_id: str
    query_text: str
    asked_by_user_id: str
    asked_at: datetime
    patient_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.query_text or not self.query_text.strip():
            raise ValueError("Query text cannot be empty or whitespace")


@dataclass(frozen=True)
class SynthesisRequest:
    query: ClinicalQuery
    retrieved_evidence: List[str]
    patient_context: Optional[str] = None
    max_tokens: int = 4096
    stream: bool = True
    system_prompt: Optional[str] = None


@dataclass(frozen=True)
class StreamChunk:
    chunk_index: int
    text: str
    is_final: bool = False
    token_count: int = 1
