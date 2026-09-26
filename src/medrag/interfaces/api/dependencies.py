"""FastAPI dependency injection container and RBAC scope guards."""

from typing import Callable
from fastapi import Depends, Request
from medrag.application.services.claim_auditor import ClaimAuditor
from medrag.domain.exceptions import ClinicalException, TenantIsolationViolationException
from medrag.infrastructure.auth.auth_service import JWTAuthProvider
from medrag.infrastructure.auth.rate_limiter import TenantRateLimiter
from medrag.infrastructure.jobs.job_queue import MemoryJobQueue
from medrag.infrastructure.models.embedder import DeterministicEmbedder
from medrag.infrastructure.models.nli_verifier import DeterministicNLIVerifier
from medrag.infrastructure.models.reranker import RuleBasedReranker
from medrag.infrastructure.retrieval.rrf import compute_rrf_scores
from medrag.infrastructure.storage.audit_log import AuditLogRepository
from medrag.infrastructure.storage.lancedb_store import LanceDBVectorStore
from medrag.infrastructure.storage.timeline_repo import LanceDBTimelineRepository
from medrag.ports.auth import AuthenticatedUser


# Global singleton services for local/test execution
class ServiceContainer:
    def __init__(self) -> None:
        self.auth_provider = JWTAuthProvider()
        self.rate_limiter = TenantRateLimiter()
        self.audit_log_repo = AuditLogRepository()
        self.job_queue = MemoryJobQueue()
        self.timeline_repo = LanceDBTimelineRepository(db_uri="data/test_lancedb")
        self.vector_store = LanceDBVectorStore(db_uri="data/test_lancedb")
        self.embedder = DeterministicEmbedder()
        self.reranker = RuleBasedReranker()
        self.compute_rrf = compute_rrf_scores
        self.nli_verifier = DeterministicNLIVerifier()
        self.claim_auditor = ClaimAuditor(verifier=self.nli_verifier)


_container = ServiceContainer()


def get_services() -> ServiceContainer:
    return _container


def get_current_user(request: Request) -> AuthenticatedUser:
    """Extract authenticated user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise ClinicalException(
            "UNAUTHENTICATED",
            "Institutional session required.",
            status_code=401,
        )
    return user


def require_scope(required_scope: str) -> Callable:
    """Factory generating dependency that validates RBAC scope."""

    def _scope_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not user.has_scope(required_scope):
            raise ClinicalException(
                "INSUFFICIENT_SCOPE",
                f"Operation requires scope '{required_scope}'.",
                status_code=403,
                details={"required_scope": required_scope, "user_role": user.role},
            )
        return user

    return _scope_checker


def assert_tenant_boundary(user: AuthenticatedUser, target_tenant_id: str) -> None:
    """Enforce strict multi-tenant data access boundaries."""
    if user.role == "admin" or user.tenant_id == "system":
        return
    if user.tenant_id != target_tenant_id:
        raise TenantIsolationViolationException(target_tenant_id)
