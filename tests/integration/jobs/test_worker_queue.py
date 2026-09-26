"""Integration tests for background job queue and async worker daemon."""

import pytest
import shutil

from medrag.domain.patient import PatientId
from medrag.infrastructure.ingestion.fhir_parser import FHIRParser
from medrag.infrastructure.jobs.job_queue import MemoryJobQueue
from medrag.infrastructure.jobs.worker import AsyncWorkerDaemon
from medrag.infrastructure.storage.lancedb_store import LanceDBVectorStore
from medrag.infrastructure.storage.timeline_repo import LanceDBTimelineRepository


@pytest.fixture
def worker_environment(tmp_path):
    """Fixture providing isolated storage, queue, and worker daemon."""
    db_dir = str(tmp_path / "worker_db")
    queue = MemoryJobQueue()
    timeline_repo = LanceDBTimelineRepository(db_uri=db_dir)
    vector_store = LanceDBVectorStore(db_uri=db_dir, embedding_dim=128)
    worker = AsyncWorkerDaemon(
        job_queue=queue,
        timeline_repo=timeline_repo,
        vector_store=vector_store,
        fhir_parser=FHIRParser(),
    )
    yield queue, timeline_repo, vector_store, worker
    shutil.rmtree(db_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_job_queue_idempotency_and_locking(worker_environment):
    """Job queue enforces idempotency deduplication and distributed locks."""
    queue, _, _, _ = worker_environment

    payload = {"patient_id": "pat-100", "data": "test"}
    job_id_1 = await queue.enqueue(
        "FHIR_BUNDLE_INGEST", payload, tenant_id="tenant-1", idempotency_key="key-unique-123"
    )
    # Mark completed
    await queue.update_job(job_id_1, status="COMPLETED")

    # Second enqueue with same key must return existing job ID without creating a duplicate
    job_id_2 = await queue.enqueue(
        "FHIR_BUNDLE_INGEST", payload, tenant_id="tenant-1", idempotency_key="key-unique-123"
    )
    assert job_id_1 == job_id_2

    # Distributed lock testing
    lock_key = "lock:patient:pat-100"
    acquired1 = await queue.acquire_lock(lock_key, ttl_seconds=5.0)
    assert acquired1 is True

    # Concurrent attempt to acquire same lock must fail
    acquired2 = await queue.acquire_lock(lock_key, ttl_seconds=5.0)
    assert acquired2 is False

    # Release lock
    await queue.release_lock(lock_key)
    acquired3 = await queue.acquire_lock(lock_key, ttl_seconds=5.0)
    assert acquired3 is True


@pytest.mark.asyncio
async def test_worker_executes_fhir_bundle_ingest(worker_environment):
    """Worker daemon processes FHIR bundle and persists timeline to LanceDB repository."""
    queue, timeline_repo, _, worker = worker_environment

    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "pat-async-99",
                    "gender": "female",
                    "birthDate": "1980-01-01",
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "id": "enc-async-1",
                    "period": {"start": "2024-03-15T09:00:00Z"},
                    "reasonCode": [{"text": "Emergency consult"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-k-1",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "2823-3"}], "text": "Potassium"},
                    "valueQuantity": {"value": 6.8, "unit": "mmol/L"},
                    "referenceRange": [{"low": {"value": 3.5}, "high": {"value": 5.1}}],
                    "interpretation": [{"coding": [{"code": "HH"}]}],
                    "encounter": {"reference": "Encounter/enc-async-1"},
                }
            },
        ],
    }

    job_id = await queue.enqueue(
        "FHIR_BUNDLE_INGEST",
        {"bundle_json": bundle, "clinic_id": "clinic-er"},
        tenant_id="tenant-mayo",
    )

    # Worker executes job
    result = await worker.execute_job(job_id)
    assert result["status"] == "COMPLETED"
    assert result["result"]["patient_id"] == "pat-async-99"

    # Verify timeline is now present in LanceDB repository
    timeline = await timeline_repo.get_timeline("tenant-mayo", PatientId("pat-async-99"))
    assert timeline is not None
    assert timeline.encounter_count() == 1
    assert len(timeline.encounters[0].observations) == 1
    assert timeline.encounters[0].observations[0].code_loinc == "2823-3"
    assert timeline.encounters[0].observations[0].numeric_value == 6.8
