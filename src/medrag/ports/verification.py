"""Port protocol for Natural Language Inference (NLI) claim verification."""

from typing import List, Protocol
from medrag.domain.citation import ClinicalClaim, VerifiedFootnote
from medrag.domain.literature import MedicalChunk


class INLIVerifier(Protocol):
    """Abstract interface for deterministic claim-to-evidence NLI verification."""

    async def verify_claim(
        self, claim: ClinicalClaim, evidence_chunks: List[MedicalChunk]
    ) -> VerifiedFootnote:
        """Compute entailment probabilities and assign verification status."""
        ...

    async def verify_batch(
        self, claims: List[ClinicalClaim], evidence_chunks: List[MedicalChunk]
    ) -> List[VerifiedFootnote]:
        """Batch NLI verification across multiple claims."""
        ...
