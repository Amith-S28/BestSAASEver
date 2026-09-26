"""Port protocol for hybrid storage and patient timeline repositories."""

from typing import List, Optional, Protocol
from medrag.domain.literature import MedicalChunk, RetrievedEvidence
from medrag.domain.patient import PatientId, PatientTimeline


class IVectorStore(Protocol):
    """Abstract interface for hybrid vector + BM25 literature search."""

    async def query_hybrid(
        self,
        tenant_id: str,
        query_vector: List[float],
        query_text: str,
        snomed_filters: Optional[List[str]] = None,
        rxnorm_filters: Optional[List[str]] = None,
        top_k: int = 25,
    ) -> List[RetrievedEvidence]:
        """Hybrid vector cosine + BM25 search with tenant scoping and RRF fusion."""
        ...

    async def insert_chunks(self, tenant_id: str, chunks: List[MedicalChunk]) -> int:
        """Batch insert Apache Arrow backed vectors with metadata."""
        ...

    async def delete_by_tenant(self, tenant_id: str) -> int:
        """Purge all data for a tenant (right to erasure)."""
        ...

    async def count_chunks(self, tenant_id: str) -> int:
        """Count total indexed chunks for quota enforcement."""
        ...


class ITimelineRepository(Protocol):
    """Abstract interface for patient encounter timeline storage."""

    async def save_timeline(self, timeline: PatientTimeline) -> None:
        """Atomically persist or update a patient timeline."""
        ...

    async def get_timeline(self, tenant_id: str, patient_id: PatientId) -> Optional[PatientTimeline]:
        """Retrieve patient timeline scoped to tenant."""
        ...

    async def delete_patient(self, tenant_id: str, patient_id: PatientId) -> bool:
        """Permanently purge a patient record under HIPAA Right to Erasure."""
        ...

    async def list_patients(
        self, tenant_id: str, clinic_id: str, limit: int = 50, cursor: Optional[str] = None
    ) -> List[PatientTimeline]:
        """Paginated listing of patient timelines within a clinic."""
        ...
