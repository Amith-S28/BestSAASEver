"""Unit tests for synthesis request and query domain models."""

from datetime import datetime, timezone
import pytest

from medrag.domain.synthesis import (
    ClinicalQuery,
    StreamChunk,
    SynthesisRequest,
)


def test_clinical_query_validation():
    """ClinicalQuery enforces non-empty query text."""
    query = ClinicalQuery(
        query_id="qry-001",
        tenant_id="tenant-mayo",
        clinic_id="clinic-cardio",
        patient_id="pat-100",
        query_text="Evaluate ejection fraction trajectory",
        asked_by_user_id="usr-123",
        asked_at=datetime.now(timezone.utc),
    )
    assert query.query_id == "qry-001"
    assert query.patient_id == "pat-100"

    with pytest.raises(ValueError, match="Query text cannot be empty"):
        ClinicalQuery(
            query_id="qry-002",
            tenant_id="tenant-mayo",
            clinic_id="clinic-cardio",
            query_text="",
            asked_by_user_id="usr-123",
            asked_at=datetime.now(timezone.utc),
        )


def test_stream_chunk_monotonicity():
    """StreamChunk tracks index and final token status."""
    chunk1 = StreamChunk(chunk_index=0, text="Patient shows", is_final=False)
    chunk2 = StreamChunk(chunk_index=1, text=" improvement.", is_final=True)

    assert chunk1.chunk_index == 0
    assert not chunk1.is_final
    assert chunk2.is_final
