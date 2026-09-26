"""Pure domain models for clinical claims, citations, and NLI verification.

ZERO external dependencies. Standard library only.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    CONTRADICTED = "contradicted"
    UNGROUNDED = "ungrounded"


@dataclass(frozen=True)
class ClinicalClaim:
    claim_id: str
    sentence_text: str
    sentence_index: int
    cited_chunk_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerifiedFootnote:
    claim: ClinicalClaim
    status: VerificationStatus
    entailment_score: float
    contradiction_score: float
    supporting_excerpt: Optional[str]
    source_document: str
    source_page_or_section: str
    manual_override: bool = False
    override_reason: Optional[str] = None
    override_by_user_id: Optional[str] = None

    def is_safe_to_display(self) -> bool:
        return self.status in (VerificationStatus.VERIFIED, VerificationStatus.UNCERTAIN) or self.manual_override

    def is_contradicted(self) -> bool:
        return self.status == VerificationStatus.CONTRADICTED and not self.manual_override


@dataclass(frozen=True)
class VerifiedClinicalReport:
    query_text: str
    raw_synthesis: str
    verified_footnotes: List[VerifiedFootnote]
    redacted_claim_count: int
    overall_faithfulness: float

    def has_contradictions(self) -> bool:
        return any(f.is_contradicted() for f in self.verified_footnotes)

    def total_claims(self) -> int:
        return len(self.verified_footnotes)
