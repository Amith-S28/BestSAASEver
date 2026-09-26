"""Unit tests for CMO override workflow."""

import pytest
from medrag.application.services.cmo_override import CMOOverrideWorkflow
from medrag.domain.citation import (
    ClinicalClaim,
    VerificationStatus,
    VerifiedClinicalReport,
    VerifiedFootnote,
)
from medrag.domain.exceptions import UnverifiedClinicalClaimException


def test_cmo_override_uncertain_claim():
    """CMO override successfully updates UNCERTAIN claim to safe status."""
    claim = ClinicalClaim("clm-1", "Adjust dosage per hospital protocol", 0, ["chk-1"])
    fn = VerifiedFootnote(
        claim=claim,
        status=VerificationStatus.UNCERTAIN,
        entailment_score=0.62,
        contradiction_score=0.10,
        supporting_excerpt=None,
        source_document="Hospital Guidelines",
        source_page_or_section="P&T Protocol",
    )

    report = VerifiedClinicalReport(
        query_text="Dosage review",
        raw_synthesis="Adjust dosage per hospital protocol",
        verified_footnotes=[fn],
        redacted_claim_count=0,
        overall_faithfulness=0.0,
    )

    workflow = CMOOverrideWorkflow()
    overridden_report = workflow.apply_override(
        report=report,
        claim_id="clm-1",
        user_id="cmo-dr-vance",
        reason="clinical_judgment",
        justification="Verified against internal P&T nephrology standard",
    )

    assert overridden_report.overall_faithfulness == 1.0
    overridden_fn = overridden_report.verified_footnotes[0]
    assert overridden_fn.manual_override is True
    assert overridden_fn.override_by_user_id == "cmo-dr-vance"
    assert overridden_fn.is_safe_to_display()


def test_cmo_override_contradicted_claim_forbidden():
    """Attempting to override a CONTRADICTED claim raises UnverifiedClinicalClaimException."""
    claim = ClinicalClaim("clm-contra", "Contradicted statement", 0, ["chk-1"])
    fn_contra = VerifiedFootnote(
        claim=claim,
        status=VerificationStatus.CONTRADICTED,
        entailment_score=0.05,
        contradiction_score=0.90,
        supporting_excerpt="Contradicting evidence excerpt",
        source_document="Harrison's",
        source_page_or_section="p. 100",
    )

    report = VerifiedClinicalReport(
        query_text="Check",
        raw_synthesis="Contradicted statement",
        verified_footnotes=[fn_contra],
        redacted_claim_count=1,
        overall_faithfulness=0.0,
    )

    workflow = CMOOverrideWorkflow()
    with pytest.raises(UnverifiedClinicalClaimException):
        workflow.apply_override(
            report=report,
            claim_id="clm-contra",
            user_id="cmo-dr-vance",
            reason="clinical_judgment",
        )
