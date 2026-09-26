"""Unit tests for claim auditor and contradiction redaction service."""

import pytest
from medrag.application.services.claim_auditor import ClaimAuditor
from medrag.domain.citation import VerificationStatus
from medrag.domain.literature import MedicalChunk
from medrag.infrastructure.models.nli_verifier import DeterministicNLIVerifier


@pytest.fixture
def nephrology_chunk():
    return MedicalChunk(
        chunk_id="chk-neph-1",
        document_id="doc-kdigo",
        title="KDIGO AKI Guidelines",
        chapter="Chapter 3",
        page_number=35,
        text_content="Discontinue Lisinopril promptly in the setting of acute decompensation.",
        specialty="Nephrology",
    )


@pytest.mark.asyncio
async def test_claim_auditor_auto_redaction(nephrology_chunk):
    """ClaimAuditor redacts contradictory sentences with standard safety tombstone."""
    verifier = DeterministicNLIVerifier()
    auditor = ClaimAuditor(verifier=verifier)

    raw_synthesis = (
        "Patient exhibits severe acute kidney injury. "
        "Continue Lisinopril therapy at high doses [^1]. "
        "Hydration is indicated."
    )

    report = await auditor.audit_synthesis(
        query_text="Evaluate Lisinopril therapy in this patient",
        raw_synthesis=raw_synthesis,
        evidence_chunks=[nephrology_chunk],
    )

    assert report.redacted_claim_count == 1
    assert "Safety Filter: Clinical recommendation redacted" in report.raw_synthesis
    assert "Continue Lisinopril therapy at high doses" not in report.raw_synthesis


@pytest.mark.asyncio
async def test_claim_auditor_quarantine_on_multiple_contradictions(nephrology_chunk):
    """Report is quarantined when 3 or more contradictions are detected."""
    verifier = DeterministicNLIVerifier()
    auditor = ClaimAuditor(verifier=verifier)

    raw_synthesis = (
        "Continue Lisinopril therapy at high doses [^1]. "
        "Lisinopril is indicated despite acute kidney injury [^1]. "
        "Lisinopril is recommended without restriction [^1]."
    )

    report = await auditor.audit_synthesis(
        query_text="Assess medication safety",
        raw_synthesis=raw_synthesis,
        evidence_chunks=[nephrology_chunk],
    )

    assert report.redacted_claim_count >= 3
    assert "Safety Quarantined" in report.raw_synthesis
