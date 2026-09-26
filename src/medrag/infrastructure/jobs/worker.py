"""Async background worker daemon executing clinical ingestion, indexing, and privacy jobs."""

import asyncio
from typing import Any, Dict, Optional

from medrag.domain.patient import PatientId
from medrag.infrastructure.ingestion.fhir_parser import FHIRParser
from medrag.infrastructure.ingestion.pdf_parser import PDFLabParser
from medrag.infrastructure.jobs.job_queue import MemoryJobQueue
from medrag.infrastructure.storage.lancedb_store import LanceDBVectorStore
from medrag.infrastructure.storage.timeline_repo import LanceDBTimelineRepository


class AsyncWorkerDaemon:
    """Worker daemon executing background tasks from the queue."""

    def __init__(
        self,
        job_queue: MemoryJobQueue,
        timeline_repo: LanceDBTimelineRepository,
        vector_store: LanceDBVectorStore,
        fhir_parser: Optional[FHIRParser] = None,
        pdf_parser: Optional[PDFLabParser] = None,
    ) -> None:
        self.job_queue = job_queue
        self.timeline_repo = timeline_repo
        self.vector_store = vector_store
        self.fhir_parser = fhir_parser or FHIRParser()
        self.pdf_parser = pdf_parser or PDFLabParser()

    async def execute_job(self, job_id: str) -> Dict[str, Any]:
        """Execute a single job by job_id."""
        job = await self.job_queue.get_status(job_id)
        if job.get("status") == "NOT_FOUND":
            return {"error": "Job not found"}

        job_type = job["job_type"]
        tenant_id = job["tenant_id"]
        payload = job["payload"]

        await self.job_queue.update_job(job_id, status="PROCESSING", progress=0.1)

        try:
            # 1. FHIR_BUNDLE_INGEST
            if job_type == "FHIR_BUNDLE_INGEST":
                bundle_json = payload["bundle_json"]
                clinic_id = payload.get("clinic_id", "default_clinic")
                temp_timeline = self.fhir_parser.parse_bundle(bundle_json, tenant_id, clinic_id)
                pid = temp_timeline.patient_id.value

                # Acquire distributed lock
                lock_key = f"lock:tenant:{tenant_id}:patient:{pid}"
                acquired = await self.job_queue.acquire_lock(lock_key, ttl_seconds=30.0)
                if not acquired:
                    raise RuntimeError(f"Could not acquire lock for patient {pid}")

                try:
                    # Check existing timeline for merge
                    existing = await self.timeline_repo.get_timeline(tenant_id, PatientId(pid))
                    if existing:
                        final_timeline = self.fhir_parser.merge_timelines(existing, temp_timeline)
                    else:
                        final_timeline = temp_timeline

                    await self.timeline_repo.save_timeline(final_timeline)
                    result = {
                        "patient_id": pid,
                        "encounter_count": final_timeline.encounter_count(),
                        "status": "INGESTED",
                    }
                finally:
                    await self.job_queue.release_lock(lock_key)

            # 2. PDF_LAB_INGEST
            elif job_type == "PDF_LAB_INGEST":
                pdf_path = payload["pdf_path"]
                observations, confidence = await self.pdf_parser.parse_pdf(pdf_path)
                result = {
                    "observations_extracted": len(observations),
                    "parse_confidence": confidence,
                    "status": "PARSED",
                }

            # 3. PATIENT_DELETE (HIPAA Right to Erasure)
            elif job_type == "PATIENT_DELETE":
                pid = payload["patient_id"]
                deleted = await self.timeline_repo.delete_patient(tenant_id, PatientId(pid))
                result = {"patient_id": pid, "deleted": deleted}

            # 4. CORPUS_REINDEX
            elif job_type == "CORPUS_REINDEX":
                chunks = payload.get("chunks", [])
                inserted = await self.vector_store.insert_chunks(tenant_id, chunks)
                result = {"chunks_indexed": inserted}

            else:
                result = {"status": "NOOP", "job_type": job_type}

            await self.job_queue.update_job(job_id, status="COMPLETED", progress=1.0, result=result)
            return {"job_id": job_id, "status": "COMPLETED", "result": result}

        except Exception as e:
            await self.job_queue.update_job(job_id, status="FAILED", progress=0.0, error=str(e))
            return {"job_id": job_id, "status": "FAILED", "error": str(e)}
