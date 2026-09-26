"""Port protocol for asynchronous background job execution and queues."""

from typing import Any, Dict, Optional, Protocol


class IJobQueue(Protocol):
    """Abstract interface for background job enqueueing and supervision."""

    async def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        tenant_id: str,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Enqueue a background task with idempotency protection. Returns job_id."""
        ...

    async def get_status(self, job_id: str) -> Dict[str, Any]:
        """Query execution status, progress, and results of a background job."""
        ...
