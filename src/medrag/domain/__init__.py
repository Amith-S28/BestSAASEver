"""Pure clinical domain layer for MedRAG v2.0.

ZERO external dependencies. Standard library only.
"""

from .citation import (
    ClinicalClaim,
    VerificationStatus,
    VerifiedClinicalReport,
    VerifiedFootnote,
)
from .exceptions import (
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
from .literature import (
    DocumentId,
    MedicalBook,
    MedicalChunk,
    RetrievedEvidence,
)
from .patient import (
    ClinicId,
    ClinicalEncounter,
    Condition,
    Gender,
    LabObservation,
    MedicationRecord,
    ObservationFlag,
    PatientId,
    PatientTimeline,
    TenantId,
)
from .synthesis import (
    ClinicalQuery,
    StreamChunk,
    SynthesisRequest,
)

__all__ = [
    # Patient
    "Gender",
    "ObservationFlag",
    "PatientId",
    "TenantId",
    "ClinicId",
    "LabObservation",
    "MedicationRecord",
    "Condition",
    "ClinicalEncounter",
    "PatientTimeline",
    # Literature
    "DocumentId",
    "MedicalChunk",
    "MedicalBook",
    "RetrievedEvidence",
    # Citation & Verification
    "VerificationStatus",
    "ClinicalClaim",
    "VerifiedFootnote",
    "VerifiedClinicalReport",
    # Synthesis
    "ClinicalQuery",
    "SynthesisRequest",
    "StreamChunk",
    # Exceptions
    "ClinicalException",
    "PatientNotFoundException",
    "ChunkNotFoundException",
    "IngestionCorruptedException",
    "InvalidFHIRResourceException",
    "TenantIsolationViolationException",
    "InsufficientScopeException",
    "UnverifiedClinicalClaimException",
    "QuotaExceededException",
    "ModelUnavailableException",
]
