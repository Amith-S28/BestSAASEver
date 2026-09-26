"""Pure domain exceptions for MedRAG v2.0.

ZERO external dependencies. Standard library only.
All application and domain errors inherit from ClinicalException.
"""

from typing import Any, Dict, Optional


class ClinicalException(Exception):
    """Base exception for all MedRAG clinical intelligence errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details: Dict[str, Any] = details or {}


class PatientNotFoundException(ClinicalException):
    """Raised when a queried patient ID does not exist within the tenant partition."""

    def __init__(self, patient_id: str) -> None:
        super().__init__(
            error_code="PATIENT_NOT_FOUND",
            message=f"Patient '{patient_id}' not found in active clinic",
            status_code=404,
            details={"patient_id": patient_id},
        )


class ChunkNotFoundException(ClinicalException):
    """Raised when an evidence citation references a non-existent chunk ID."""

    def __init__(self, chunk_id: str) -> None:
        super().__init__(
            error_code="CHUNK_NOT_FOUND",
            message=f"Evidence chunk '{chunk_id}' not found",
            status_code=404,
            details={"chunk_id": chunk_id},
        )


class IngestionCorruptedException(ClinicalException):
    """Raised when an uploaded FHIR bundle or lab PDF cannot be structurally parsed."""

    def __init__(
        self, filename: str, reason: str, json_path: Optional[str] = None
    ) -> None:
        super().__init__(
            error_code="INGESTION_CORRUPTED",
            message=f"Failed to ingest clinical file '{filename}': {reason}",
            status_code=400,
            details={"filename": filename, "reason": reason, "json_path": json_path},
        )


class InvalidFHIRResourceException(ClinicalException):
    """Raised when a specific FHIR R4 resource violates required structural invariants."""

    def __init__(self, resource_type: str, field: str, reason: str) -> None:
        super().__init__(
            error_code="INVALID_FHIR_RESOURCE",
            message=f"Invalid FHIR resource {resource_type}.{field}: {reason}",
            status_code=400,
            details={"resource_type": resource_type, "field": field, "reason": reason},
        )


class TenantIsolationViolationException(ClinicalException):
    """Raised when a query or write violates tenant cryptographic boundary isolation."""

    def __init__(self, tenant_id: str) -> None:
        super().__init__(
            error_code="TENANT_ISOLATION_VIOLATION",
            message="Cross-tenant access blocked by security isolation boundary",
            status_code=403,
            details={"attempted_tenant": tenant_id},
        )


class InsufficientScopeException(ClinicalException):
    """Raised when an authenticated actor lacks the required RBAC scope for an action."""

    def __init__(self, required_scope: str, available_scopes: list[str]) -> None:
        super().__init__(
            error_code="INSUFFICIENT_SCOPE",
            message=f"Access denied: missing required scope '{required_scope}'",
            status_code=403,
            details={"required_scope": required_scope, "available_scopes": available_scopes},
        )


class UnverifiedClinicalClaimException(ClinicalException):
    """Raised when a clinical output contains high-confidence contradictions with literature."""

    def __init__(self, claim_text: str, contradiction_score: float) -> None:
        super().__init__(
            error_code="CLAIM_CONTRADICTED",
            message="Clinical recommendation contradicted by published medical literature",
            status_code=422,
            details={"claim_text": claim_text, "contradiction_score": contradiction_score},
        )


class QuotaExceededException(ClinicalException):
    """Raised when a tenant exhausts its monthly query quota."""

    def __init__(self, tenant_id: str, quota_type: str, limit: int) -> None:
        super().__init__(
            error_code="QUOTA_EXCEEDED",
            message=f"Monthly {quota_type} quota exceeded ({limit}) for tenant '{tenant_id}'",
            status_code=429,
            details={"tenant_id": tenant_id, "quota_type": quota_type, "limit": limit},
        )


class ModelUnavailableException(ClinicalException):
    """Raised when inference serving runtimes (vLLM, LM Studio) are unresponsive."""

    def __init__(self, model_name: str, reason: str) -> None:
        super().__init__(
            error_code="MODEL_UNAVAILABLE",
            message=f"Inference model '{model_name}' unavailable: {reason}",
            status_code=503,
            details={"model_name": model_name, "reason": reason},
        )
