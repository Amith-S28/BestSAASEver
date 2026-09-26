"""Unit tests for typed clinical exception hierarchy."""

from medrag.domain.exceptions import (
    ChunkNotFoundException,
    ClinicalException,
    IngestionCorruptedException,
    InsufficientScopeException,
    InvalidFHIRResourceException,
    ModelUnavailableException,
    PatientNotFoundException,
    QuotaExceededException,
    TenantIsolationViolationException,
    UnverifiedClinicalClaimException,
)


def test_exception_status_codes_and_payloads():
    """All domain exceptions inherit from ClinicalException with structured error details."""
    exc1 = PatientNotFoundException("pat-999")
    assert isinstance(exc1, ClinicalException)
    assert exc1.status_code == 404
    assert exc1.error_code == "PATIENT_NOT_FOUND"
    assert exc1.details["patient_id"] == "pat-999"

    exc2 = TenantIsolationViolationException("tenant-compromised")
    assert exc2.status_code == 403
    assert exc2.error_code == "TENANT_ISOLATION_VIOLATION"

    exc3 = IngestionCorruptedException("labs.pdf", "corrupted table boundaries", "Bundle.entry[3]")
    assert exc3.status_code == 400
    assert exc3.details["json_path"] == "Bundle.entry[3]"

    exc4 = UnverifiedClinicalClaimException("Contraindicated drug dosage", 0.92)
    assert exc4.status_code == 422
    assert exc4.error_code == "CLAIM_CONTRADICTED"
    assert exc4.details["contradiction_score"] == 0.92

    exc5 = QuotaExceededException("tenant-mayo", "query", 5000)
    assert exc5.status_code == 429
    assert exc5.error_code == "QUOTA_EXCEEDED"

    exc6 = ModelUnavailableException("Qwen-32B", "Connection refused")
    assert exc6.status_code == 503
    assert exc6.error_code == "MODEL_UNAVAILABLE"
