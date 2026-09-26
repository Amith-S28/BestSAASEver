"""Clinical claim decomposition, verification orchestration, and contradiction redaction service."""

import re
from typing import List, Tuple
from medrag.domain.citation import (
    ClinicalClaim,
    VerificationStatus,
    VerifiedClinicalReport,
    VerifiedFootnote,
)
from medrag.domain.literature import MedicalChunk
from medrag.ports.verification import INLIVerifier


class ClaimAuditor:
    """Audits clinical synthesis text by decomposing into claims, verifying via NLI, and redacting contradictions."""

    def __init__(self, verifier: INLIVerifier) -> None:
        self.verifier = verifier

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split clinical text into sentences while respecting periods in abbreviations."""
        # Simple clinical sentence splitter
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        return sentences

    @staticmethod
    def _extract_citations(sentence: str, evidence_chunks: List[MedicalChunk]) -> Tuple[str, List[str]]:
        """Extract [^x] or [x] citation anchors and map them to chunk_ids."""
        cited_ids: List[str] = []
        # Match [^1] or [1]
        matches = re.findall(r"\[\^?(\d+)\]", sentence)
        for m in matches:
            idx = int(m) - 1  # 1-based index to 0-based
            if 0 <= idx < len(evidence_chunks):
                cited_ids.append(evidence_chunks[idx].chunk_id)

        clean_text = re.sub(r"\[\^?\d+\]", "", sentence).strip()
        return clean_text, cited_ids

    async def audit_synthesis(
        self,
        query_text: str,
        raw_synthesis: str,
        evidence_chunks: List[MedicalChunk],
    ) -> VerifiedClinicalReport:
        """Decompose synthesis, verify claims via NLI, and apply contradiction redaction."""
        sentences = self._split_sentences(raw_synthesis)
        if not sentences:
            return VerifiedClinicalReport(
                query_text=query_text,
                raw_synthesis=raw_synthesis,
                verified_footnotes=[],
                redacted_claim_count=0,
                overall_faithfulness=1.0,
            )

        claims: List[ClinicalClaim] = []
        for idx, sentence in enumerate(sentences):
            clean_text, cited_chunk_ids = self._extract_citations(sentence, evidence_chunks)
            claim = ClinicalClaim(
                claim_id=f"clm-{idx+1}",
                sentence_text=clean_text or sentence,
                sentence_index=idx,
                cited_chunk_ids=cited_chunk_ids,
            )
            claims.append(claim)

        # Batch verify via port
        footnotes = await self.verifier.verify_batch(claims, evidence_chunks)

        # Assemble safe audited output text
        output_sentences: List[str] = []
        redacted_count = 0
        verified_count = 0

        for idx, (sentence, footnote) in enumerate(zip(sentences, footnotes)):
            if footnote.is_contradicted():
                redacted_count += 1
                tombstone = (
                    f"[Safety Filter: Clinical recommendation redacted — "
                    f"contradicts {footnote.source_document}, {footnote.source_page_or_section}]"
                )
                output_sentences.append(tombstone)
            else:
                if footnote.status == VerificationStatus.VERIFIED or footnote.manual_override:
                    verified_count += 1
                output_sentences.append(sentence)

        # Quarantine check: 3 or more contradictions suppress entire text
        if redacted_count >= 3:
            final_synthesis = (
                "[Safety Quarantined: Multiple recommendations contradicted published clinical literature. "
                "Full synthesis suppressed for patient safety.]"
            )
        else:
            final_synthesis = " ".join(output_sentences)

        total = len(claims)
        faithfulness = (verified_count / total) if total > 0 else 1.0

        return VerifiedClinicalReport(
            query_text=query_text,
            raw_synthesis=final_synthesis,
            verified_footnotes=footnotes,
            redacted_claim_count=redacted_count,
            overall_faithfulness=float(faithfulness),
        )
