"""Chief Medical Officer (CMO) human-in-the-loop verification override workflow."""

from typing import List, Optional
from medrag.domain.citation import (
    VerificationStatus,
    VerifiedClinicalReport,
    VerifiedFootnote,
)
from medrag.domain.exceptions import UnverifiedClinicalClaimException


class CMOOverrideWorkflow:
    """Manages clinician and CMO human-in-the-loop claim overrides (Amendment 6)."""

    ALLOWED_REASONS = {
        "clinical_judgment",
        "institutional_protocol",
        "recent_literature",
    }

    def apply_override(
        self,
        report: VerifiedClinicalReport,
        claim_id: str,
        user_id: str,
        reason: str,
        justification: Optional[str] = None,
    ) -> VerifiedClinicalReport:
        """Apply a CMO manual override to an UNCERTAIN or UNGROUNDED claim.

        CONTRADICTED claims cannot be overridden via this workflow (four-eyes principle required).
        """
        if reason not in self.ALLOWED_REASONS:
            raise ValueError(f"Invalid override reason '{reason}'. Allowed: {self.ALLOWED_REASONS}")

        updated_footnotes: List[VerifiedFootnote] = []
        target_found = False

        for fn in report.verified_footnotes:
            if fn.claim.claim_id == claim_id:
                target_found = True
                if fn.status == VerificationStatus.CONTRADICTED:
                    raise UnverifiedClinicalClaimException(
                        claim_text=fn.claim.sentence_text,
                        contradiction_score=fn.contradiction_score,
                    )

                # Construct new overridden footnote
                new_fn = VerifiedFootnote(
                    claim=fn.claim,
                    status=fn.status,
                    entailment_score=fn.entailment_score,
                    contradiction_score=fn.contradiction_score,
                    supporting_excerpt=fn.supporting_excerpt,
                    source_document=fn.source_document,
                    source_page_or_section=fn.source_page_or_section,
                    manual_override=True,
                    override_reason=reason,
                    override_by_user_id=user_id,
                )
                updated_footnotes.append(new_fn)
            else:
                updated_footnotes.append(fn)

        if not target_found:
            raise ValueError(f"Claim ID '{claim_id}' not found in report")

        # Recompute faithfulness
        verified_count = sum(
            1 for fn in updated_footnotes
            if fn.status == VerificationStatus.VERIFIED or fn.manual_override
        )
        total = len(updated_footnotes)
        faithfulness = (verified_count / total) if total > 0 else 1.0

        return VerifiedClinicalReport(
            query_text=report.query_text,
            raw_synthesis=report.raw_synthesis,
            verified_footnotes=updated_footnotes,
            redacted_claim_count=report.redacted_claim_count,
            overall_faithfulness=float(faithfulness),
        )
