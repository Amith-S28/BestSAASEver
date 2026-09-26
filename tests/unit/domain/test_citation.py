"""Unit tests for citation, verification status, and clinical report domain models."""

import pytest

from medrag.domain.citation import (
    ClinicalClaim,
    VerificationStatus,
    VerifiedClinicalReport,
    VerifiedFootnote,
)


def test_verified_footnote_display_safety():
    """VerifiedFootnote determines safe display based on status and CMO overrides."""
    claim = ClinicalClaim(
        claim_id="clm-1",
        sentence_text="Initiate Lisinopril for chronic kidney disease with proteinuria.",
        sentence_index=0,
        cited_chunk_ids=["chk-001"],
    )

    fn_verified = VerifiedFootnote(
        claim=claim,
        status=VerificationStatus.VERIFIED,
        entailment_score=0.92,
        contradiction_score=0.02,
        supporting_excerpt="ACE inhibitors reduce proteinuria in CKD.",
        source_document="KDIGO Clinical Practice Guideline",
        source_page_or_section="Section 3.1",
    )
    assert fn_verified.is_safe_to_display()
    assert not fn_verified.is_contradicted()

    fn_contradicted = VerifiedFootnote(
        claim=claim,
        status=VerificationStatus.CONTRADICTED,
        entailment_score=0.05,
        contradiction_score=0.89,
        supporting_excerpt="Contraindicated in bilateral renal artery stenosis.",
        source_document="KDIGO Clinical Practice Guideline",
        source_page_or_section="Section 3.4",
    )
    assert not fn_contradicted.is_safe_to_display()
    assert fn_contradicted.is_contradicted()

    # CMO manual override makes uncertain or safe display true
    fn_overridden = VerifiedFootnote(
        claim=claim,
        status=VerificationStatus.UNCERTAIN,
        entailment_score=0.65,
        contradiction_score=0.15,
        supporting_excerpt=None,
        source_document="Hospital Formularies",
        source_page_or_section="P&T Protocol 2025",
        manual_override=True,
        override_reason="clinical_judgment",
        override_by_user_id="cmo-dr-vance",
    )
    assert fn_overridden.is_safe_to_display()
    assert not fn_overridden.is_contradicted()


def test_verified_clinical_report_contradictions():
    """VerifiedClinicalReport accurately detects contradiction presence."""
    claim1 = ClinicalClaim("c1", "Sentence 1", 0)
    claim2 = ClinicalClaim("c2", "Sentence 2", 1)

    fn1 = VerifiedFootnote(
        claim=claim1,
        status=VerificationStatus.VERIFIED,
        entailment_score=0.95,
        contradiction_score=0.01,
        supporting_excerpt="Excerpt 1",
        source_document="Harrison's",
        source_page_or_section="p. 100",
    )
    fn2 = VerifiedFootnote(
        claim=claim2,
        status=VerificationStatus.CONTRADICTED,
        entailment_score=0.05,
        contradiction_score=0.85,
        supporting_excerpt="Contradicting excerpt",
        source_document="Harrison's",
        source_page_or_section="p. 102",
    )

    report_clean = VerifiedClinicalReport(
        query_text="Summarize labs",
        raw_synthesis="Sentence 1",
        verified_footnotes=[fn1],
        redacted_claim_count=0,
        overall_faithfulness=1.0,
    )
    assert not report_clean.has_contradictions()
    assert report_clean.total_claims() == 1

    report_flagged = VerifiedClinicalReport(
        query_text="Summarize labs",
        raw_synthesis="Sentence 1 Sentence 2",
        verified_footnotes=[fn1, fn2],
        redacted_claim_count=1,
        overall_faithfulness=0.5,
    )
    assert report_flagged.has_contradictions()
    assert report_flagged.total_claims() == 2
