"""Background job queue adapter implementing medrag.ports.jobs.IJobQueue with distributed locks."""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional
import uuid


class MemoryJobQueue:
    """In-process async background job queue with idempotency tracking and distributed locking."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> job_id
        self._locks: Dict[str, float] = {}          # lock_key -> expire_timestamp
        self._lock_mutex = asyncio.Lock()

    async def acquire_lock(self, lock_key: str, ttl_seconds: float = 30.0) -> bool:
        """Acquire a distributed lock with TTL expiration."""
        async with self._lock_mutex:
            now = datetime.now(timezone.utc).timestamp()
            # Check if held and not expired
            if lock_key in self._locks:
                if now < self._locks[lock_key]:
                    return False  # Lock held
            # Acquire lock
            self._locks[lock_key] = now + ttl_seconds
            return True

    async def release_lock(self, lock_key: str) -> None:
        """Release a distributed lock."""
        async with self._lock_mutex:
            self._locks.pop(lock_key, None)

    async def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        tenant_id: str,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Enqueue a background job with idempotency deduplication."""
        if not idempotency_key:
            # Generate deterministic hash from payload
            serialized = json.dumps(payload, sort_keys=True)
            idempotency_key = f"tenant:{tenant_id}:{job_type}:{hashlib.sha256(serialized.encode()).hexdigest()}"

        # Check existing idempotency record
        if idempotency_key in self._idempotency_map:
            existing_job_id = self._idempotency_map[idempotency_key]
            existing_job = self._jobs.get(existing_job_id)
            if existing_job and existing_job["status"] in ("COMPLETED", "PROCESSING"):
                return existing_job_id

        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        job_record = {
            "job_id": job_id,
            "job_type": job_type,
            "tenant_id": tenant_id,
            "idempotency_key": idempotency_key,
            "status": "QUEUED",
            "payload": payload,
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
        }

        self._jobs[job_id] = job_record
        self._idempotency_map[idempotency_key] = job_id
        return job_id

    async def get_status(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job execution status."""
        job = self._jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "status": "NOT_FOUND"}
        return job

    async def update_job(
        self,
        job_id: str,
        status: str,
        progress: float = 0.0,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update job execution state."""
        if job_id in self._jobs:
            now = datetime.now(timezone.utc).isoformat()
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["progress"] = progress
            self._jobs[job_id]["result"] = result
            self._jobs[job_id]["error"] = error
            self._jobs[job_id]["updated_at"] = now
