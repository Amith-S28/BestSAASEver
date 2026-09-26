"""Port protocol for authentication and RBAC scope validation."""

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated user context injected by security middleware."""

    user_id: str
    tenant_id: str
    clinic_id: str
    role: str  # clinician | cmo | auditor | researcher | admin
    scopes: List[str]

    def has_scope(self, required_scope: str) -> bool:
        return required_scope in self.scopes or "admin" in self.scopes or self.role == "admin"


class IAuthProvider(Protocol):
    """Abstract interface for token and API key validation."""

    async def validate_token(self, token: str) -> Optional[AuthenticatedUser]:
        """Validate JWT session token and extract authenticated user context."""
        ...

    async def validate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        """Validate hashed API key and return authenticated tenant context."""
        ...
