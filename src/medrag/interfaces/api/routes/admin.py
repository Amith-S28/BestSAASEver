"""Admin Console, Audit Trail, and Tenant Usage API routes."""

from typing import Optional
from fastapi import APIRouter, Depends
from medrag.interfaces.api.dependencies import (
    assert_tenant_boundary,
    get_services,
    require_scope,
)
from medrag.ports.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1", tags=["Admin & Audit"])


@router.get("/admin/tenants/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: str,
    user: AuthenticatedUser = Depends(require_scope("tenant:manage")),
):
    """Retrieve tenant quota consumption and active stream metrics."""
    assert_tenant_boundary(user, tenant_id)
    services = get_services()
    stats = services.rate_limiter.get_tenant_usage(tenant_id)
    return {
        "tenant_id": tenant_id,
        **stats,
    }


@router.get("/admin/jobs")
async def list_jobs(
    limit: int = 50,
    user: AuthenticatedUser = Depends(require_scope("tenant:manage")),
):
    """List recent background processing jobs."""
    services = get_services()
    # InMemoryJobQueue tracking
    jobs = []
    for j in getattr(services.job_queue, "_jobs", {}).values():
        if user.role == "admin" or j.tenant_id == user.tenant_id:
            jobs.append({
                "job_id": j.job_id,
                "job_type": j.job_type.value,
                "tenant_id": j.tenant_id,
                "patient_id": j.patient_id,
                "status": j.status.value,
                "retry_count": j.retry_count,
                "created_at": j.created_at,
                "error": j.error,
            })
    return {"items": jobs[:limit], "total_count": len(jobs)}


@router.get("/audit/log")
async def query_audit_log(
    limit: int = 25,
    cursor: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_scope("audit:read")),
):
    """Query immutable audit trail with cursor-based pagination."""
    services = get_services()
    return services.audit_log_repo.query_logs(
        tenant_id=user.tenant_id,
        limit=limit,
        cursor=cursor,
    )
